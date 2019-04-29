from __future__ import unicode_literals

import discord
from discord.ext import commands
import sys

import settings.settings as settings

import youtube_dl

def main(arguments):
    settings.init(arguments)

    bot = commands.Bot(command_prefix='!')

    @bot.command()
    async def logout(context):
        await bot.logout()
        sys.exit()

    @bot.command(pass_context=True)
    async def play(context, url):
        author = context.message.author
        await context.send(author)
        await context.send(url)
        channel = author.voice.channel

        if not channel:
            await ctx.send("You are not connected to a voice channel")
            return

        voice = bot.voice_clients
        if voice and voice.is_connected():
            await voice.move_to(channel)
        else:
            voice = await channel.connect()

            ydl_opts = {
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'ffmpeg_location' : 'C:\\Users\\Maxime\\Downloads\\ffmpeg-20190428-45048ec-win64-static\\bin',
                'outtmpl': 'music/test.mp3',
            }
            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

        #f = open("myfile.jpg", "rb")



    bot.run(settings.token)

if __name__ == '__main__':
    main(sys.argv[1:])
