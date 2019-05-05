from __future__ import unicode_literals

import asyncio

import discord
import youtube_dl

from discord.ext import commands

import sys

import settings.settings as settings

from cogs.music_cog import Music
from cogs.random_cog import Random

settings.init(sys.argv[1:])

bot = commands.Bot(command_prefix=commands.when_mentioned_or("!"),
                   description='MyDiscordBot')

@bot.command()
async def rekt(context):
    await bot.logout()
    sys.exit()

@bot.event
async def on_ready():
    print('Logged in as {0} ({0.id})'.format(bot.user))
    print('------')


bot.add_cog(Music(bot))
bot.add_cog(Random(bot))
bot.run(settings.token)
