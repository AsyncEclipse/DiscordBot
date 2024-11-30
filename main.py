import asyncio
import os
import discord
import time
from commands.game_commands import GameCommands
from commands.tile_commands import TileCommands
import config
from discord import app_commands
from commands.setup_commands import SetupCommands
from commands.player_commands import PlayerCommands
from commands.search_commands import SearchCommands
# from helpers import ImageCache
from helpers import ImageCache
from helpers.GamestateHelper import GamestateHelper
from listeners.ButtonListener import ButtonListener
from discord.ext import commands
import logging
# import threading


class DiscordBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def on_ready(self):
        self.loop.create_task(self.start_timer())

    async def setup_hook(self) -> None:
        print("Bot is starting")
        await self.add_cog(SetupCommands(self))
        await self.add_cog(TileCommands(self))
        await self.add_cog(PlayerCommands(self))
        await self.add_cog(ButtonListener(self))
        await self.add_cog(GameCommands(self))
        await self.add_cog(SearchCommands(self))
        await self.add_cog(AdminCommands(self))
        await self.tree.sync()
        start_time = time.perf_counter()
        print("Starting to load images")
        ImageCache.ImageCacheHelper("images/resources")
        end_time = time.perf_counter()
        elapsed_time = end_time - start_time
        print(f"Total elapsed time for image load: {elapsed_time:.2f} seconds")
        print("Bot is now ready.")

    async def start_timer(self):
        while True:
            await self.checkGameTimers()
            await asyncio.sleep(3600 * 2)

    async def checkGameTimers(self):
        guild = bot.get_guild(1254475918873985094)
        if guild is None:
            return
        for x in range(0, 999):
            gameName = f"aeb{x}"
            if not os.path.exists(f"{config.gamestate_path}/{gameName}_saveFile.json"):
                continue
            game = GamestateHelper(None, gameName)
            if len(game.gamestate.get("activePlayerColor", [])) > 0 and "lastPingTime" in game.gamestate:
                current_time_seconds = time.time()
                oldPingTime = game.gamestate["lastPingTime"]
                if current_time_seconds - oldPingTime > 3600 * 12:
                    actions_channel = discord.utils.get(guild.channels, name=f"{game.game_id}-actions")
                    if actions_channel is not None and isinstance(actions_channel, discord.TextChannel):
                        player = game.getPlayerObjectFromColor(game.gamestate["activePlayerColor"][0])
                        message = f"{player['player_name']}, this is a gentle reminder that it is your turn."
                        await actions_channel.send(message)
                        game.updatePingTime()
                else:
                    if "20MinReminder" in game.gamestate and len(game.gamestate["20MinReminder"]) > 0 and game.gamestate["activePlayerColor"][0] == game.gamestate["20MinReminder"][0]:
                        player = game.getPlayerObjectFromColor(game.gamestate["activePlayerColor"][0])
                        message = f"{player['player_name']}, this is a gentle reminder to end your turn."
                        await actions_channel.send(message)
                        game.initilizeKey("20MinReminder")

    async def shutdown(self) -> None:
        await self.close()


class AdminCommands(commands.Cog):
    def __init__(self, bot: DiscordBot):
        self.bot = bot

    @app_commands.command(name='shutdown', description='Shuts down the bot.')
    async def shutdown_command(self, interaction: discord.Interaction):
        userID = str(interaction.user.id)

        if userID != "488681163146133504" and userID != "265561667293675521":
            await interaction.response.send_message("You are not authorised to use this command.")
            return
        await interaction.response.send_message("Shutting down the bot...")
        await self.bot.shutdown()


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
bot = DiscordBot(command_prefix="$", intents=discord.Intents.all())

bot.run(config.token)
