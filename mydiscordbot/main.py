from __future__ import unicode_literals

import discord
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



ytdlopts = {
    'format': 'bestaudio/best',
    'outtmpl': 'music/%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',
}

ffmpegopts = {
    'before_options': '-nostdin',
    'options': '-vn'
}

ytdl = YoutubeDL(ytdlopts)

class YTDLSource(discord.PCMVolumeTransformer):

    def __init__(self, source, *, data, requester):
        super().__init__(source)
        self.requester = requester

        self.title = data.get('title')
        self.web_url = data.get('webpage_url')

    def __getitem__(self, item: str):

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

        return cls(discord.FFmpegPCMAudio(source), data=data, requester=context.author)

    @classmethod
    async def regather_stream(cls, data, *, loop):
        loop = loop or asyncio.get_event_loop()
        requester = data['requester']

        to_run = partial(ytdl.extract_info, url=data['webpage_url'], download=False)
        data = await loop.run_in_executor(None, to_run)

        return cls(discord.FFmpegPCMAudio(data['url']), data=data, requester=requester)


def main(arguments):
    settings.init(arguments)

    bot = commands.Bot(command_prefix='!')

    @bot.command()
    async def rekt(context):
        await bot.logout()
        sys.exit()

    @bot.command(pass_context=True)
    async def play(context, *song_name):
        author = context.message.author

        if not author.voice:
            await context.send('You are not connected to a voice channel')
            return

        channel = author.voice.channel

        voice = bot.voice_clients
        if voice and voice.is_connected():
            await voice.move_to(channel)
        else:
            voice = await channel.connect()

        formated_song_name = " ".join(song_name)

        source = await YTDLSource.create_source(context, formated_song_name, loop=bot.loop, download=True)

        voice.play(source)

    @bot.command(pass_context=True)
    async def pause(context):
        vc = context.voice_clients
        vc.pause()

    @bot.command(pass_context=True)
    async def resume(context):
        vc = context.voice_clients
        vc.resume()

    @bot.command(pass_context=True)
    async def stop(context):
        vc = bot.voice_clients
        vc.stop()


    @bot.command(pass_context=True)
    async def volume(context, volume):
        vc = context.voice_client

        if not vc or not vc.is_connected():
            return await context.send('I am not currently connected to voice!', delete_after=20)

        if not 0 < vol < 101:
            return await context.send('Please enter a value between 1 and 100.')

        player = self.get_player(context)

        if vc.source:
            vc.source.volume = vol / 100

        player.volume = vol / 100
        await context.send(f'**`{context.author}`**: Set the volume to **{vol}%**')


    @bot.command(pass_context=True)
    async def customplay(context):
        guild = context.guild.voice_channels

        #channel = discord.utils.get(guild.voice_channels, name='Général', bitrate=64000)
        #if channel is not None:
        await context.send(guild)

    bot.run(settings.token)

if __name__ == '__main__':
    main(sys.argv[1:])
