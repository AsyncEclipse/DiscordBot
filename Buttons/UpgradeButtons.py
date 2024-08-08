import discord
from discord import Interaction
from discord._types import ClientT
from discord.ext import commands
from discord.ui import Button, View
import Buttons.TurnButtons
from helpers.GamestateHelper import GamestateHelper
from helpers.PlayerHelper import PlayerHelper
from helpers.ShipHelper import PlayerShip
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
                                actions=self.actions, author=self.author, player=self.p1,
                                ship="interceptor", old_part=i)
            view.add_item(button2)

        await interaction.response.edit_message(content=f"{interaction.user.mention}, pick which part to replace or "
                                                        f"remove.",
                                                view=view)

    @discord.ui.button(label="Cruiser", style=discord.ButtonStyle.primary)
    async def cruiser(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = View()
        for i in self.p1.stats["cruiser_parts"]:
            button2 = ShowParts(label=self.part_stats[i]["name"], style=discord.ButtonStyle.primary,
                                actions=self.actions, author=self.author, player=self.p1,
                                ship="cruiser", old_part=i)
            view.add_item(button2)

        await interaction.response.edit_message(content=f"{interaction.user.mention}, pick which part to replace or "
                                                        f"remove.",
                                                view=view)

    @discord.ui.button(label="Dreadnought", style=discord.ButtonStyle.primary)
    async def dreadnought(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = View()
        for i in self.p1.stats["dread_parts"]:
            button2 = ShowParts(label=self.part_stats[i]["name"], style=discord.ButtonStyle.primary,
                                actions=self.actions, author=self.author, player=self.p1,
                                ship="dread", old_part=i)
            view.add_item(button2)

        await interaction.response.edit_message(content=f"{interaction.user.mention}, pick which part to replace or "
                                                        f"remove.",
                                                view=view)

    @discord.ui.button(label="Starbase", style=discord.ButtonStyle.primary)
    async def starbase(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = View()
        for i in self.p1.stats["starbase_parts"]:
            button2 = ShowParts(label=self.part_stats[i]["name"], style=discord.ButtonStyle.primary,
                                actions=self.actions, author=self.author, player=self.p1,
                                ship="starbase", old_part=i)
            view.add_item(button2)

        await interaction.response.edit_message(content=f"{interaction.user.mention}, pick which part to replace or "
                                                        f"remove.",
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
        self.available_techs = ["empty", "ioc", "elc", "nud", "hul", "gas", "nus"]
        with open("data/parts.json", "r") as f:
            self.part_stats = json.load(f)
        for tech in self.part_stats:
            if tech in (self.player.stats["military_tech"] or self.player.stats["grid_tech"] or self.player.stats["nano_tech"]):
                self.available_techs.append(tech)

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

    async def callback(self, interaction: discord.Interaction):
        view = View()
        for i in self.available_techs:
            button2 = ChooseUpgrade(label=self.part_stats[i]["name"],style=discord.ButtonStyle.primary,
                                    author=self.author, actions=self.actions,
                                    player=self.player, ship=self.ship, old_part=self.old_part, new_part=i)
            view.add_item(button2)
        await interaction.response.edit_message(content=f"{interaction.user.mention}, replace "
                                                        f"{self.part_stats[self.old_part]['name']} with "
                                                        f"which part? Remove as a free action with Empty.", view=view)

    async def interaction_check(self, interaction: discord.Interaction):
        if str(interaction.user.id) != str(self.author):
            await interaction.response.send_message("These buttons are not for you.")
        else:
            return True

class ChooseUpgrade(Button):
    def __init__(self, label, style:discord.ButtonStyle.primary, author, actions, player, ship, old_part, new_part):
        super().__init__(label=label, style=style)
        self.author = author
        self.actions = actions
        self.player = player
        self.ship = ship
        self.old_part = old_part
        self.new_part = new_part

    async def callback(self, interaction: discord.Interaction):
        for i,part in enumerate(self.player.stats[f"{self.ship}_parts"]):
            if part == self.old_part:
                self.player.stats[f"{self.ship}_parts"][i] = self.new_part
        ship = PlayerShip(self.player.stats, self.ship)
        if ship.check_valid_ship():
            await interaction.response.send_message(f'{self.new_part}, {self.player.stats["cruiser_parts"]}')
        else:
            await interaction.response.send_message("That is not a valid ship configuration!")
    async def interaction_check(self, interaction: discord.Interaction):
        if str(interaction.user.id) != str(self.author):
            await interaction.response.send_message("These buttons are not for you.")
        else:
            return True