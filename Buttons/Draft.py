import asyncio
import json
import discord
from discord.ui import View
from Buttons.DiscoveryTile import DiscoveryTileButtons
from helpers.DrawHelper import DrawHelper
from helpers.EmojiHelper import Emoji
from helpers.GamestateHelper import GamestateHelper
from helpers.PlayerHelper import PlayerHelper
from discord.ui import View, Button

class DraftButtons:

    @staticmethod  
    def getInitialShrineButtons(game: GamestateHelper, player):
        0=0