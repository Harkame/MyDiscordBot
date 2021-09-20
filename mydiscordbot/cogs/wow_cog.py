from __future__ import unicode_literals

import discord

from discord.ext import commands

import random

TIMEOUT_CHANNEl = 30


class Random(commands.Cog):
    __slots__ = ("bot", "players")

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="affix")
    async def affix(self, context, *args: int):
        pass
