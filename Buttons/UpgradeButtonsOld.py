import discord
from discord import Interaction
from discord._types import ClientT
from discord.ext import commands
from discord.ui import Button, View
import Buttons.TurnButtonsOld
from helpers.GamestateHelper import GamestateHelper
from helpers.PlayerHelper import PlayerHelper
from helpers.ShipHelper import PlayerShip
from helpers.DrawHelper import DrawHelper
import json

class UpgradeShip(discord.ui.View):
    def __init__(self, interaction: discord.Interaction, author, actions, player):
        super().__init__()
        self.author = author
        self.actions = actions
        self.p1 = player
        with open("data/parts.json", "r") as f:
            self.part_stats = json.load(f)
        if self.actions <= 0:
            self.remove_item(self.interceptor)
            self.remove_item(self.cruiser)
            self.remove_item(self.dreadnought)
            self.remove_item(self.starbase)
    """
    Parameters
    ----------
        author : str
            discord member id (converted to string) to track button author for protection
        player : PlayerHelper() class object
            This will serve as the temporary changes before saving this game to the gamestate when finished
        actions: int
            number of upgrade actions per turn. Will decrement to 0 over the course or upgrading
            and stop the player from doing more actions than possible
    """

    @discord.ui.button(label="Interceptor", style=discord.ButtonStyle.blurple)
    async def interceptor(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = View()
        for i in self.p1.stats["interceptor_parts"]:
            button2 = ShowParts(label=self.part_stats[i]["name"], style=discord.ButtonStyle.blurple,
                                actions=self.actions, author=self.author, player=self.p1,
                                ship="interceptor", old_part=i)
            view.add_item(button2)

        await interaction.response.edit_message(content=f"{interaction.user.mention}, pick which part to replace or "
                                                        f"remove.",
                                                view=view)

    @discord.ui.button(label="Cruiser", style=discord.ButtonStyle.blurple)
    async def cruiser(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = View()
        for i in self.p1.stats["cruiser_parts"]:
            button2 = ShowParts(label=self.part_stats[i]["name"], style=discord.ButtonStyle.blurple,
                                actions=self.actions, author=self.author, player=self.p1,
                                ship="cruiser", old_part=i)
            view.add_item(button2)

        await interaction.response.edit_message(content=f"{interaction.user.mention}, pick which part to replace or "
                                                        f"remove.",
                                                view=view)

    @discord.ui.button(label="Dreadnought", style=discord.ButtonStyle.blurple)
    async def dreadnought(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = View()
        for i in self.p1.stats["dread_parts"]:
            button2 = ShowParts(label=self.part_stats[i]["name"], style=discord.ButtonStyle.blurple,
                                actions=self.actions, author=self.author, player=self.p1,
                                ship="dread", old_part=i)
            view.add_item(button2)

        await interaction.response.edit_message(content=f"{interaction.user.mention}, pick which part to replace or "
                                                        f"remove.",
                                                view=view)

    @discord.ui.button(label="Starbase", style=discord.ButtonStyle.blurple)
    async def starbase(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = View()
        for i in self.p1.stats["starbase_parts"]:
            button2 = ShowParts(label=self.part_stats[i]["name"], style=discord.ButtonStyle.blurple,
                                actions=self.actions, author=self.author, player=self.p1,
                                ship="starbase", old_part=i)
            view.add_item(button2)

        await interaction.response.edit_message(content=f"{interaction.user.mention}, pick which part to replace or "
                                                        f"remove.",
                                                view=view)

    @discord.ui.button(label="Finish Upgrade", style=discord.ButtonStyle.red)
    async def finish_upgrade(self, interaction: discord.Interaction, button: discord.ui.Button):
        ships = ["interceptor", "cruiser", "dread", "starbase"]
        for i in ships:
            ship = PlayerShip(self.p1.stats, i)
            if not ship.check_valid_ship():
                await interaction.response.send_message("One of your ships is not valid! Please reset and try again", ephemeral=True)
                return
        game = GamestateHelper(interaction.channel)
        self.p1.spend_influence_on_action("upgrade")
        game.update_player(self.p1)
        next_player = game.get_next_player(self.p1.stats)
        view = Buttons.TurnButtonsOld.Turn(interaction, next_player)
        await interaction.message.delete()
        await interaction.channel.send(f"{interaction.user.mention} you have upgraded your ships!")


        await interaction.response.send_message(f"<@{next_player["player_name"]}> use these buttons to do your turn. "

                                                f"The number of activations you have for each action is listed in ()",
                                                view=view)

    @discord.ui.button(label="Reset", style=discord.ButtonStyle.red)
    async def reset(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = Buttons.TurnButtonsOld.Turn(interaction, self.author)
        await interaction.message.delete()
        await interaction.response.send_message(f"{interaction.user.mention} use these buttons to do your turn. "
                                                f"The number of activations you have for each action is listed in ()",
                                                view=view)


    async def interaction_check(self, interaction: discord.Interaction):
        if str(interaction.user.id) != str(self.author):
            await interaction.response.send_message("These buttons are not for you.")
        else:
            return True

class ShowParts(Button):
    def __init__(self, label, style:discord.ButtonStyle.blurple, author, actions, player, ship, old_part):
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
            if tech in self.player.stats["military_tech"]:
                self.available_techs.append(tech)
            if tech in self.player.stats["grid_tech"]:
                self.available_techs.append(tech)
            if tech in self.player.stats["nano_tech"]:
                self.available_techs.append(tech)
            if "ancient_parts" in self.player.stats and tech in self.player.stats["ancient_parts"]:
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
            button2 = ChooseUpgrade(label=self.part_stats[i]["name"],style=discord.ButtonStyle.blurple,
                                    author=self.author, actions=self.actions,
                                    player=self.player, ship=self.ship, old_part=self.old_part, new_part=i)
            view.add_item(button2)
        await interaction.response.edit_message(content=f"{interaction.user.mention}, replace "
                                                        f"{self.part_stats[self.old_part]['name']} with "
                                                        f"which part? Remove as a free action by selecting 'Empty'.", view=view)

    async def interaction_check(self, interaction: discord.Interaction):
        if str(interaction.user.id) != str(self.author):
            await interaction.response.send_message("These buttons are not for you.")
        else:
            return True

class ChooseUpgrade(Button):
    def __init__(self, label, style:discord.ButtonStyle.blurple, author, actions, player, ship, old_part, new_part):
        super().__init__(label=label, style=style)
        self.author = author
        self.actions = actions
        self.player = player
        self.ship = ship
        self.old_part = old_part
        self.new_part = new_part

    async def callback(self, interaction: discord.Interaction):
        if self.new_part != "empty":
            self.actions -= 1
        if self.new_part in ["anm", "axc", "cod", "fls", "hyg", "ins", "iod", "iom", "iot", "jud", "mus", "ricon", "shd", "som", "socha"]:
            self.player.stats["ancient_parts"].remove(self.new_part)

        for i,part in enumerate(self.player.stats[f"{self.ship}_parts"]):
            if part == self.old_part:
                self.player.stats[f"{self.ship}_parts"][i] = self.new_part
                break

        view = UpgradeShip(interaction, self.author, self.actions, self.player)
        game = GamestateHelper(interaction.channel)
        drawing = DrawHelper(game.gamestate)
        image = drawing.player_area(self.player.stats)
        await interaction.message.delete()
        await interaction.response.send_message(content=f"{interaction.user.mention}, choose which ship you would like to upgrade.",
            file=drawing.show_player_ship_area(image), view=view)


    async def interaction_check(self, interaction: discord.Interaction):
        if str(interaction.user.id) != str(self.author):
            await interaction.response.send_message("These buttons are not for you.")
        else:
            return True