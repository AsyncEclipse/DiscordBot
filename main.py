import discord
import time
from commands.game_commands import GameCommands
from commands.tile_commands import TileCommands
import config
from discord import app_commands
from commands.setup_commands import SetupCommands
from commands.player_commands import PlayerCommands
from commands.search_commands import SearchCommands
from helpers import ImageCache
from listeners.ButtonListener import ButtonListener
from discord.ext import commands
import logging

class DiscordBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

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
        print(f"Starting to load images")
        imageCache = ImageCache.ImageCacheHelper("images/resources")
        end_time = time.perf_counter()
        elapsed_time = end_time - start_time
        print(f"Total elapsed time for image load: {elapsed_time:.2f} seconds")
        print("Bot is now ready.")
    
    async def shutdown(self)->None:    
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

