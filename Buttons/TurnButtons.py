import discord
from discord.ext import commands
from discord.ui import View
from helpers.GamestateHelper import GamestateHelper
from helpers.PlayerHelper import PlayerHelper
from Buttons.BuildButtons import Build, BuildLocation
from Buttons.UpgradeButtons import UpgradeShip
from helpers.DrawHelper import DrawHelper

class Turn(discord.ui.View):
    def __init__(self, interaction, player_id):
        super().__init__()
        self.game = GamestateHelper(interaction.channel)
        self.player = self.game.get_player(str(player_id))
        self.author = str(player_id)
        self.explore.label = f"Explore ({self.player['explore_apt']})"
        self.research.label = f"Research ({self.player['research_apt']})"
        self.upgrade.label = f"Upgrade ({self.player['upgrade_apt']})"
        self.build.label = f"Build ({self.player['build_apt']})"
        self.move.label = f"Move ({self.player['move_apt']})"
        self.influence.label = f"Influence ({self.player['influence_apt']})"


    @discord.ui.button(style=discord.ButtonStyle.primary)
    async def explore(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Explore")

    @discord.ui.button(style=discord.ButtonStyle.success)
    async def research(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Research")


    @discord.ui.button(style=discord.ButtonStyle.primary)
    async def upgrade(self, interaction: discord.Interaction, button: discord.ui.Button):
        drawing = DrawHelper(self.game.gamestate)
        image = drawing.player_area(self.player)
        view = UpgradeShip(interaction, self.author)
        await interaction.message.delete()
        await interaction.response.send_message(
            f"{interaction.user.mention}, choose which ship you would like to upgrade.",
            file=drawing.show_player_ship_area(image), view=view, ephemeral=True)

    @discord.ui.button(style=discord.ButtonStyle.success)
    async def build (self, interaction: discord.Interaction, button: discord.ui.Button):
        game = GamestateHelper(interaction.channel)
        tiles = game.get_owned_tiles(interaction.user.id)
        tiles.sort()
        view=View()
        for i in tiles:
            button2 = BuildLocation(i, discord.ButtonStyle.primary, self.author)
            view.add_item(button2)
        await interaction.message.delete()
        await interaction.response.send_message(f"{interaction.user.mention}, choose which tile you would like to build in.", view=view)

    @discord.ui.button(style=discord.ButtonStyle.primary)
    async def move(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Move")

    @discord.ui.button(style=discord.ButtonStyle.success)
    async def influence(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Influence")

    @discord.ui.button(label="Pass", style=discord.ButtonStyle.danger)
    async def pass_turn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Pass")

    async def interaction_check(self, interaction: discord.Interaction):
        if str(interaction.user.id) != str(self.author):
           await interaction.response.send_message("These buttons are not for you.")
        else:
            return True