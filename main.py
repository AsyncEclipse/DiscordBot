import discord
import time
from commands.tile_commands import TileCommands
import config
from commands.setup_commands import SetupCommands
from commands.player_commands import PlayerCommands
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
        await self.tree.sync()
        start_time = time.perf_counter()
        print(f"Starting to load images")
        imageCache = ImageCache.ImageCacheHelper("images/resources")
        end_time = time.perf_counter()
        elapsed_time = end_time - start_time
        print(f"Total elapsed time for image load: {elapsed_time:.2f} seconds")
        print("Bot is now ready.")

logging.basicConfig(level=logging.INFO)  
logger = logging.getLogger(__name__)  

intents = discord.Intents.default()  
intents.messages = True  
intents.message_content = True    
bot = DiscordBot(command_prefix="$", intents=discord.Intents.all())

@bot.event  
async def on_command_error(ctx, error):  
    logger.error(f'Error in command {ctx.command}: {error}')  
    
    log_channel = discord.utils.get(ctx.guild.channels, name="bot-log")  
    
    if log_channel is not None and isinstance(log_channel, discord.TextChannel):  
        await log_channel.send(f'Error in command {ctx.command}: {error}')  
    else:  
        logger.warning(f'Log channel "bot-log" not found.') 

bot.run(config.token)

