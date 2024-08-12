import discord
import re
from discord import Interaction
from discord._types import ClientT
from discord.ext import commands
from discord.ui import View, Button
import Buttons.TurnButtonsOld
from helpers.GamestateHelper import GamestateHelper
from helpers.PlayerHelper import PlayerHelper

class BuildLocation(discord.ui.DynamicItem[discord.ui.Button], template=r'location:(?P<location>[0-9]+)'):
    def __init__(self, location, style:discord.ButtonStyle.primary, author):
        super().__init__(
            discord.ui.Button(
                label=location,
                style=style,
                custom_id=f'location:{str(location)}',
            )
        )
        self.author = author
    @classmethod
    async def from_custom_id(self, interaction: discord.Interaction, item: discord.ui.Button, match: re.Match[str], /):
        await interaction.response.defer(thinking=True)
        game = GamestateHelper(interaction.channel)
        p1 = game.get_player(interaction.user.id)
        loc = match['location']
        view = View()
        view = BuildButton.buildButtonsView(interaction,"",0,loc,view)
        await interaction.message.delete()
        await interaction.followup.send(f"{interaction.user.mention}, you have {p1['materials']} materials to "
                                                f"spend on up to {p1['build_apt']} units in this system.", view=view)
    

    # async def callback(self, interaction: discord.Interaction):
    #     game = GamestateHelper(interaction.channel)
    #     p1 = game.get_player(interaction.user.id)
    #     view = Build(interaction, [], 0, self.label, self.author)
    #     await interaction.message.delete()
    #     await interaction.response.send_message(f"{interaction.user.mention}, you have {p1['materials']} materials to "
    #                                             f"spend on up to {p1['build_apt']} units in this system.", view=view)
    async def interaction_check(self, interaction: discord.Interaction):
        if str(interaction.user.id) != str(self.author):
            await interaction.response.send_message("These buttons are not for you.")
        else:
            return True

class BuildButton(discord.ui.DynamicItem[discord.ui.Button], template=r'b:(?P<build>[a-zA-Z]+):c:(?P<cost>[0-9]+):l:(?P<location>[0-9]+)'):
    def __init__(self, interaction: discord.Interaction, ship: str, build: str, loc: str, cost: int = 0) -> None:
        game = GamestateHelper(interaction.channel)
        p1 = game.get_player(interaction.user.id)
        key = f"cost_{ship.lower()}"
        if ship.lower() == "dreadnought":
            key = f"cost_dread"
        super().__init__(
            discord.ui.Button(
                label=f"{ship} ({p1[f'{key}']})",
                style=discord.ButtonStyle.primary,
                custom_id=f'b:{build}:c:{str(cost)}:l:{loc}:s:{ship}',
            )
        )
    @staticmethod
    def buildButtonsView(interaction: discord.Interaction, build: str, cost, build_loc, view: View):
        ships = ["Interceptor","Cruiser","Dreadnought","Starbase","Orbital","Monolith"]
        if build == "":
            build = "none"
        game = GamestateHelper(interaction.channel)
        p1 = game.get_player(interaction.user.id)
        if "stb" not in p1["military_tech"]:
            ships.remove("Starbase")
        if "orb" not in p1["nano_tech"]:
            ships.remove("Orbital")
        if "mon" not in p1["nano_tech"]:
            ships.remove("Monolith")
        for ship in ships:
            button = BuildButton(interaction, ship, build, build_loc, cost)  
            view.add_item(button)  
        return view
    @classmethod
    async def from_custom_id(self, interaction: discord.Interaction, item: discord.ui.Button, match: re.Match[str], /):
        game = GamestateHelper(interaction.channel)
        p1 = game.get_player(interaction.user.id)
        build = match['build'].replace("none","").split(f';')
        
        cost = int(match['cost'])
        loc = match['location']
        ship = str(match['ship'])
        if len(build) == p1["build_apt"]:
            await interaction.response.edit_message(content=f"You cannot build any more units. Current build is:"
                                                            f"\n {build} for {cost} materials.")
            return
        build.append(f"{p1['color']}-{GamestateHelper.getShipFullName(ship)}")
        key = f"cost_{ship.lower()}"
        if ship.lower() == "dreadnought":
            key = f"cost_dread"
        cost += p1[key]
        build.append(ship)
        view = View()
        view = BuildButton.buildButtonsView(interaction,";".join(build),cost,loc,view)
        await interaction.response.edit_message(content=f"Total cost so far of {cost}", view=view)
    
