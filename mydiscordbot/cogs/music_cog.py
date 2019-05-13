from __future__ import unicode_literals

import asyncio

import discord
import youtube_dl

from discord.ext import commands

import sys

import itertools
import traceback
from async_timeout import timeout

from helpers.config_helper import get_config

import settings.settings as settings

TIMEOUT_CHANNEl = 30

class VoiceConnectionError(commands.CommandError):
    """Custom Exception class for connection errors."""


class InvalidVoiceChannel(VoiceConnectionError):
    """Exception for cases of invalid Voice Channels."""

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
        if not context.guild:
            raise commands.NoPrivateMessage
        return True

    async def __error(self, context, error):
        if isinstance(error, commands.NoPrivateMessage):
            try:
                return await context.send('This command can not be used in Private Messages.')
            except discord.HTTPException:
                pass
        elif isinstance(error, InvalidVoiceChannel):
            await context.send('Error connecting to Voice Channel. '
                           'Please make sure you are in a valid channel or provide me with one')

        print('Ignoring exception in command {}:'.format(context.command), file=sys.stderr)
        traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)

    def get_player(self, context):
        try:
            player = self.players[context.guild.id]
        except KeyError:
            player = MusicPlayer(context)
            self.players[context.guild.id] = player

        return player

    @commands.command(name='connect', aliases=['join'])
    async def connect_(self, context, *, channel: discord.VoiceChannel=None):
        if not channel:
            if not context.author.voice:
                raise InvalidVoiceChannel('No channel to join. Please either specify a valid channel or join one.')

            channel = context.author.voice.channel

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

    @commands.command(name='play', aliases=['sing'])
    async def play(self, context, *, search: str):
        await context.trigger_typing()

        vc = context.voice_client

        if not vc:
            await context.invoke(self.connect_)

        player = self.get_player(context)


        # If download is False, source will be a dict which will be used later to regather the stream.
        # If download is True, source will be a discord.FFmpegPCMAudio with a VolumeTransformer.
        source = await YTDLSource.from_url(search, loop=self.bot.loop)

        await player.queue.put(source)

    @commands.command()
    async def play_stream(self, context, *, url):
        async with context.typing():
            source = await YTDLSource.from_url(url, loop=self.bot.loop, stream=True)
            player = self.get_player(context)

            await player.queue.put(source)

        await context.send('Now playing: {}'.format(player.title))

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
            await player.now_playing.delete()
        except discord.HTTPException:
            pass

        player.now_playing = await context.send(f'**Now Playing:** `{vc.source.title}`')

    @commands.command(name='volume', aliases=['vol'])
    async def change_volume(self, context, *, vol: float):
        vc = context.voice_client

        if not vc or not vc.is_connected():
            return await context.send('I am not currently connected to voice!', delete_after=20)

        if not -1 < vol < 101:
            return await context.send('0 - 100.')

        player = self.get_player(context)

        if vc.source:
            vc.source.volume = vol / 100

        player.volume = vol / 100
        await context.send(f'**`{context.author}`**: Set the volume to **{vol}%**')

    @commands.command(name='mute', aliases=['m', 'tg'])
    async def mute(self, context):
        vc = context.voice_client

        if not vc or not vc.is_connected():
            return await context.send('I am not currently connected to voice!', delete_after=20)

        player = self.get_player(context)

        if vc.source:
            vc.source.volume = 0 / 100

        player.volume = 0 / 100
        await context.send(f'**`{context.author}`**: Mute de bot*')

    @commands.command(name='stop')
    async def stop_(self, context):
        vc = context.voice_client

        if not vc or not vc.is_connected():
            return await context.send('I am not currently playing anything!', delete_after=20)

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

        if parameters[0] in ['create', 'add']:
            if len(parameters) == 1:
                await context.send('Missing playist name')
                return

            player.create_playist(parameters[1])

            await context.send('Playist {} created'.format(parameters[1]))
        elif parameters[0] in ['delete', 'remove']:
            if parameters[1].isdigit():
                index = int(parameters[1])

                playist_title = settings.playists[index].title

                settings.playists.pop(index)

                await context.send('Playist {} deleted'.format(playist_title))
            else:
                await context.send('Invalid index')
        elif parameters[0].isdigit():
            index = int(parameters[0])

            if index > len(settings.playists):
                await context.send('Invalid index')

                return

            playist = settings.playists[index]

            if len(parameters) == 1:
                await context.send('Playist {} : '.format(playist.title))

                if len(playist.urls) == 0:
                    await context.send('No song')
                else:
                    for index, key in enumerate(settings.playists):
                        await context.send('[{}] - {}'.format(index, key))
                return
            else:
                if parameters[1] in ['create', 'add']:
                    playist.urls.append(parameters[2])
                elif parameters[1] in ['delete', 'remove']:
                    if len(parameters) == 2:
                        await context.send('Invalid index')
                        return

                    if parameters[2].isdigit():
                        index = int(parameters[2])

                        if index > len(playist.urls):
                            await context.send('Invalid index')
                            return

                        title = playist.title

                        url = playist.urls[index]

                        playist.urls.pop(index)

                        await context.send('Url {} removed'.format(url))
                    else:
                        await context.send('Invalid index')

                elif parameters[1] == 'rename':
                    old_name = playist.title

                    playist.title = parameters[2]

                    await context.send('Playist {} renamed to {}'.format(old_name, playist.title))
                elif parameters[1] == 'play':
                    if index < len(settings.playists):
                        await context.send('Invalid index')
                        return

                    playist = settings.playists[index]

                    for url in playist.urls:
                        source = await YTDLSource.from_url(url, loop=self.bot.loop)

                        await player.queue.put(source)

        else:
            await context.send('Unknow parameters')
            return

class MusicPlayer:
    __slots__ = ('bot', '_guild', '_channel', '_cog', 'queue', 'next', 'current', 'now_playing', 'volume', 'playists')

    def __init__(self, context):
        self.bot = context.bot
        self._guild = context.guild
        self._channel = context.channel
        self._cog = context.cog

        self.queue = asyncio.Queue()
        self.next = asyncio.Event()

        self.now_playing = None  # Now playing message
        self.volume = .5
        self.current = None

        context.bot.loop.create_task(self.player_loop())

    async def player_loop(self):
        """Our main player loop."""
        await self.bot.wait_until_ready()

        while not self.bot.is_closed():
            self.next.clear()

            try:
                async with timeout(TIMEOUT_CHANNEl):
                    source = await self.queue.get()
            except asyncio.TimeoutError:
                return self.destroy(self._guild)

            if not isinstance(source, YTDLSource):
                try:
                    source = await YTDLSource.from_url(source, loop=self.bot.loop, download=False, stream=True)
                except Exception as e:
                    await self._channel.send(f'There was an error processing your song.\n'
                                             f'```css\n[{e}]\n```')
                    continue

            source.volume = self.volume
            self.current = source

            self._guild.voice_client.play(source, after=lambda _: self.bot.loop.call_soon_threadsafe(self.next.set))
            self.now_playing = await self._channel.send(f'**Now Playing:** `{source.title}`')
            await self.next.wait()

            source.cleanup()
            self.current = None

            try:
                await self.now_playing.delete()
            except discord.HTTPException:
                pass

    def destroy(self, guild):
        return self.bot.loop.create_task(self._cog.cleanup(guild))

    def create_playist(self, title):
        self.playists[title] = []

youtube_dl.utils.bug_reports_message = lambda: ''

ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '192.168.0.1'
}

ffmpeg_options = {
    'options': '-vn'
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)

        self.data = data

        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=False))

        if 'entries' in data:
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)
