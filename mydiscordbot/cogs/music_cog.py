from __future__ import unicode_literals

import asyncio
import random

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
import validators
from yaml import Loader, load, dump

TIMEOUT_CHANNEl = 30

ytdlopts = {
    "format": "bestaudio/best",
    "outtmpl": "downloads/%(extractor)s-%(id)s-%(title)s.%(ext)s",
    "restrictfilenames": True,
    "noplaylist": True,
    "nocheckcertificate": True,
    "ignoreerrors": False,
    "logtostderr": False,
    "quiet": True,
    "no_warnings": True,
    "default_search": "auto",
    "source_address": "0.0.0.0",  # ipv6 addresses cause issues sometimes
}

ffmpegopts = {
    "before_options": "-nostdin -reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn",
}

executable = os.path.join("ffmpeg")
# executable = os.path.join("D", "ffmpeg", "bin", "ffmpeg.exe")

ytdl = YoutubeDL(ytdlopts)

BEGIN_LIMIT = 0
END_LIMIT = 40

loto_gride = [i for i in range(BEGIN_LIMIT, END_LIMIT)]
loto_value = random.randrange(BEGIN_LIMIT, END_LIMIT)


def check_kick():
    global loto_gride
    global loto_value

    value = random.randrange(BEGIN_LIMIT, END_LIMIT)

    print(f"value : {value}")
    print(f"loto_value : {loto_value}")
    print(f"loto_gride : {loto_gride}")

    while value not in loto_gride:
        value = random.randrange(BEGIN_LIMIT, END_LIMIT)

    if loto_value == value:
        loto_gride = [i for i in range(BEGIN_LIMIT, END_LIMIT)]
        loto_value = random.randrange(BEGIN_LIMIT, END_LIMIT)
        return True

    loto_gride.remove(value)

    return False


class VoiceConnectionError(commands.CommandError):
    """Custom Exception class for connection errors."""


class InvalidVoiceChannel(VoiceConnectionError):
    """Exception for cases of invalid Voice Channels."""


class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, requester):
        super().__init__(source)
        self.requester = requester

        self.title = data.get("title")
        self.web_url = data.get("webpage_url")

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

        if "entries" in data:
            # take first item from a playlist
            data = data["entries"][0]

        await context.send(
            f'```ini\n[Added {data["title"]} to the Queue.]\n```', delete_after=15
        )

        if download:
            source = ytdl.prepare_filename(data)
        else:
            return {
                "webpage_url": data["webpage_url"],
                "requester": context.author,
                "title": data["title"],
            }

        return cls(
            discord.FFmpegPCMAudio(source, options=ffmpegopts, executable=executable),
            data=data,
            requester=context.author,
        )

    @classmethod
    async def regather_stream(cls, data, *, loop):
        """Used for preparing a stream, instead of downloading.
        Since Youtube Streaming links expire."""
        loop = loop or asyncio.get_event_loop()
        requester = data["requester"]

        to_run = partial(ytdl.extract_info, url=data["webpage_url"], download=False)
        data = await loop.run_in_executor(None, to_run)

        return cls(
            discord.FFmpegPCMAudio(
                data["url"], options=ffmpegopts, executable=executable
            ),
            data=data,
            requester=requester,
        )


