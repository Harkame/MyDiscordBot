from __future__ import unicode_literals

import asyncio

import discord
import youtube_dl

from discord.ext import commands

import sys

import settings.settings as settings

from functools import partial
from youtube_dl import YoutubeDL

import random

TIMEOUT_CHANNEl = 30

(commands.Cog)

class Random(commands.Cog):
    __slots__ = ('bot', 'players')

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='random', aliases=['rand'])
    async def random(self, context, *args : int):
        if len(args) == 1:
            value = random.randrange(args[0])
        if len(args) == 2:
            value = random.randrange(args[0], args[1])
        if len(args) == 3:
            value = random.randrange(args[0], args[1], args[2])
        else:
            pass

        await context.send(value)
