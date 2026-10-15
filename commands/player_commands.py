import asyncio
import discord
import json
from discord.ext import commands
from discord import app_commands
from typing import Optional
from Buttons.DiplomaticRelations import DiplomaticRelationsButtons
from Buttons.Move import MoveButtons
from Buttons.Reputation import ReputationButtons
from Buttons.Research import ResearchButtons
from Buttons.Turn import TurnButtons
from Buttons.Upgrade import UpgradeButtons
from helpers.PlayerHelper import PlayerHelper
from helpers.GamestateHelper import GamestateHelper
from helpers.DrawHelper import DrawHelper
from discord.ui import View, Button


class PlayerCommands(commands.GroupCog, name="player"):
    def __init__(self, bot):
        self.bot = bot

    color_choices = [
        app_commands.Choice(name="Blue", value="blue"),
        app_commands.Choice(name="Red", value="red"),
        app_commands.Choice(name="Yellow", value="yellow"),
        app_commands.Choice(name="Purple", value="purple"),
        app_commands.Choice(name="Green", value="green"),
        app_commands.Choice(name="White", value="white"),
        app_commands.Choice(name="Pink", value="pink"),
        app_commands.Choice(name="Teal", value="teal"),
        app_commands.Choice(name="Brown", value="brown")
    ]

    ship_choices = [
        app_commands.Choice(name="Interceptor", value="interceptor"),
        app_commands.Choice(name="Cruiser", value="cruiser"),
        app_commands.Choice(name="Dreadnought", value="dread"),
        app_commands.Choice(name="Starbase", value="starbase"),
        app_commands.Choice(name="Orbital", value="orb")
    ]

    @app_commands.command(name="stats", description="Anything to do with player stats")
    async def stats(self, interaction: discord.Interaction,
                    materials: Optional[int],
                    science: Optional[int],
                    money: Optional[int],
                    material_cubes: Optional[int],
                    science_cubes: Optional[int],
                    money_cubes: Optional[int],
                    discovery_tiles_kept: Optional[int],
                    influence: Optional[int],
                    colony_ships: Optional[int],mag_points: Optional[int], player: Optional[discord.Member] = None):
        """

        :param materials: Materials resource count - may use +1/-1 to add/subtract
        :param science: Science resource count - may use +1/-1 to add/subtract
        :param money: Money resource count - may use +1/-1 to add/subtract
        :param influence: Influence disc count - may use +1/-1 to add/subtract
        :param material_cubes: Material cube count - may use +1/-1 to add/subtract
        :param science_cubes: Science cube count - may use +1/-1 to add/subtract
        :param money_cubes: Money cube count - may use +1/-1 to add/subtract
        :param influence: Influence disc count - may use +1/-1 to add/subtract
        :param colony_ships: Ready colony ship count - may use +1/-1 to add/subtract
        :param mag_points: Points for Magellan kept parts - may use +1/-1 to add/subtract
        :return:
        """
        if player is None:
            player = interaction.user
        gamestate = GamestateHelper(interaction.channel)
        p1 = PlayerHelper(player.id, gamestate.get_player(player.id))
        options = [materials, science, money, material_cubes, science_cubes, money_cubes,
                   influence, colony_ships, discovery_tiles_kept, mag_points]

        if all(x is None for x in options):
            top_response = (f"{p1.name} player stats:")
            response = "\n".join([f"> Faction: {p1.stats['name']}",
                                 f"> Materials: {p1.stats['materials']}",
                                 f"> Material income: {p1.materials_income()}",
                                 f"> Science: {p1.stats['science']}",
                                 f"> Science income: {p1.science_income()}",
                                 f"> Money: {p1.stats['money']}",
                                 f"> Money income: {p1.money_income()}",
                                 f"> Influence dics: {p1.stats['influence_discs']}",
                                 f"> Upkeep: {p1.upkeepCosts()}",
                                 f"> Colony Ships: {p1.stats['colony_ships']}",
                                 f"> Perma_Passed: {p1.stats.get('perma_passed','False')}",
                                 f"> Discovery Tiles Kept For Points: {p1.stats.get('disc_tiles_for_points','0')}"])
            await interaction.response.send_message(top_response)
            await interaction.channel.send(response)
            return
        else:
            pass

        top_response = f"{p1.name} made the following changes:"
        response = ""

        if materials:
            response += (p1.adjust_materials(materials))
        if science:
            response += (p1.adjust_science(science))
        if money:
            response += (p1.adjust_money(money))
        if material_cubes:
            response += (p1.adjust_material_cube(material_cubes))
        if science_cubes:
            response += (p1.adjust_science_cube(science_cubes))
        if money_cubes:
            response += (p1.adjust_money_cube(money_cubes))
        if influence:
            response += (p1.adjust_influence(influence))
        if mag_points:
            response += (p1.adjust_mag_points(mag_points))
        if colony_ships:
            before = p1.stats['colony_ships']
            p1.adjust_colony_ships(-colony_ships)
            response += f"\n> Adjusted colony ships from {str(before)} to {str(p1.stats['colony_ships'])}"
        if discovery_tiles_kept:
            if 'disc_tiles_for_points' not in p1.stats:
                p1.stats['disc_tiles_for_points'] = 0
            before = p1.stats['disc_tiles_for_points']
            p1.modify_disc_tile_for_points(discovery_tiles_kept)
            response += ("\n> Adjusted the number of discovery tiles kept for points from"
                         f" {str(before)} to {str(p1.stats['disc_tiles_for_points'])}")

        gamestate.update_player(p1)
        await interaction.response.send_message(top_response)
        await interaction.channel.send(response)

    @app_commands.command(name="remove_tech")
    async def remove_tech(self, interaction: discord.Interaction, tech: str):
        """:param tech: The ID of the tech to be removed. Type help to get a list of your tech IDs"""
        game = GamestateHelper(interaction.channel)
        player = game.get_player(interaction.user.id, interaction)
        player_helper = PlayerHelper(game.get_player_from_color(player["color"]), player)
        with open("data/techs.json", "r") as f:
            tech_data = json.load(f)
        tech_details = tech_data.get(tech)
        if tech_details is None:
            msg = "Your tech ids are the following: \n"
            for tech2 in player_helper.getTechs():
                msg += tech2 + " = " + tech_data.get(tech2)["name"] + "\n"
            await interaction.response.send_message(msg)
            return
        else:
            game.playerReturnTech(player_helper.player_id, tech, player_helper.getTechType(tech))
            await interaction.response.send_message("Successfully returned " + tech_details["name"])

    @app_commands.command(name="remove_ancient_might")
    async def remove_ancient_might(self, interaction: discord.Interaction):
        game = GamestateHelper(interaction.channel)  
        player = game.get_player(interaction.user.id, interaction)
        game.playerRemoveAncientMight(game.get_player_from_color(player["color"]))
        await interaction.response.send_message("Successfully removed ancient might")

    actionChoices = [app_commands.Choice(name="Explore", value="explore"),
                     app_commands.Choice(name="Build", value="build"),
                     app_commands.Choice(name="Upgrade", value="upgrade"),
                     app_commands.Choice(name="Influence", value="influence"),
                     app_commands.Choice(name="Research", value="research"),
                     app_commands.Choice(name="Move", value="move")]

    @app_commands.command(name="adjust_actions")
    @app_commands.choices(action=actionChoices)
    async def adjust_actions(self, interaction: discord.Interaction, amount_to_change: int,
                             action: app_commands.Choice[str], player: Optional[discord.Member] = None):
        game = GamestateHelper(interaction.channel)
        if player is None:
            player = interaction.user
        gamestate = GamestateHelper(interaction.channel)
        player_helper = PlayerHelper(player.id, gamestate.get_player(player.id))
        player_helper.adjust_influence_on_action(action.value, amount_to_change)
        game.update_player(player_helper)
        message = f"{player.mention} adjusted action disks for {action.value} by {amount_to_change}."
        await interaction.response.send_message(message)

    @app_commands.command(name="research")
    async def research(self, interaction: discord.Interaction):
        game = GamestateHelper(interaction.channel)
        player = game.get_player(interaction.user.id,interaction)
        player_helper = PlayerHelper(game.get_player_from_color(player["color"]), player)
        await interaction.response.defer(thinking=False)
        await ResearchButtons.startResearch(game, player, player_helper, interaction, False)

    @app_commands.command(name="change_player")
    @app_commands.choices(color=color_choices)
    async def change_player(self, interaction: discord.Interaction, color: app_commands.Choice[str], new_player: discord.Member):
        game = GamestateHelper(interaction.channel)
        player = None
        for p2 in game.gamestate["players"]:
            if game.gamestate["players"][p2]["color"] == color.value:
                player = p2
        if player != None:
            game.change_player(player, new_player.id, new_player.display_name, new_player.mention)
        await interaction.response.defer(thinking=False)
        drawing = DrawHelper(game.gamestate)
        await interaction.followup.send("Successfully changed player owner to " + new_player.display_name,
                                        file=await asyncio.to_thread(drawing.show_game))

    @app_commands.command(name="change_color")
    @app_commands.choices(color=color_choices)
    async def change_color(self, interaction: discord.Interaction, color: app_commands.Choice[str]):
        game = GamestateHelper(interaction.channel)
        player = game.get_player(interaction.user.id,interaction)
        for p2 in game.gamestate["players"]:
            if game.gamestate["players"][p2]["color"] == color.value:
                await interaction.channel.send("Another player already uses that color")
                return

        game.changeColor(player["color"], color.value)
        await interaction.response.defer(thinking=False)
        drawing = DrawHelper(game.gamestate)
        await interaction.followup.send("Successfully changed color to " + color.value,
                                        file=await asyncio.to_thread(drawing.show_game))

    @app_commands.command(name="upgrade")
    async def upgrade(self, interaction: discord.Interaction):
        game = GamestateHelper(interaction.channel)
        player = game.get_player(interaction.user.id,interaction)
        await interaction.response.defer(thinking=False)
        await UpgradeButtons.startUpgrade(game, player, interaction, False, "dummy","dum")

    @app_commands.command(name="ship_parts", description="Show or change your ship parts for free")
    @app_commands.choices(ship=ship_choices)
    async def ship_parts(self, interaction: discord.Interaction,
                         ship: Optional[app_commands.Choice[str]] = None,
                         slot: Optional[int] = None,
                         part: Optional[str] = None):
        """

        :param ship: Which ship to change. Leave empty to pick from all your ships
        :param slot: The slot to change, counting from 1. Leave empty to pick it from buttons
        :param part: Three letter code of the part to fit. Give an unknown code for the full part list
        """
        game = GamestateHelper(interaction.channel)
        player = game.get_player(interaction.user.id, interaction)
        if player is None:
            await interaction.response.send_message("You are not a player in this game.")
            return
        await interaction.response.defer(thinking=False)
        player_helper = PlayerHelper(game.get_player_from_color(player["color"]), player)
        with open("data/parts.json", "r") as f:
            part_stats = json.load(f)
        if part is not None and part.lower() not in part_stats:
            catalog = [f"> {code} = {details['name']}" for code, details in part_stats.items()]
            await interaction.followup.send("Every ship part code:")
            for start in range(0, len(catalog), 20):
                await interaction.channel.send("\n".join(catalog[start:start + 20]))
            return
        if ship is None:
            if slot is not None or part is not None:
                await interaction.followup.send("Give me the ship you want to change.")
                return
            await UpgradeButtons.startUpgrade(game, player, interaction, False, "free", "1")
            return

        ship_name = ship.value
        if ship_name not in game.getShipsWithParts(player):
            await interaction.followup.send(f"Your faction has no {ship_name}.")
            return
        player_helper.renameOldExileParts(ship_name)
        parts = player[f"{ship_name}_parts"]
        if slot is not None and not 1 <= slot <= len(parts):
            await interaction.followup.send(f"Your {ship_name} has {len(parts)} slots, numbered 1 to {len(parts)}.")
            return
        new_part = part.lower() if part is not None else None
        if new_part is not None and new_part not in player_helper.getAvailableShipParts():
            await interaction.followup.send(f"You cannot fit a {part_stats[new_part]['name']}, "
                                            "you do not have the tech or discovery tile for it.")
            return
        if new_part == "mus":
            await interaction.followup.send("A Muon Source is fitted by a discovery tile, "
                                            "it cannot be swapped into an existing slot.")
            return

        drawing = DrawHelper(game.gamestate)
        image = await asyncio.to_thread(drawing.player_area, player)
        await interaction.followup.send(file=await asyncio.to_thread(drawing.show_player_ship,
                                                                     image, ship_name, player["name"]))
        player_helper.setOldShipParts(ship_name)
        game.update_player(player_helper)
        if new_part is None and slot is None:
            await UpgradeButtons.upgradeShip(game, player, interaction, f"upgradeShip_1_{ship_name}_free",
                                             player_helper)
        elif new_part is None:
            old_part = parts[slot - 1]
            await UpgradeButtons.selectOldPart(game, player, interaction,
                                               f"selectOldPart_1_{ship_name}_{old_part}_free_{slot - 1}",
                                               player_helper)
        elif slot is not None:
            await UpgradeButtons.chooseUpgrade(game, player, interaction,
                                               f"chooseUpgrade_1_{ship_name}_{parts[slot - 1]}_{new_part}_"
                                               f"{slot - 1}_free", player_helper)
        else:
            view = View()
            for index, old_part in enumerate(parts):
                view.add_item(Button(label=f"{index + 1}. {part_stats[old_part]['name']}",
                                     style=discord.ButtonStyle.red,
                                     custom_id=(f"FCID{player['color']}_chooseUpgrade_1_{ship_name}_"
                                                f"{old_part}_{new_part}_{index}_free")))
            await interaction.channel.send(f"{interaction.user.mention}, which part of your {ship_name} should "
                                           f"the {part_stats[new_part]['name']} replace?", view=view)

    @ship_parts.autocomplete("part")
    async def ship_parts_part_autocomplete(self, interaction: discord.Interaction, current: str):
        game = GamestateHelper(interaction.channel)
        player = game.get_player(interaction.user.id, interaction)
        if player is None:
            return []
        with open("data/parts.json", "r") as f:
            part_stats = json.load(f)
        names = {code: part_stats[code]["name"] for code in PlayerHelper("", player).getAvailableShipParts()}
        return [app_commands.Choice(name=name, value=code) for code, name in sorted(names.items(), key=lambda x: x[1])
                if current.lower() in name.lower() or current.lower() in code][:25]

    @app_commands.command(name="move")
    async def move(self, interaction: discord.Interaction):
        game = GamestateHelper(interaction.channel)
        player = game.get_player(interaction.user.id,interaction)
        await interaction.response.defer(thinking=False)
        await MoveButtons.startMove(game, player, interaction, "startMove_8", False)

    @app_commands.command(name="break_relations")
    @app_commands.choices(color=color_choices)
    async def break_relations(self, interaction: discord.Interaction, color: app_commands.Choice[str]):
        player = interaction.user
        await interaction.response.defer(thinking=False)
        game = GamestateHelper(interaction.channel)
        p1 = game.get_player(player.id, interaction)
        p2 = game.getPlayerObjectFromColor(color.value)
        await DiplomaticRelationsButtons.breakRelationsWith(game, p1, p2, interaction)

    @app_commands.command(name="break_minor_species")
    async def break_minor_species(self, interaction: discord.Interaction):
        player = interaction.user
        game = GamestateHelper(interaction.channel)
        p1 = game.get_player(player.id,interaction)
        game.breakMinorSpecies(p1)
        await interaction.response.send_message("Successfully broke relations with a minor species.")

    @app_commands.command(name="form_relations")
    @app_commands.choices(color=color_choices)
    async def form_relations(self, interaction: discord.Interaction, color: app_commands.Choice[str]):
        player = interaction.user
        await interaction.response.defer(thinking=False)
        game = GamestateHelper(interaction.channel)
        p1 = game.get_player(player.id,interaction)
        await DiplomaticRelationsButtons.acceptRelationsWith(game, p1, interaction, "dummy_" + color.value)

    @app_commands.command(name="show_player_area")
    async def show_player_area(self, interaction: discord.Interaction, player: Optional[discord.Member] = None):
        if player is None:
            player = interaction.user
        game = GamestateHelper(interaction.channel)
        p1 = game.get_player(player.id,interaction)
        drawing = DrawHelper(game.gamestate)
        image = drawing.player_area(p1)
        await interaction.response.defer(thinking=True)
        await interaction.followup.send(file=drawing.show_player_area(image))

    @app_commands.command(name="set_passed")
    async def set_passed(self, interaction: discord.Interaction, passed: bool,
                         permanent: Optional[bool] = None, player: Optional[discord.Member] = None):
        if player is None:
            player = interaction.user
        if permanent is None:
            permanent = passed
        game = GamestateHelper(interaction.channel)
        p1 = game.get_player(player.id,interaction)
        player_helper = PlayerHelper(game.get_player_from_color(p1["color"]), p1)
        player_helper.permanentlyPassTurn(permanent)
        player_helper.passTurn(passed)
        if passed:
            game.addToPassOrder(p1["player_name"])
        game.update_player(player_helper)
        await interaction.response.send_message(f"{player.mention} set passed status to {passed}.")

    @app_commands.command(name="set_traitor")
    async def set_traitor(self, interaction: discord.Interaction, traitor: bool,
                          player: Optional[discord.Member] = None):
        if player is None:
            player = interaction.user
        game = GamestateHelper(interaction.channel)
        p1 = game.get_player(player.id,interaction)
        player_helper = PlayerHelper(game.get_player_from_color(p1["color"]), p1)
        game.makeEveryoneNotTraitor()
        player_helper.setTraitor(traitor)
        game.update_player(player_helper)
        await interaction.response.send_message(f"{player.mention} set traitor status to {traitor}.")

    @app_commands.command(name="draw_reputation")
    async def draw_reputation(self, interaction: discord.Interaction, num_options: int):
        game = GamestateHelper(interaction.channel)
        player = game.get_player(interaction.user.id,interaction)
        player_helper = PlayerHelper(game.get_player_from_color(player["color"]), player)
        await interaction.response.defer(thinking=True, ephemeral=True)
        await ReputationButtons.resolveGainingReputation(game, num_options, interaction, player_helper, False)
        await interaction.channel.send(f"{interaction.user.name} drew {num_options} reputation tiles.")

    @app_commands.command(name="return_reputation")
    async def return_reputation(self, interaction: discord.Interaction, rep_value: int):
        game = GamestateHelper(interaction.channel)
        player = game.get_player(interaction.user.id,interaction)
        game.returnReputation(rep_value, player)
        message = f"{interaction.user.name} returned a reputation tile with value {rep_value}."
        await interaction.response.send_message(message, ephemeral=True)

    @app_commands.command(name="show_player_ships")
    async def show_player_ships(self, interaction: discord.Interaction, player: Optional[discord.Member] = None):
        if player is None:
            player = interaction.user
        game = GamestateHelper(interaction.channel)
        p1 = game.get_player(player.id,interaction)
        drawing = DrawHelper(game.gamestate)
        image = drawing.player_area(p1)
        await interaction.response.defer(thinking=True)
        await interaction.followup.send(file=drawing.show_player_ship_area(image))

    @app_commands.command(name="start_turn")
    async def start_turn(self, interaction: discord.Interaction, player: Optional[discord.Member] = None):
        if player is None:
            player = interaction.user
        # view = Turn(interaction, player.id)
        game = GamestateHelper(interaction.channel)
        p1 = game.get_player(player.id,interaction)
        TurnButtons.startNewTurn(p1, game)
        view = TurnButtons.getStartTurnButtons(game, p1, "dummy")
        game.updatePingTime()
        await interaction.response.send_message(f"## {game.getPlayerEmoji(p1)} started their turn.")
        await interaction.channel.send((f"{p1['player_name']} use these buttons to do your turn. "
                                        "The number of activations you have for each action"
                                        " is listed in brackets `()`" + game.displayPlayerStats(p1)), view=view)
