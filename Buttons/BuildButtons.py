import discord
from discord import Interaction
from discord._types import ClientT
from discord.ext import commands
from discord.ui import Button
import Buttons.TurnButtons
from helpers.GamestateHelper import GamestateHelper
from helpers.PlayerHelper import PlayerHelper

class BuildLocation(Button):
    def __init__(self, label, style:discord.ButtonStyle.primary, author):
        super().__init__(label=label, style=style)
        self.author = author
    async def callback(self, interaction: discord.Interaction):
        game = GamestateHelper(interaction.channel)
        p1 = game.get_player(interaction.user.id)
        view = Build(interaction, [], 0, self.label, self.author)
        await interaction.message.delete()
        await interaction.response.send_message(f"{interaction.user.mention}, you have {p1["materials"]} materials to "
                                                f"spend on up to {p1["build_apt"]} units in this system.", view=view)
    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user.id != self.author:
            await interaction.response.send_message("These buttons are not for you.")
        else:
            return True

class Build(discord.ui.View):
    def __init__(self, interaction: discord.Interaction, build, cost, build_loc, author):
        super().__init__()
        self.game = GamestateHelper(interaction.channel)
        self.p1 = self.game.get_player(author)
        self.build = build
        self.cost = cost
        self.build_loc = build_loc
        self.author = author
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
        self.build.append(f"{self.p1["color"]}-int")
        self.cost += self.p1["cost_interceptor"]
        view = Build(interaction, self.build, self.cost, self.build_loc, self.author)
        await interaction.response.edit_message(content= f"Total cost so far of {self.cost}", view=view)

    @discord.ui.button(style=discord.ButtonStyle.primary)
    async def cruiser(self, interaction: discord.Interaction, button: discord.ui.Button):
        if len(self.build) == self.p1["build_apt"]:
            await interaction.response.edit_message(content=f"You cannot build any more units. Current build is:"
                                                            f"\n {self.build} for {self.cost} materials.")
            return
        self.build.append(f"{self.p1["color"]}-cru")
        self.cost += self.p1["cost_cruiser"]
        view = Build(interaction, self.build, self.cost, self.build_loc, self.author)
        await interaction.response.edit_message(content= f"Total cost so far of {self.cost}", view=view)

    @discord.ui.button(style=discord.ButtonStyle.primary)
    async def dreadnought(self, interaction: discord.Interaction, button: discord.ui.Button):
        if len(self.build) == self.p1["build_apt"]:
            await interaction.response.edit_message(content=f"You cannot build any more units. Current build is:"
                                                            f"\n {self.build} for {self.cost} materials.")
            return
        self.build.append(f"{self.p1["color"]}-drd")
        self.cost += self.p1["cost_dread"]
        view = Build(interaction, self.build, self.cost, self.build_loc, self.author)
        await interaction.response.edit_message(content=f"Total cost so far of {self.cost}", view=view)

    @discord.ui.button(style=discord.ButtonStyle.success)
    async def starbase(self, interaction: discord.Interaction, button: discord.ui.Button):
        if len(self.build) == self.p1["build_apt"]:
            await interaction.response.edit_message(content=f"You cannot build any more units. Current build is:"
                                                            f"\n {self.build} for {self.cost} materials.")
            return
        self.build.append(f"{self.p1["color"]}-sb")
        self.cost += self.p1["cost_starbase"]
        view = Build(interaction, self.build, self.cost, self.build_loc, self.author)
        await interaction.response.edit_message(content=f"Total cost so far of {self.cost}", view=view)

    @discord.ui.button(style=discord.ButtonStyle.success)
    async def orbital(self, interaction: discord.Interaction, button: discord.ui.Button):
        if len(self.build) == self.p1["build_apt"]:
            await interaction.response.edit_message(content=f"You cannot build any more units. Current build is:"
                                                            f"\n {self.build} for {self.cost} materials.")
            return
        self.build.append(f"{self.p1["color"]}-orb")
        self.cost += self.p1["cost_orbital"]
        view = Build(interaction, self.build, self.cost, self.build_loc, self.author)
        await interaction.response.edit_message(content=f"Total cost so far of {self.cost}", view=view)

    @discord.ui.button(style=discord.ButtonStyle.success)
    async def monolith(self, interaction: discord.Interaction, button: discord.ui.Button):
        if len(self.build) == self.p1["build_apt"]:
            await interaction.response.edit_message(content=f"You cannot build any more units. Current build is:"
                                                            f"\n {self.build} for {self.cost} materials.")
            return
        self.build.append(f"{self.p1["color"]}-mon")
        self.cost += self.p1["cost_monolith"]
        view = Build(interaction, self.build, self.cost, self.build_loc, self.author)
        await interaction.response.edit_message(content=f"Total cost so far of {self.cost}", view=view)

    @discord.ui.button(label="Finished", style=discord.ButtonStyle.danger)
    async def finished(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = BuildPay(interaction, build=self.build, cost=self.cost, build_loc=self.build_loc,
                        resources=[self.p1["materials"], self.p1["science"], self.p1["money"]],
                        spent=0, author=self.author)
        await interaction.message.delete()
        await interaction.response.send_message(f"Total cost: {self.cost}"
                    f"\nAvailable resources: Materials-{self.p1["materials"]} Science-{self.p1["science"]} Money-{self.p1["money"]}", view=view)

    @discord.ui.button(label="Reset", style=discord.ButtonStyle.danger)
    async def reset(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = Build(interaction, [], 0, self.build_loc, self.author)
        await interaction.message.delete()
        await interaction.response.send_message(f"Total cost so far of 0", view=view)

class BuildPay(discord.ui.View):
    def __init__(self, interaction: discord.Interaction, build, cost, build_loc, resources, spent, author):
        super().__init__()
        self.game = GamestateHelper(interaction.channel)
        self.p1 = self.game.get_player(author)
        self.build = build
        self.cost = cost
        self.build_loc = build_loc
        self.material, self.science, self.money = resources
        self.spent = spent
        self.convert_science.label = f"Science ({self.p1["trade_value"]}:1)"
        self.convert_money.label = f"Money ({self.p1["trade_value"]}:1)"
        self.author = author
        if self.material == 0:
            self.remove_item(self.one_material)
        if self.material < 2:
            self.remove_item(self.two_material)
        if (self.science / self.p1["trade_value"]) < 1:
            self.remove_item(self.convert_science)
        if (self.money / self.p1["trade_value"]) < 1:
            self.remove_item(self.convert_money)
        if self.spent < self.cost:
            self.remove_item(self.finish_build)

    @discord.ui.button(label="Material (1)",style=discord.ButtonStyle.primary)
    async def one_material(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.spent += 1
        self.material -= 1
        view = BuildPay(interaction, self.build, self.cost, self.build_loc,
                        [self.material, self.science, self.money],
                        self.spent, self.author)

        await interaction.response.edit_message(content=f"Total cost: {self.cost}"
                    f"\nAvailable resources: Materials-{self.material} Science-{self.science} Money-{self.money}"
                    f"\nResources spent: {self.spent}", view=view)

    @discord.ui.button(label="Materials (2)",style=discord.ButtonStyle.primary)
    async def two_material(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.spent += 2
        self.material -= 2
        view = BuildPay(interaction, self.build, self.cost, self.build_loc,
                        [self.material, self.science, self.money],
                        self.spent, self.author)

        await interaction.response.edit_message(content=f"Total cost: {self.cost}"
                    f"\nAvailable resources: Materials-{self.material} Science-{self.science} Money-{self.money}"
                    f"\nResources spent: {self.spent}", view=view)

    @discord.ui.button(style=discord.ButtonStyle.secondary)
    async def convert_science(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.spent += 1
        self.science -= self.p1["trade_value"]
        view = BuildPay(interaction, self.build, self.cost, self.build_loc,
                        [self.material, self.science, self.money],
                        self.spent, self.author)
        await interaction.response.edit_message(content=f"Total cost: {self.cost}"
                    f"\nAvailable resources: Materials-{self.material} Science-{self.science} Money-{self.money}"
                    f"\nResources spent: {self.spent}", view=view)

    @discord.ui.button(style=discord.ButtonStyle.secondary)
    async def convert_money(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.spent += 1
        self.money -= self.p1["trade_value"]
        view = BuildPay(interaction, self.build, self.cost, self.build_loc,
                        [self.material, self.science, self.money],
                        self.spent, self.author)
        await interaction.response.edit_message(content=f"Total cost: {self.cost}"
                    f"\nAvailable resources: Materials-{self.material} Science-{self.science} Money-{self.money}"
                    f"\nResources spent: {self.spent}", view=view)

    @discord.ui.button(label="Reset", style=discord.ButtonStyle.danger)
    async def reset(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = Buttons.TurnButtons.Turn(interaction, interaction.user.id)
        await interaction.message.delete()
        await interaction.response.send_message(f"{interaction.user.mention} use these buttons to do your turn. "
                                                f"The number of activations you have for each action is listed in ()", view=view)
    @discord.ui.button(label="Finish Build", style=discord.ButtonStyle.danger)
    async def finish_build(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.game.add_units(self.build, self.build_loc)
        self.p1["science"], self.p1["materials"], self.p1["money"] = self.science, self.material, self.money
        self.game.gamestate["players"][str(self.author)] = self.p1
        self.game.update()
        #TODO make sure player ship stock is reduced somehow. Risky to do it directly with add_units
        # because self.p1 will not be changed and will overwrite.
        view = Buttons.TurnButtons.Turn(interaction, self.author)
        await interaction.message.delete()
        await interaction.response.send_message(f"{interaction.user.mention} use these buttons to do your turn. "
                                                f"The number of activations you have for each action is listed in ()", view=view)

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user.id != self.author:
            await interaction.response.send_message("These buttons are not for you.")
        else:
            return True