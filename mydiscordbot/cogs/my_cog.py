import discord
import time
from discord.ext import commands
import requests
import json
from random import randrange
import re

api_key = "2YUM3TJWX59R"


def get_random_gif():
    request = requests.get(
        f"https://g.tenor.com/v1/search?q=gay&key={api_key}&limit=50"
    )

    if request.status_code == 200:
        results = json.loads(request.content)["results"]

        return results[randrange(50)]["media"][0]["gif"]["url"]


class MyCog(commands.Cog):
    __slots__ = ("bot", "players")

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="pd", aliases=["gay"])
    async def pd(self, context, *args):
        if len(args) == 0 or len(args[0]) < 4:
            await context.send(f"<@238739541505081344> {get_random_gif()}")
            return
        else:
            name = args[0].lower()

            if "miel" in name:
                return

            for member in context.guild.members:
                if args[0].lower() in member.name.lower():
                    await context.send(f"<@{member.id}> {get_random_gif()}")
                    return

        # Héraclès..#3582
        # Whist#3376

    @commands.command(name="mp")
    async def mp(self, context, *args):
        if len(args) == 0 or len(args[0]) < 4:
            return

        name = args[0].lower()

        if "miel" in name:
            return

        print(name)

        if name == "harkame":
            if randrange(2) == 1:
                name = "curtis"
            else:
                name = "daddy"

        for member in context.guild.members:
            if name in member.name.lower():
                user = self.bot.get_user(member.id)

                if hasattr(user, "create_dm"):
                    channel = await user.create_dm()
                    await channel.send(get_random_gif())

                return
