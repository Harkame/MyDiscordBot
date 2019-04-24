import discord
from discord.ext import commands
import sys

token = ''

def main(arguments):
    bot = commands.Bot(command_prefix='%')

    @bot.command()
    async def ping(ctx):
        await ctx.send('pong')

    bot.run('')

if __name__ == '__main__':
    main(sys.argv[1:])
