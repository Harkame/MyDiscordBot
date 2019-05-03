from __future__ import unicode_literals

import asyncio

import discord
import youtube_dl

from discord.ext import commands

import sys

import settings.settings as settings

import asyncio
import itertools
import sys
import traceback
from async_timeout import timeout
from functools import partial
from youtube_dl import YoutubeDL

from helper.ydtl_helper import YTDLSource

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def join(self, context, *, channel: discord.VoiceChannel):
        if context.voice_client is not None:
            return await context.voice_client.move_to(channel)

        await channel.connect()

    @commands.command()
    async def play(self, context, *, url):
        async with context.typing():
            player = await YTDLSource.from_url(url, loop=self.bot.loop)
            context.voice_client.play(player, after=lambda e: print('Player error: %s' % e) if e else None)

        await context.send('Now playing: {}'.format(player.title))

    @commands.command()
    async def play_stream(self, context, *, url):
        async with context.typing():
            player = await YTDLSource.from_url(url, loop=self.bot.loop, stream=True)
            context.voice_client.play(player, after=lambda e: print('Player error: %s' % e) if e else None)

        await context.send('Now playing: {}'.format(player.title))

    @commands.command()
    async def volume(self, context, volume: int):
        if context.voice_client is None:
            return await context.send("Not connected to a voice channel.")

        context.voice_client.source.volume = volume / 100
        await context.send("Changed volume to {}%".format(volume))

    @commands.command()
    async def volume(self, context, volume: int):
        if context.voice_client is None:
            return await context.send("Not connected to a voice channel.")

        context.voice_client.source.volume = 0 / 100
        await context.send("Muted {}%".format(volume))

    @commands.command()
    async def stop(self, context):
        await context.voice_client.disconnect()

    @play.before_invoke
    @play_stream.before_invoke
    async def ensure_voice(self, context):
        if context.voice_client is None:
            if context.author.voice:
                await context.author.voice.channel.connect()
            else:
                await context.send("You are not connected to a voice channel.")
                raise commands.CommandError("Author not connected to a voice channel.")
        elif context.voice_client.is_playing():
            context.voice_client.stop()
