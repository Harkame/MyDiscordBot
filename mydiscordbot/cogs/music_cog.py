from __future__ import unicode_literals

import asyncio

import discord
from youtube_dl import YoutubeDL

from discord.ext import commands

import sys

import itertools
import traceback
from async_timeout import timeout

from functools import partial

import settings.settings as settings

import os

from helpers import helper_config

TIMEOUT_CHANNEl = 30

ytdlopts = {
    'format': 'bestaudio/best',
    'outtmpl': 'downloads/%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0'  # ipv6 addresses cause issues sometimes
}

ffmpegopts = {
    'before_options': '-nostdin',
    'options': '-vn',
}

executable = os.path.join('C:\\', 'ffmpeg', 'bin', 'ffmpeg.exe')

ytdl = YoutubeDL(ytdlopts)


class VoiceConnectionError(commands.CommandError):
    """Custom Exception class for connection errors."""


class InvalidVoiceChannel(VoiceConnectionError):
    """Exception for cases of invalid Voice Channels."""


class YTDLSource(discord.PCMVolumeTransformer):

    def __init__(self, source, *, data, requester):
        super().__init__(source)
        self.requester = requester

        self.title = data.get('title')
        self.web_url = data.get('webpage_url')

        # YTDL info dicts (data) have other useful information you might want
        # https://github.com/rg3/youtube-dl/blob/master/README.md

    def __getitem__(self, item: str):
        """Allows us to access attributes similar to a dict.
        This is only useful when you are NOT downloading.
        """
        return self.__getattribute__(item)

    @classmethod
    async def create_source(cls, context, search: str, *, loop, download=False):
        loop = loop or asyncio.get_event_loop()

        to_run = partial(ytdl.extract_info, url=search, download=download)
        data = await loop.run_in_executor(None, to_run)

        if 'entries' in data:
            # take first item from a playlist
            data = data['entries'][0]

        await context.send(f'```ini\n[Added {data["title"]} to the Queue.]\n```', delete_after=15)

        if download:
            source = ytdl.prepare_filename(data)
        else:
            return {'webpage_url': data['webpage_url'], 'requester': context.author, 'title': data['title']}

        return cls(discord.FFmpegPCMAudio(source, executable=executable), data=data, requester=context.author)

    @classmethod
    async def regather_stream(cls, data, *, loop):
        """Used for preparing a stream, instead of downloading.
        Since Youtube Streaming links expire."""
        loop = loop or asyncio.get_event_loop()
        requester = data['requester']

        to_run = partial(ytdl.extract_info,
                         url=data['webpage_url'], download=False)
        data = await loop.run_in_executor(None, to_run)

        return cls(discord.FFmpegPCMAudio(data['url'], executable=executable), data=data, requester=requester)


class MusicPlayer:
    """A class which is assigned to each guild using the bot for Music.
    This class implements a queue and loop, which allows for different guilds to listen to different playlists
    simultaneously.
    When the bot disconnects from the Voice it's instance will be destroyed.
    """

    __slots__ = ('bot', '_guild', '_channel', '_cog',
                 'queue', 'next', 'current', 'np', 'volume')

    def __init__(self, context):
        self.bot = context.bot
        self._guild = context.guild
        self._channel = context.channel
        self._cog = context.cog

        self.queue = asyncio.Queue()
        self.next = asyncio.Event()

        self.np = None  # Now playing message
        self.volume = .5
        self.current = None

        context.bot.loop.create_task(self.player_loop())

    async def player_loop(self):
        """Our main player loop."""
        await self.bot.wait_until_ready()

        while not self.bot.is_closed():
            self.next.clear()

            try:
                # Wait for the next song. If we timeout cancel the player and disconnect...
                async with timeout(300):  # 5 minutes...
                    source = await self.queue.get()
            except asyncio.TimeoutError:
                return self.destroy(self._guild)

            if not isinstance(source, YTDLSource):
                # Source was probably a stream (not downloaded)
                # So we should regather to prevent stream expiration
                try:
                    source = await YTDLSource.regather_stream(source, loop=self.bot.loop)
                except Exception as e:
                    await self._channel.send(f'There was an error processing your song.\n'
                                             f'```css\n[{e}]\n```')
                    continue

            source.volume = self.volume
            self.current = source

            self._guild.voice_client.play(
                source, after=lambda _: self.bot.loop.call_soon_threadsafe(self.next.set))
            self.np = await self._channel.send(f'**Now Playing:** `{source.title}` requested by '
                                               f'`{source.requester}`')
            await self.next.wait()

            # Make sure the FFmpeg process is cleaned up.
            source.cleanup()
            self.current = None

            try:
                # We are no longer playing this song...
                await self.np.delete()
            except discord.HTTPException:
                pass

    def destroy(self, guild):
        return self.bot.loop.create_task(self._cog.cleanup(guild))


