import discord
from discord.ext import commands
from helpers.GamestateHelper import GamestateHelper
from helpers.PlayerHelper import PlayerHelper

class Build(discord.ui.View):
    def __init__(self, interaction, build, cost):
        super().__init__()
        self.game = GamestateHelper(interaction.channel)
        self.p1 = self.game.get_player(interaction.user.id)
        self.build = build
        self.cost = cost
        self.interceptor.label = f"Interceptor ({self.p1["cost_interceptor"]})"
        self.cruiser.label = f"Cruiser ({self.p1["cost_cruiser"]})"
        self.dreadnought.label = f"Dreadnought ({self.p1["cost_dread"]})"
        self.starbase.label = f"Starbase ({self.p1["cost_starbase"]})"
        self.orbital.label = f"Orbital ({self.p1["cost_orbital"]})"
        self.monolith.label = f"Monolith ({self.p1["cost_monolith"]})"

        if "stb" not in self.p1["military_tech"]:
            self.remove_item(self.starbase)
        if "orb" not in self.p1["nano_tech"]:
            self.remove_item(self.orbital)
        if "mon" not in self.p1["nano_tech"]:
            self.remove_item(self.monolith)

    @discord.ui.button(style=discord.ButtonStyle.primary)
    async def interceptor(self, interaction: discord.Interaction, button: discord.ui.Button):
        if len(self.build) == self.p1["build_apt"]:
            await interaction.response.edit_message(content=f"You cannot build any more units. Current build is:"
                                                            f"\n {self.build} for {self.cost} materials.")
            return
        self.build.append([f"{self.p1["color"]}_int"])
        self.cost += self.p1["cost_interceptor"]
        view = Build(interaction, self.build, self.cost)
        await interaction.response.edit_message(content= f"Total cost so far of {self.cost}", view=view)

    @discord.ui.button(style=discord.ButtonStyle.primary)
    async def cruiser(self, interaction: discord.Interaction, button: discord.ui.Button):
        if len(self.build) == self.p1["build_apt"]:
            await interaction.response.edit_message(content=f"You cannot build any more units. Current build is:"
                                                            f"\n {self.build} for {self.cost} materials.")
            return
        self.build.append([f"{self.p1["color"]}_cru"])
        self.cost += self.p1["cost_cruiser"]
        view = Build(interaction, self.build, self.cost)
        await interaction.response.edit_message(content= f"Total cost so far of {self.cost}", view=view)

    @discord.ui.button(style=discord.ButtonStyle.primary)
    async def dreadnought(self, interaction: discord.Interaction, button: discord.ui.Button):
        if len(self.build) == self.p1["build_apt"]:
            await interaction.response.edit_message(content=f"You cannot build any more units. Current build is:"
                                                            f"\n {self.build} for {self.cost} materials.")
            return
        self.build.append([f"{self.p1["color"]}_drd"])
        self.cost += self.p1["cost_dread"]
        view = Build(interaction, self.build, self.cost)
        await interaction.response.edit_message(content=f"Total cost so far of {self.cost}", view=view)

    @discord.ui.button(style=discord.ButtonStyle.success)
    async def starbase(self, interaction: discord.Interaction, button: discord.ui.Button):
        if len(self.build) == self.p1["build_apt"]:
            await interaction.response.edit_message(content=f"You cannot build any more units. Current build is:"
                                                            f"\n {self.build} for {self.cost} materials.")
            return
        self.build.append([f"{self.p1["color"]}_sb"])
        self.cost += self.p1["cost_starbase"]
        view = Build(interaction, self.build, self.cost)
        await interaction.response.edit_message(content=f"Total cost so far of {self.cost}", view=view)

    @discord.ui.button(style=discord.ButtonStyle.success)
    async def orbital(self, interaction: discord.Interaction, button: discord.ui.Button):
        if len(self.build) == self.p1["build_apt"]:
            await interaction.response.edit_message(content=f"You cannot build any more units. Current build is:"
                                                            f"\n {self.build} for {self.cost} materials.")
            return
        self.build.append([f"{self.p1["color"]}_orb"])
        self.cost += self.p1["cost_orbital"]
        view = Build(interaction, self.build, self.cost)
        await interaction.response.edit_message(content=f"Total cost so far of {self.cost}", view=view)

    @discord.ui.button(style=discord.ButtonStyle.success)
    async def monolith(self, interaction: discord.Interaction, button: discord.ui.Button):
        if len(self.build) == self.p1["build_apt"]:
            await interaction.response.edit_message(content=f"You cannot build any more units. Current build is:"
                                                            f"\n {self.build} for {self.cost} materials.")
            return
        self.build.append([f"{self.p1["color"]}_mon"])
        self.cost += self.p1["cost_monolith"]
        view = Build(interaction, self.build, self.cost)
        await interaction.response.edit_message(content=f"Total cost so far of {self.cost}", view=view)

    @discord.ui.button(label="Finished", style=discord.ButtonStyle.danger)
    async def finished(self, interaction: discord.Interaction, button: discord.ui.Button):
        pass

    @discord.ui.button(label="Reset", style=discord.ButtonStyle.danger)
    async def reset(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = Build(interaction, [], 0)
        await interaction.message.delete()
        await interaction.response.send_message(f"Build up to {self.p1["build_apt"]} ships.", view=view)