class MusicPlayer:
    __slots__ = (
        "bot",
        "_guild",
        "_channel",
        "_cog",
        "queue",
        "next",
        "current",
        "np",
        "volume",
    )

    def __init__(self, context):
        self.bot = context.bot
        self._guild = context.guild
        self._channel = context.channel
        self._cog = context.cog

        self.queue = asyncio.Queue()
        self.next = asyncio.Event()

        self.np = None  # Now playing message
        self.volume = 0.5
        self.current = None

        context.bot.loop.create_task(self.player_loop())

    async def player_loop(self):
        """Our main player loop."""
        await self.bot.wait_until_ready()

        while not self.bot.is_closed():
            self.next.clear()
            """
            try:
                #async with timeout(1):  # 5 minutes...
                source = await self.queue.get()
            except asyncio.TimeoutError:
                return self.destroy(self._guild)
            """
            source = await self.queue.get()

            if not isinstance(source, YTDLSource):
                try:
                    source = await YTDLSource.regather_stream(
                        source, loop=self.bot.loop
                    )
                except Exception as e:
                    await self._channel.send(
                        f"There was an error processing your song.\n"
                        f"```css\n[{e}]\n```"
                    )
                    continue

            source.volume = self.volume
            self.current = source

            self._guild.voice_client.play(
                source,
                after=lambda _: self.bot.loop.call_soon_threadsafe(self.next.set),
            )
            self.np = await self._channel.send(
                f"**Now Playing:** `{source.title}` requested by "
                f"`{source.requester}`"
            )
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
    __slots__ = ("bot", "players")

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
                return await context.send(
                    "This command can not be used in Private Messages."
                )
            except discord.HTTPException:
                pass
        elif isinstance(error, InvalidVoiceChannel):
            await context.send(
                "Error connecting to Voice Channel. "
                "Please make sure you are in a valid channel or provide me with one"
            )

        print(
            "Ignoring exception in command {}:".format(context.command), file=sys.stderr
        )
        traceback.print_exception(
            type(error), error, error.__traceback__, file=sys.stderr
        )

    def get_player(self, context):
        """Retrieve the guild player, or generate one."""
        try:
            player = self.players[context.guild.id]
        except KeyError:
            player = MusicPlayer(context)
            self.players[context.guild.id] = player

        return player

    @commands.command(name="connect", aliases=["join"])
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
                    "No channel to join. Please either specify a valid channel or join one."
                )

        vc = context.voice_client

        if vc:
            if vc.channel.id == channel.id:
                return
            try:
                await vc.move_to(channel)
            except asyncio.TimeoutError:
                raise VoiceConnectionError(f"Moving to channel: <{channel}> timed out.")
        else:
            try:
                await channel.connect()
            except asyncio.TimeoutError:
                raise VoiceConnectionError(
                    f"Connecting to channel: <{channel}> timed out."
                )

        await context.send(f"Connected to: **{channel}**", delete_after=20)

    @commands.command(name="play")
    # @commands.has_permissions(administrator=True)
    async def play(self, context, search: str):
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

        # print(context.channel.members)
        # await context.channel.members[0].edit(voice_channel=None)

        if not vc:
            await context.invoke(self.connect_)
            await self.martinez(context)

        if check_kick():
            for member in context.channel.members:
                if member.id == 299891365813157889:
                    await member.move_to(None)

        player = self.get_player(context)

        # If download is False, source will be a dict which will be used later to regather the stream.
        # If download is True, source will be a discord.FFmpegPCMAudio with a VolumeTransformer.

        source = await YTDLSource.create_source(
            context, search, loop=self.bot.loop, download=False
        )

        await player.queue.put(source)

    @commands.command(name="veg")
    async def veg(self, context):
        await self.play(
            context,
            search="https://www.youtube.com/watch?v=Wb0sytKNFM0&feature=youtu.be",
        )

    @commands.command(name="calbut")
    async def calbut(self, context):
        await self.play(
            context, search="https://www.youtube.com/watch?v=Mwxk8CR5Kfk",
        )

    @commands.command(name="martinez")
    async def martinez(self, context):
        await self.play(
            context, search="https://www.youtube.com/watch?v=tbQShwfsFmE",
        )

    @commands.command(name="mec")
    async def mec(self, context):
        await self.play(
            context,
            search="https://www.youtube.com/watch?v=y47njK4mrk8&feature=youtu.be",
        )

    @commands.command(name="pause")
    async def pause(self, context):
        """Pause the currently playing song."""
        vc = context.voice_client

        if not vc or not vc.is_playing():
            return await context.send(
                "I am not currently playing anything!", delete_after=20
            )
        elif vc.is_paused():
            return

        vc.pause()
        await context.send(f"**`{context.author}`**: Paused the song!")

    @commands.command(name="resume")
    async def resume(self, context):
        """Resume the currently paused song."""
        vc = context.voice_client

        if not vc or not vc.is_connected():
            return await context.send(
                "I am not currently playing anything!", delete_after=20
            )
        elif not vc.is_paused():
            return

        vc.resume()
        await context.send(f"**`{context.author}`**: Resumed the song!")

    @commands.command(name="skip", aliases=["next"])
    async def skip_(self, context):
        """Skip the song."""
        vc = context.voice_client

        if not vc or not vc.is_connected():
            return await context.send(
                "I am not currently playing anything!", delete_after=20
            )

        if vc.is_paused():
            pass
        elif not vc.is_playing():
            return

        vc.stop()
        await context.send(f"**`{context.author}`**: Skipped the song!")

    @commands.command(name="queue", aliases=["q", "playlist"])
    async def queue_info(self, context):
        vc = context.voice_client

        if not vc or not vc.is_connected():
            return await context.send(
                "I am not currently connected to voice!", delete_after=20
            )

        player = self.get_player(context)
        if player.queue.empty():
            return await context.send("There are currently no more queued songs.")

        # Grab up to 5 entries from the queue...
        upcoming = list(itertools.islice(player.queue._queue, 0, 5))

        fmt = "\n".join(f'**`{_["title"]}`**' for _ in upcoming)
        embed = discord.Embed(title=f"Upcoming - Next {len(upcoming)}", description=fmt)

        await context.send(embed=embed)

    @commands.command(
        name="now_playing", aliases=["np", "current", "currentsong", "playing"]
    )
    async def now_playing_(self, context):
        vc = context.voice_client

        if not vc or not vc.is_connected():
            return await context.send(
                "I am not currently connected to voice!", delete_after=20
            )

        player = self.get_player(context)
        if not player.current:
            return await context.send("I am not currently playing anything!")

        try:
            # Remove our previous now_playing message.
            await player.np.delete()
        except discord.HTTPException:
            pass

        player.np = await context.send(f"**Now Playing :** `{vc.source.title}` ")
        # f"requested by `{vc.source.requester}`"

    @commands.command(name="volume", aliases=["vol"])
    async def change_volume(self, context, *, vol: float):
        """Change the player volume.
        Parameters
        ------------
        volume: float or int [Required]
            The volume to set the player to in percentage. This must be between 1 and 100.
        """
        vc = context.voice_client

        if not vc or not vc.is_connected():
            return await context.send(
                "I am not currently connected to voice!", delete_after=20
            )

        if not 0 < vol < 101:
            return await context.send("Please enter a value between 1 and 100.")

        player = self.get_player(context)

        if vc.source:
            vc.source.volume = vol / 100

        player.volume = vol / 100
        await context.send(
            f"**`{context.author}`**: Set the volume to **{vol}%**", delete_after=10
        )

    @commands.command(name="stop")
    async def stop_(self, context):
        """Stop the currently playing song and destroy the player.
        !Warning!
            This will destroy the player assigned to your guild, also deleting any queued songs and settings.
        """
        vc = context.voice_client

        if not vc or not vc.is_connected():
            return await context.send(
                "I am not currently playing anything!", delete_after=10
            )

        await self.cleanup(context.guild)
