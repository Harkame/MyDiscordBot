import discord
from discord.ext import commands
import sys

import settings.settings as settings

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
    async def ping(context):
        await context.send('pong')

    @bot.command()
    async def logout(context):
        await bot.logout()
        sys.exit()

    @bot.command(pass_context=True)
    async def play(context, url):
        author = context.message.author
        channel = author.voice_channel
        await bot.join_voice_channel(channel)
        #vc = await bot.join_voice_channel(author.voice_channel)

        #player = await vc.create_ytdl_player(url)
    #    player.start()

    bot.run(settings.token)

if __name__ == '__main__':
    main(sys.argv[1:])
