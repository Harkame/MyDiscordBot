import discord
from discord.ext import commands
import sys

import settings.settings as settings

token = ''


import discord

class MyClient(discord.Client):
    async def on_ready(self):
        print('Logged on as', self.user)

    async def on_message(self, message):
        # don't respond to ourselves
        if message.author == self.user:
            return

        if message.content == 'ping':
            await message.channel.send('pong')

def main(arguments):
    settings.init(arguments)

    #client = MyClient()
    #client.run(settings.token)

    bot = commands.Bot(command_prefix='/')

    @bot.command()
    async def ping(ctx):
        await ctx.send('pong')

    @bot.command()
    async def play(ctx, url):
        print('play')
        author = ctx.message.author
        voice_channel = author.voice_channel
        vc = await client.join_voice_channel(voice_channel)

        player = await vc.create_ytdl_player(url)
        player.start()

    bot.run(settings.token)

if __name__ == '__main__':
    main(sys.argv[1:])