class Build(discord.ui.View):
    def __init__(self, interaction: discord.Interaction, build, cost, build_loc, author):
        super().__init__()
        self.game = GamestateHelper(interaction.channel)
        self.p1 = self.game.get_player(author)
        self.build = build
        self.cost = cost
        self.build_loc = build_loc
        self.author = author
        self.interceptor.label = f"Interceptor ({self.p1['cost_interceptor']})"
        self.cruiser.label = f"Cruiser ({self.p1['cost_cruiser']})"
        self.dreadnought.label = f"Dreadnought ({self.p1['cost_dread']})"
        self.starbase.label = f"Starbase ({self.p1['cost_starbase']})"
        self.orbital.label = f"Orbital ({self.p1['cost_orbital']})"
        self.monolith.label = f"Monolith ({self.p1['cost_monolith']})"

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
        self.build.append(f"{self.p1['color']}-int")
        self.cost += self.p1["cost_interceptor"]
        view = Build(interaction, self.build, self.cost, self.build_loc, self.author)
        await interaction.response.edit_message(content= f"Total cost so far of {self.cost}", view=view)

    @discord.ui.button(style=discord.ButtonStyle.primary)
    async def cruiser(self, interaction: discord.Interaction, button: discord.ui.Button):
        if len(self.build) == self.p1["build_apt"]:
            await interaction.response.edit_message(content=f"You cannot build any more units. Current build is:"
                                                            f"\n {self.build} for {self.cost} materials.")
            return
        self.build.append(f"{self.p1['color']}-cru")
        self.cost += self.p1["cost_cruiser"]
        view = Build(interaction, self.build, self.cost, self.build_loc, self.author)
        await interaction.response.edit_message(content= f"Total cost so far of {self.cost}", view=view)

    @discord.ui.button(style=discord.ButtonStyle.primary)
    async def dreadnought(self, interaction: discord.Interaction, button: discord.ui.Button):
        if len(self.build) == self.p1["build_apt"]:
            await interaction.response.edit_message(content=f"You cannot build any more units. Current build is:"
                                                            f"\n {self.build} for {self.cost} materials.")
            return
        self.build.append(f"{self.p1['color']}-drd")
        self.cost += self.p1["cost_dread"]
        view = Build(interaction, self.build, self.cost, self.build_loc, self.author)
        await interaction.response.edit_message(content=f"Total cost so far of {self.cost}", view=view)

    @discord.ui.button(style=discord.ButtonStyle.success)
    async def starbase(self, interaction: discord.Interaction, button: discord.ui.Button):
        if len(self.build) == self.p1["build_apt"]:
            await interaction.response.edit_message(content=f"You cannot build any more units. Current build is:"
                                                            f"\n {self.build} for {self.cost} materials.")
            return
        self.build.append(f"{self.p1['color']}-sb")
        self.cost += self.p1["cost_starbase"]
        view = Build(interaction, self.build, self.cost, self.build_loc, self.author)
        await interaction.response.edit_message(content=f"Total cost so far of {self.cost}", view=view)

    @discord.ui.button(style=discord.ButtonStyle.success)
    async def orbital(self, interaction: discord.Interaction, button: discord.ui.Button):
        if len(self.build) == self.p1["build_apt"]:
            await interaction.response.edit_message(content=f"You cannot build any more units. Current build is:"
                                                            f"\n {self.build} for {self.cost} materials.")
            return
        self.build.append(f"{self.p1['color']}-orb")
        self.cost += self.p1["cost_orbital"]
        view = Build(interaction, self.build, self.cost, self.build_loc, self.author)
        await interaction.response.edit_message(content=f"Total cost so far of {self.cost}", view=view)

    @discord.ui.button(style=discord.ButtonStyle.success)
    async def monolith(self, interaction: discord.Interaction, button: discord.ui.Button):
        if len(self.build) == self.p1["build_apt"]:
            await interaction.response.edit_message(content=f"You cannot build any more units. Current build is:"
                                                            f"\n {self.build} for {self.cost} materials.")
            return
        self.build.append(f"{self.p1['color']}-mon")
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
                    f"\nAvailable resources: Materials-{self.p1['materials']} Science-{self.p1['science']} Money-{self.p1['money']}", view=view)

    @discord.ui.button(label="Reset", style=discord.ButtonStyle.danger)
    async def reset(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = Build(interaction, [], 0, self.build_loc, self.author)
        await interaction.message.delete()
        await interaction.response.send_message(f"Total cost so far of 0", view=view)

    async def interaction_check(self, interaction: discord.Interaction):
        if str(interaction.user.id) != str(self.author):
            await interaction.response.send_message("These buttons are not for you.")
        else:
            return True

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
        self.convert_science.label = f"Science ({self.p1['trade_value']}:1)"
        self.convert_money.label = f"Money ({self.p1['trade_value']}:1)"
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
        view = Buttons.TurnButtonsOld.Turn(interaction, interaction.user.id)
        await interaction.message.delete()
        await interaction.response.send_message(f"{interaction.user.mention} use these buttons to do your turn. "
                                                f"The number of activations you have for each action is listed in ()", view=view)
    @discord.ui.button(label="Finish Build", style=discord.ButtonStyle.danger)
    async def finish_build(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.game.add_units(self.build, self.build_loc)
        player = PlayerHelper(self.author, self.p1)
        player.stats["science"], player.stats["materials"], player.stats["money"] = self.science, self.material, self.money
        player.spend_influence_on_action("build")
        self.game.update_player(player)
        next_player = self.game.get_next_player(self.p1)
        view = Buttons.TurnButtonsOld.Turn(interaction, next_player)
        await interaction.message.delete()
        await interaction.response.send_message(f"<@{next_player}> use these buttons to do your turn. "
                                                
                                                f"The number of activations you have for each action is listed in ()", view=view)

    async def interaction_check(self, interaction: discord.Interaction):
        if str(interaction.user.id) != str(self.author):
            await interaction.response.send_message("These buttons are not for you.")
        else:
            return True