import discord
from discord import Interaction
from discord._types import ClientT
from discord.ext import commands
from discord.ui import Button, View
import Buttons.TurnButtons
from helpers.GamestateHelper import GamestateHelper
from helpers.PlayerHelper import PlayerHelper
import json

class UpgradeShip(discord.ui.View):
    def __init__(self, interaction: discord.Interaction, author, actions):
        super().__init__()
        self.author = author
        self.actions = actions
        self.game = GamestateHelper(interaction.channel)
        self.p1 = PlayerHelper(self.author, self.game.get_player(self.author))
        with open("data/parts.json", "r") as f:
            self.part_stats = json.load(f)
    """
    Parameters
    ----------
        author : str
            discord member id (converted to string) to track button author for protection
        actions: int
            number of upgrade actions per turn. Will decrement to 0 over the course or upgrading
            and stop the player from doing more actions than possible
    """

    @discord.ui.button(label="Interceptor", style=discord.ButtonStyle.primary)
    async def interceptor(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = View()
        for i in self.p1.stats["interceptor_parts"]:
            button2 = ShowParts(label=self.part_stats[i]["name"], style=discord.ButtonStyle.primary,
                                author=self.author, player=self.p1, ship="interceptor", part=i)
            view.add_item(button2)

        await interaction.response.edit_message(content=f"{interaction.user.mention}, pick which part to replace",
                                                view=view)

    @discord.ui.button(label="Cruiser", style=discord.ButtonStyle.primary)
    async def cruiser(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = View()
        for i in self.p1.stats["cruiser_parts"]:
            button2 = ShowParts(label=self.part_stats[i]["name"], style=discord.ButtonStyle.primary,
                                author=self.author, player=self.p1, ship="cruiser", part=i)
            view.add_item(button2)

        await interaction.response.edit_message(content=f"{interaction.user.mention}, pick which part to replace",
                                                view=view)

    @discord.ui.button(label="Dreadnought", style=discord.ButtonStyle.primary)
    async def dreadnought(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = View()
        for i in self.p1.stats["dread_parts"]:
            button2 = ShowParts(label=self.part_stats[i]["name"], style=discord.ButtonStyle.primary,
                                author=self.author, player=self.p1, ship="dread", part=i)
            view.add_item(button2)

        await interaction.response.edit_message(content=f"{interaction.user.mention}, pick which part to replace",
                                                view=view)

    @discord.ui.button(label="Starbase", style=discord.ButtonStyle.primary)
    async def starbase(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = View()
        for i in self.p1.stats["starbase_parts"]:
            button2 = ShowParts(label=self.part_stats[i]["name"], style=discord.ButtonStyle.primary,
                                author=self.author, player=self.p1, ship="starbase", part=i)
            view.add_item(button2)

        await interaction.response.edit_message(content=f"{interaction.user.mention}, pick which part to replace",
                                                view=view)


    async def interaction_check(self, interaction: discord.Interaction):
        if str(interaction.user.id) != str(self.author):
           await interaction.response.send_message("These buttons are not for you.")
        else:
            return True

class ShowParts(Button):
    def __init__(self, label, style:discord.ButtonStyle.primary, author, actions, player, ship, old_part):
        super().__init__(label=label, style=style)
        self.author = author
        self.actions = actions
        self.player = player
        self.ship = ship
        self.old_part = old_part
    """
    Parameters
    ----------
        author : str
            discord member id (converted to string) to track button author for protection
        player : PlayerHelper() class object
            This will serve as the temporary changes before saving this game to the gamestate when finished
        ship: str
            Ship type to be modified. interceptor, cruiser, dread, starbase are the options
        old_part: str
            String matching the part to change in the ship part list
    """

    async def callback(self, intraction: discord.Interaction):
        pass

    async def interaction_check(self, interaction: discord.Interaction):
        if str(interaction.user.id) != str(self.author):
            await interaction.response.send_message("These buttons are not for you.")
        else:
            return True

class ChooseUpgrade(Button)