class Music(commands.Cog):
    __slots__ = ('bot', 'players')

    def __init__(self, bot):
        self.bot = bot
        self.players = {}

    async def cleanup(self, guild):
        try:
            await guild.voice_client.disconnect()
        except AttributeError:
            pass

        try:
            del self.players[guild.id]
        except KeyError:
            pass

    async def __local_check(self, context):
        """A local check which applies to all commands in this cog."""
        if not context.guild:
            raise commands.NoPrivateMessage
        return True

    async def __error(self, context, error):
        """A local error handler for all errors arising from commands in this cog."""
        if isinstance(error, commands.NoPrivateMessage):
            try:
                return await context.send('This command can not be used in Private Messages.')
            except discord.HTTPException:
                pass
        elif isinstance(error, InvalidVoiceChannel):
            await context.send('Error connecting to Voice Channel. '
                           'Please make sure you are in a valid channel or provide me with one')

        print('Ignoring exception in command {}:'.format(context.command), file=sys.stderr)
        traceback.print_exception(
            type(error), error, error.__traceback__, file=sys.stderr)

    def get_player(self, context):
        """Retrieve the guild player, or generate one."""
        try:
            player = self.players[context.guild.id]
        except KeyError:
            player = MusicPlayer(context)
            self.players[context.guild.id] = player

        return player

    @commands.command(name='connect', aliases=['join'])
    async def connect_(self, context, *, channel: discord.VoiceChannel = None):
        """Connect to voice.
        Parameters
        ------------
        channel: discord.VoiceChannel [Optional]
            The channel to connect to. If a channel is not specified, an attempt to join the voice channel you are in
            will be made.
        This command also handles moving the bot to different channels.
        """
        if not channel:
            try:
                channel = context.author.voice.channel
            except AttributeError:
                raise InvalidVoiceChannel(
                    'No channel to join. Please either specify a valid channel or join one.')

        vc = context.voice_client

        if vc:
            if vc.channel.id == channel.id:
                return
            try:
                await vc.move_to(channel)
            except asyncio.TimeoutError:
                raise VoiceConnectionError(f'Moving to channel: <{channel}> timed out.')
        else:
            try:
                await channel.connect()
            except asyncio.TimeoutError:
                raise VoiceConnectionError(f'Connecting to channel: <{channel}> timed out.')

        await context.send(f'Connected to: **{channel}**', delete_after=20)

    @commands.command(name='play', aliases=['sing'])
    async def play_(self, context, *, search: str):
        """Request a song and add it to the queue.
        This command attempts to join a valid voice channel if the bot is not already in one.
        Uses YTDL to automatically search and retrieve a song.
        Parameters
        ------------
        search: str [Required]
            The song to search and retrieve using YTDL. This could be a simple search, an ID or URL.
        """
        await context.trigger_typing()

        vc = context.voice_client

        if not vc:
            await context.invoke(self.connect_)

        player = self.get_player(context)

        # If download is False, source will be a dict which will be used later to regather the stream.
        # If download is True, source will be a discord.FFmpegPCMAudio with a VolumeTransformer.
        source = await YTDLSource.create_source(context, search, loop=self.bot.loop, download=False)

        await player.queue.put(source)

    @commands.command(name='pause')
    async def pause_(self, context):
        """Pause the currently playing song."""
        vc = context.voice_client

        if not vc or not vc.is_playing():
            return await context.send('I am not currently playing anything!', delete_after=20)
        elif vc.is_paused():
            return

        vc.pause()
        await context.send(f'**`{context.author}`**: Paused the song!')

    @commands.command(name='resume')
    async def resume_(self, context):
        """Resume the currently paused song."""
        vc = context.voice_client

        if not vc or not vc.is_connected():
            return await context.send('I am not currently playing anything!', delete_after=20)
        elif not vc.is_paused():
            return

        vc.resume()
        await context.send(f'**`{context.author}`**: Resumed the song!')

    @commands.command(name='skip')
    async def skip_(self, context):
        """Skip the song."""
        vc = context.voice_client

        if not vc or not vc.is_connected():
            return await context.send('I am not currently playing anything!', delete_after=20)

        if vc.is_paused():
            pass
        elif not vc.is_playing():
            return

        vc.stop()
        await context.send(f'**`{context.author}`**: Skipped the song!')

    @commands.command(name='queue', aliases=['q', 'playlist'])
    async def queue_info(self, context):
        """Retrieve a basic queue of upcoming songs."""
        vc = context.voice_client

        if not vc or not vc.is_connected():
            return await context.send('I am not currently connected to voice!', delete_after=20)

        player = self.get_player(context)
        if player.queue.empty():
            return await context.send('There are currently no more queued songs.')

        # Grab up to 5 entries from the queue...
        upcoming = list(itertools.islice(player.queue._queue, 0, 5))

        fmt = '\n'.join(f'**`{_["title"]}`**' for _ in upcoming)
        embed = discord.Embed(title=f'Upcoming - Next {len(upcoming)}', description=fmt)

        await context.send(embed=embed)

    @commands.command(name='now_playing', aliases=['np', 'current', 'currentsong', 'playing'])
    async def now_playing_(self, context):
        vc = context.voice_client

        if not vc or not vc.is_connected():
            return await context.send('I am not currently connected to voice!', delete_after=20)

        player = self.get_player(context)
        if not player.current:
            return await context.send('I am not currently playing anything!')

        try:
            # Remove our previous now_playing message.
            await player.np.delete()
        except discord.HTTPException:
            pass

        player.np = await context.send(f'**Now Playing:** `{vc.source.title}` '
                                   f'requested by `{vc.source.requester}`')

    @commands.command(name='volume', aliases=['vol'])
    async def change_volume(self, context, *, vol: float):
        """Change the player volume.
        Parameters
        ------------
        volume: float or int [Required]
            The volume to set the player to in percentage. This must be between 1 and 100.
        """
        vc = context.voice_client

        if not vc or not vc.is_connected():
            return await context.send('I am not currently connected to voice!', delete_after=20)

        if not 0 < vol < 101:
            return await context.send('Please enter a value between 1 and 100.')

        player = self.get_player(context)

        if vc.source:
            vc.source.volume = vol / 100

        player.volume = vol / 100
        await context.send(f'**`{context.author}`**: Set the volume to **{vol}%**', delete_after=10)

    @commands.command(name='stop')
    async def stop_(self, context):
        """Stop the currently playing song and destroy the player.
        !Warning!
            This will destroy the player assigned to your guild, also deleting any queued songs and settings.
        """
        vc = context.voice_client

        if not vc or not vc.is_connected():
            return await context.send('I am not currently playing anything!', delete_after=10)

        await self.cleanup(context.guild)

    @commands.command(name='playist')
    async def playist(self, context, *parameters):

        player = self.get_player(context)

        if len(parameters) == 0:
            if len(settings.playists) == 0:
                await context.send('No playists')
            else:
                await context.send('Playists : ')
                for index, key in enumerate(settings.playists):
                    await context.send('[{}] - {}'.format(index, key['title']))

            return

        if parameters[0] in ['create', 'add', 'new']:
            if len(parameters) == 1:
                await context.send('Missing playist name')
                return

            playist_name = parameters[1]

            if playist_name in settings.playists:
                await context.send('Playist name already used')
                return

            new_playist = {'title': playist_name, 'urls': []}

            settings.playists.append(new_playist)

            await context.send('Playist {} created'.format(parameters[1]))
        elif parameters[0] in ['delete', 'remove']:
            if parameters[1].isdigit():
                index = int(parameters[1])

                playist_title = settings.playists[index].title

                settings.playists.pop(index)

                await context.send('Playist {} deleted'.format(playist_title))
            else:
                await context.send('Invalid index')
        elif parameters[0] in ['save', 'keep', 'store']:
            helper_config.write_config(os.path.join(
                '.', 'playists.yml'), settings.playists)
            await context.send('Playists saved')
        elif parameters[0].isdigit():
            index = int(parameters[0])

            if index > len(settings.playists):
                await context.send('Invalid index')

                return

            playist = settings.playists[index]

            if len(parameters) == 1:
                await context.send('Playist {} : '.format(playist['title']))

                if len(playist['urls']) == 0:
                    await context.send('No song')
                else:
                    for index in range(len(playist['urls'])):
                        await context.send('{} : {}'.format(index, playist['urls'][index]))
                return
            else:
                if parameters[1] in ['create', 'add']:
                    playist['urls'].append(parameters[2])

                    await context.send(f"Song '{parameters[2]}' added to playist [{index}] ({playist['title']}")

                elif parameters[1] in ['delete', 'remove']:
                    if len(parameters) == 2:
                        await context.send('Invalid index')
                        return

                    if parameters[2].isdigit():
                        index = int(parameters[2])

                        if index > len(playist['urls']):
                            await context.send('Invalid index')
                            return

                        title = playist['title']

                        url = playist['urls'][index]

                        playist['urls'].pop(index)

                        await context.send(f'`{url}` removed')
                    else:
                        await context.send('Invalid index')

                elif parameters[1] == 'rename':
                    old_name = playist.title

                    playist.title = parameters[2]

                    await context.send('Playist {} renamed to {}'.format(old_name, playist.title))
                elif parameters[1] in ['play', 'run']:
                    await context.trigger_typing()

                    vc = context.voice_client

                    if not vc:
                        await context.invoke(self.connect_)

                    player = self.get_player(context)

                    for url in playist['urls']:
                        source = await YTDLSource.create_source(context, url, loop=self.bot.loop, download=False)
                        await player.queue.put(source)
        else:
            await context.send('Unknow parameters')
            return
