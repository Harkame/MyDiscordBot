import discord
from discord.ext import commands
import sys

import settings.settings as settings

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
            player = await voice.create_ytdl_player(url)
            player.start()

        #vc = await bot.join_voice_channel(author.voice_channel)

        #player = await vc.create_ytdl_player(url)
    #    player.start()

    bot.run(settings.token)

if __name__ == '__main__':
    main(sys.argv[1:])
