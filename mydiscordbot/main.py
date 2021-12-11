from __future__ import unicode_literals

import discord
from discord.ext import commands

import sys

import settings.settings as settings

from cogs.music_cog import Music
from cogs.random_cog import Random
from cogs.my_cog import MyCog

settings.init(sys.argv[1:])
intents = discord.Intents.default()
intents.members = True

bot = commands.Bot(
    command_prefix=commands.when_mentioned_or("!"),
    description="MyDiscordBot",
    intents=intents,
)


@bot.command()
async def rekt(context):

    if str(context.author) == "Harkame#2009":
        await context.send("Tchao")
        await bot.logout()
    else:
        await context.send("Tchao")


@bot.command()
async def on_ready():
    print("Logged in as {0} ({0.id})".format(bot.user))
    print("------")


bot.add_cog(Music(bot))
bot.add_cog(Random(bot))
bot.add_cog(MyCog(bot))

bot.run(settings.token)
