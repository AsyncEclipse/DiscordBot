import asyncio
import discord
from helpers import FactionData
from helpers.DrawHelper import DrawHelper
from helpers.EmojiHelper import Emoji
from helpers.GamestateHelper import GamestateHelper
from helpers.PlayerHelper import PlayerHelper
from discord.ui import View, Button


class BuildButtons:

    @staticmethod
    def raidSuffix(buttonID: str):
        """The trailing marker that keeps a nested Raid build inside its Move action."""
        if "herRaid_" not in buttonID:
            return ""
        return "_herRaid_" + buttonID.rsplit("_", 1)[1]

    @staticmethod
    def buildsLeft(player, build_apt):
        """Build units a Build action may still place, across every system it visits."""
        return max(0, build_apt - player.get("buildsThisAction", 0))

    @staticmethod
    async def startBuild(game: GamestateHelper, player, interaction: discord.Interaction,
                         buttonID: str, player_helper: PlayerHelper):
        tiles = game.get_owned_tiles(player)
        tiles.sort()
        view = View()
        nested_raid = "herRaidBuild" in buttonID
        resume_build = "herRegroupResume" in buttonID
        resume_after_move = "herRegroupResumeAfter" in buttonID
        if not nested_raid and not resume_build:
            await interaction.channel.send(f"{player['player_name']} is using their turn to build")
        if "2" not in buttonID:
            player_helper.spend_influence_on_action("build")
            player_helper.stats["buildsThisAction"] = 0
            if FactionData.has(player, "phase_technology"):
                player_helper.stats["phaseBuildsThisAction"] = 0
                player_helper.stats["phaseSwappedThisAction"] = False
            game.update_player(player_helper)
            await interaction.message.delete()
        if buttonID == "startBuild" and (FactionData.has(player, "raid")
                                         or FactionData.has(player, "regroup")):
            player_helper.stats["herCrossUsed"] = False
            player_helper.stats["herRaidCharged"] = False
            game.update_player(player_helper)
        if nested_raid:
            await interaction.message.delete()
            moveCount = buttonID.rsplit("_", 1)[1]
            suffix = f"_herRaid_{moveCount}"
        else:
            suffix = ""
        for tile in tiles:
            view.add_item(Button(label=tile, style=discord.ButtonStyle.blurple,
                                 custom_id=f"FCID{player['color']}_buildIn_{tile}{suffix}"))
        if nested_raid:
            view.add_item(Button(label="Back to Move", style=discord.ButtonStyle.gray,
                                 custom_id=f"FCID{player['color']}_herBackToMove_{moveCount}"))
        elif (not player.get("passed") and FactionData.has(player, "regroup")
              and not player.get("herCrossUsed")
              and (buttonID == "startBuild" or resume_build)):
            view.add_item(Button(label="Move Activation (1)", style=discord.ButtonStyle.green,
                                 custom_id=f"FCID{player['color']}_herRegroupMove_before"))
        if resume_after_move:
            view.add_item(Button(label="Finish Action", style=discord.ButtonStyle.red,
                                 custom_id=f"FCID{player['color']}_finishAction"))
        view.add_item(Button(label="Restart Turn", style=discord.ButtonStyle.gray,
                             custom_id=f"FCID{player['color']}_restartTurn"))
        message = f"{player['player_name']}, choose which tile you would like to build in."
        if (not player.get("passed") and FactionData.has(player, "regroup")
                and not player.get("herCrossUsed")
                and (buttonID == "startBuild" or resume_build)):
            message += " Regroup: this Build action also includes one Move activation."
        await interaction.channel.send(message, view=view)
        drawing = DrawHelper(game.gamestate)
        if len(tiles) > 0:
            asyncio.create_task(interaction.followup.send(file=await asyncio.to_thread(drawing.mergeLocationsFile,
                                                                                       tiles), ephemeral=True))

    @staticmethod
    async def buildIn(game: GamestateHelper, player, interaction: discord.Interaction, buttonID: str):
        loc = buttonID.split("_")[1]
        suffix = BuildButtons.raidSuffix(buttonID)
        view = View()
        view = BuildButtons.buildBuildButtonsView(interaction, "", 0, loc, view, player, game, suffix)
        await interaction.message.delete()
        buildApt = player["build_apt"]
        if suffix or player.get("passed") or player.get("pulsarBuild"):
            buildApt = 1
        else:
            buildApt = BuildButtons.buildsLeft(player, buildApt)
        await interaction.channel.send(f"{player['player_name']}, you have {player['materials']} materials to "
                                       f"spend on up to {str(buildApt)} units in this system.", view=view)

    @staticmethod
    async def buildShip(game: GamestateHelper, player, interaction: discord.Interaction, buttonID: str):
        build = buttonID.split("_")[1].replace("none", "").split(";")
        if "" in build:
            build.remove("")
        cost = int(buttonID.split("_")[2])
        loc = buttonID.split("_")[3]
        ship = str(buttonID.split("_")[4])
        suffix = BuildButtons.raidSuffix(buttonID)
        buildApt = player["build_apt"]
        if suffix or player.get("passed") or player.get("pulsarBuild"):
            buildApt = 1
        else:
            buildApt = BuildButtons.buildsLeft(player, buildApt)
        if len(build) >= buildApt:
            await interaction.message.edit(content=(f"You cannot build any more units. Current build is:\n"
                                                    f"{build} for {cost} materials."))
            return
        build.append(f"{player['color']}-{GamestateHelper.getShipShortName(ship)}")
        cost += PlayerHelper.get_ship_cost(player, game.getShipShortName(ship))
        view = View()
        view = BuildButtons.buildBuildButtonsView(interaction, ";".join(build), cost, loc, view, player, game, suffix)
        await interaction.message.edit(content=f"Total cost so far of {cost}", view=view)

    @staticmethod
    def buildBuildButtonsView(interaction: discord.Interaction, build: str, cost, build_loc, view: View, player,
                              game: GamestateHelper, suffix: str = ""):
        ships = ["Interceptor", "Cruiser", "Dreadnought", "Starbase", "Orbital", "Monolith"]
        if build == "":
            build = "none"
        shipsShort = ["int", "cru", "drd", "sb"]

        if "stb" not in player["military_tech"] or not player.get("starbase_parts"):
            ships.remove("Starbase")
        if "orb" not in player["nano_tech"] or "orb" in build:
            ships.remove("Orbital")
        if "mon" not in player["nano_tech"] or "mon" in build:
            ships.remove("Monolith")
        player_ships = game.gamestate["board"][build_loc]["player_ships"]
        for shipInTile in player_ships:
            if "orb" in shipInTile and "Orbital" in ships:
                ships.remove("Orbital")
            if "mon" in shipInTile and "Monolith" in ships:
                ships.remove("Monolith")
        for counter, ship in enumerate(ships):
            ship_short = game.getShipShortName(ship)
            remaining = 10
            if counter < len(player["ship_stock"]) and "Orb" not in ship and "Mon" not in ship:
                remaining = player["ship_stock"][counter]
                if shipsShort[counter] in build:
                    remaining -= build.count(shipsShort[counter])
            ship_cost = PlayerHelper.get_ship_cost(player, ship_short)
            buttonElements = [f"FCID{player['color']}", "buildShip", build, str(cost), build_loc, ship]
            if remaining > 0:
                if ship != "Monolith":
                    shipEmoji = Emoji.getEmojiByName(player['color'] + game.getShipShortName(ship))
                    if ship == "Orbital":
                        shipEmoji = Emoji.getEmojiByName("orb")
                    view.add_item(Button(label=f"{ship} ({ship_cost})", emoji=shipEmoji,
                                         style=discord.ButtonStyle.blurple,
                                         custom_id="_".join(buttonElements) + suffix))
                else:
                    view.add_item(Button(label=f"{ship} ({ship_cost})",
                                         style=discord.ButtonStyle.blurple,
                                         custom_id="_".join(buttonElements) + suffix))
        buttonElements = [f"FCID{player['color']}", "finishBuild", build, str(cost), build_loc]
        if build != "none":
            view.add_item(Button(label="Finished In This System", style=discord.ButtonStyle.red,
                                 custom_id="_".join(buttonElements) + suffix))
        else:
            view.add_item(Button(label="Finish Action", style=discord.ButtonStyle.red,
                                 custom_id=f"FCID{player['color']}_finishAction"))
        view.add_item(Button(label="Reset Build", style=discord.ButtonStyle.gray,
                             custom_id=f"FCID{player['color']}_buildIn_{build_loc}" + suffix))
        if suffix:
            view.add_item(Button(label="Back to Move", style=discord.ButtonStyle.gray,
                                 custom_id=f"FCID{player['color']}_herBackToMove_{suffix.rsplit('_', 1)[1]}"))
        view.add_item(Button(label="Restart Turn", style=discord.ButtonStyle.gray,
                             custom_id=f"FCID{player['color']}_restartTurn"))
        return view

    @staticmethod
    async def finishBuild(game: GamestateHelper, player, interaction: discord.Interaction, buttonID: str):
        build = buttonID.split("_")[1].replace("none", "").split(";")
        cost = buttonID.split("_")[2]
        loc = buttonID.split("_")[3]
        suffix = BuildButtons.raidSuffix(buttonID)
        view = View()
        view = BuildButtons.buildBuildSpendButtonsView(game, interaction, player, ";".join(build),
                                                       cost, loc, view, str(player['materials']),
                                                       str(player['science']), str(player['money']), "0", suffix)
        await interaction.message.delete()
        await interaction.channel.send(f"Total cost: {cost}\n"
                                       f"Available resources: Materials-{player['materials']}"
                                       f" Science-{player['science']} Money-{player['money']}", view=view)

    @staticmethod
    async def spendMaterial(game: GamestateHelper, player, interaction: discord.Interaction, buttonID: str):
        build = buttonID.split("_")[1]
        cost = buttonID.split("_")[2]
        loc = buttonID.split("_")[3]
        material = int(buttonID.split("_")[4])
        science = buttonID.split("_")[5]
        money = buttonID.split("_")[6]
        spent = int(buttonID.split("_")[7])
        matSpent = int(buttonID.split("_")[8])
        suffix = BuildButtons.raidSuffix(buttonID)
        material -= matSpent
        spent += matSpent
        material = str(material)
        spent = str(spent)
        view = View()
        view = BuildButtons.buildBuildSpendButtonsView(game, interaction, player, build, cost,
                                                       loc, view, material, science, money, spent, suffix)
        await interaction.message.edit(content=f"Total cost: {cost}"
                                       f"\nAvailable resources: Materials-{material} Science-{science} Money-{money}"
                                       f"\nResources spent: {spent}", view=view)

    async def convertResource(game: GamestateHelper, player, interaction: discord.Interaction, buttonID: str):
        build = buttonID.split("_")[1]
        cost = buttonID.split("_")[2]
        loc = buttonID.split("_")[3]
        material = buttonID.split("_")[4]
        science = int(buttonID.split("_")[5])
        money = int(buttonID.split("_")[6])
        spent = int(buttonID.split("_")[7])
        resource = buttonID.split("_")[8]
        suffix = BuildButtons.raidSuffix(buttonID)
        ratio = FactionData.of(player).get("money_trade_ratio", 1) if resource == "Money" else 1
        spent += ratio
        if resource == "Science":
            science -= player["trade_value"]
        else:
            money -= player["trade_value"]
        # the 3:2 trade buys two materials, so an odd cost leaves one of them with the player
        if spent > int(cost):
            material = str(int(material) + spent - int(cost))
            spent = int(cost)
        science = str(science)
        money = str(money)
        spent = str(spent)
        view = View()
        view = BuildButtons.buildBuildSpendButtonsView(game, interaction, player, build, cost,
                                                       loc, view, material, science, money, spent, suffix)
        await interaction.message.edit(content=f"Total cost: {cost}"
                                       f"\nAvailable resources: Materials-{material} Science-{science} Money-{money}"
                                       f"\nResources spent: {spent}", view=view)

    @staticmethod
    def buildBuildSpendButtonsView(game: GamestateHelper, interaction: discord.Interaction, player,
                                   build: str, cost: str, build_loc: str, view: View,
                                   material: str, science: str, money: str, spent: str, suffix: str = ""):
        num = min(int(cost), int(material))
        buttonElements = [f"FCID{player['color']}", "spendMaterial", build, str(cost),
                          build_loc, material, science, money, spent, str(num)]
        if num > 0 and int(spent) < int(cost):
            view.add_item(Button(label=f"Materials ({str(num)})", style=discord.ButtonStyle.blurple,
                                 custom_id="_".join(buttonElements) + suffix))

        elements = ["Science", "Money"]
        tradeVal = player['trade_value']
        for resource in elements:
            buttonElements = [f"FCID{player['color']}", "convertResource", build, str(cost),
                              build_loc, material, science, money, spent, resource]
            if resource == "Science":
                if int(science) >= tradeVal and int(spent) < int(cost):
                    view.add_item(Button(label=f"{resource} ({str(tradeVal)}:1)", style=discord.ButtonStyle.gray,
                                         custom_id="_".join(buttonElements) + suffix))
            if resource == "Money":
                if int(money) >= tradeVal and int(spent) < int(cost):
                    ratio = FactionData.of(player).get("money_trade_ratio", 1)
                    view.add_item(Button(label=f"{resource} ({str(tradeVal)}:{ratio})", style=discord.ButtonStyle.gray,
                                         custom_id="_".join(buttonElements) + suffix))

        buttonElements = [f"FCID{player['color']}", "finishSpendForBuild", build, build_loc, material, science, money]
        if int(spent) >= int(cost):
            view.add_item(Button(label="Finish Build In This System", style=discord.ButtonStyle.red,
                                 custom_id="_".join(buttonElements) + suffix))
        if suffix:
            view.add_item(Button(label="Back to Move", style=discord.ButtonStyle.gray,
                                 custom_id=f"FCID{player['color']}_herBackToMove_{suffix.rsplit('_', 1)[1]}"))
        view.add_item(Button(label="Restart Turn", style=discord.ButtonStyle.gray,
                             custom_id=f"FCID{player['color']}_restartTurn"))
        return view

    @staticmethod
    async def finishSpendForBuild(game: GamestateHelper, player, interaction: discord.Interaction,
                                  buttonID: str, player_helper: PlayerHelper):
        build = buttonID.split("_")[1].replace("none", "").split(";")
        loc = buttonID.split("_")[2]
        material = int(buttonID.split("_")[3])
        science = int(buttonID.split("_")[4])
        money = int(buttonID.split("_")[5])
        suffix = BuildButtons.raidSuffix(buttonID)
        moveCount = int(suffix.rsplit("_", 1)[1]) if suffix else 0
        game.add_units(build, loc)
        game.fixshipsOrder(loc)
        summary = ""
        textSum = ""
        for ship in build:

            shortName = ship.split("-")[1]
            if shortName != "mon" and shortName != "orb":
                shipEmoji = Emoji.getEmojiByName(player['color'] + shortName)
                textSum += shipEmoji + " "
            summary += " " + game.getShipFullName(shortName)
            textSum += game.getShipFullName(shortName).capitalize() + "\n"
        if suffix and moveCount == 1 and not player.get("herRaidCharged"):
            # Raid's build before the first move spends the Move action's disc now;
            # moveTo then skips it so the action still uses exactly one disc.
            player_helper.spend_influence_on_action("move")
            player_helper.stats["herRaidCharged"] = True
        player_helper.specifyDetailsOfAction("Built " + summary + " in " + loc + ".")
        player_helper.stats["science"] = science
        player_helper.stats["materials"] = material
        player_helper.stats["money"] = money
        if suffix:
            player_helper.stats["herCrossUsed"] = True
        player_helper.stats["buildsThisAction"] = player_helper.stats.get("buildsThisAction", 0) + len(build)
        game.update_player(player_helper)
        drawing = DrawHelper(game.gamestate)
        await interaction.channel.send("This is what the tile looks like after the build. They built the following:\n"
                                       + textSum,
                                       file=await asyncio.to_thread(drawing.board_tile_image_file, loc))
        if suffix:
            if moveCount <= player["move_apt"]:
                await interaction.message.delete()
                from Buttons.Move import MoveButtons
                await MoveButtons.startMove(game, player, interaction,
                                            f"startMove_{moveCount}_herRaidResume", False)
            else:
                from Buttons.Turn import TurnButtons
                await TurnButtons.finishAction(player, game, interaction, player_helper)
            return
        buildApt = player["build_apt"]
        pulsar_build = player.get("pulsarBuild")
        if player.get("passed") or pulsar_build:
            buildApt = 1
            if pulsar_build:
                player_helper.stats["pulsarBuild"] = False
                game.update_player(player_helper)
        view2 = View()
        if not player.get("passed") and not pulsar_build \
                and BuildButtons.buildsLeft(player_helper.stats, buildApt) > 0:
            view2.add_item(Button(label="Build Somewhere Else", style=discord.ButtonStyle.red,
                                  custom_id="startBuild2_deleteMsg"))
        if (FactionData.has(player, "regroup") and not player.get("passed")
                and not pulsar_build and not player.get("herCrossUsed")):
            view2.add_item(Button(label="Move Activation (1)", style=discord.ButtonStyle.green,
                                  custom_id=f"FCID{player['color']}_herRegroupMove_after"))
        if FactionData.has(player, "phase_technology"):
            player_helper.stats["phaseBuildsThisAction"] = (
                player_helper.stats.get("phaseBuildsThisAction", 0) + len(build))
            game.update_player(player_helper)
            if (not player_helper.stats.get("phaseSwappedThisAction", False)
                    and player_helper.stats["phaseBuildsThisAction"] < buildApt):
                view2.add_item(Button(label="Swap for Upgrade", style=discord.ButtonStyle.green,
                                      custom_id=f"FCID{player['color']}_phaseTechUpgrade"))
        view2.add_item(Button(label="Finish Action", style=discord.ButtonStyle.red,
                              custom_id=f"FCID{player['color']}_finishAction"))
        await interaction.channel.send(f"{player['player_name']} use buttons to finish the action or"
                                       " potentially build somewhere else.", view=view2)
        await interaction.message.delete()

    @staticmethod
    async def phaseTechUpgrade(game: GamestateHelper, player, interaction: discord.Interaction,
                               buttonID: str, player_helper: PlayerHelper):
        """Phase Technology: spend the remaining Build activation as an Upgrade 1 activation."""
        from Buttons.Upgrade import UpgradeButtons
        buildApt = player["build_apt"]
        if player.get("passed") or player.get("pulsarBuild"):
            buildApt = 1
        if not FactionData.has(player, "phase_technology"):
            await interaction.followup.send("Your faction cannot swap a Build activation for an Upgrade.",
                                            ephemeral=True)
            return
        if player_helper.stats.get("phaseSwappedThisAction", False):
            await interaction.followup.send("You already swapped a Build activation this action.", ephemeral=True)
            return
        if player_helper.stats.get("phaseBuildsThisAction", 0) < 1:
            await interaction.followup.send("Phase Technology swaps a later Build activation, not the first.",
                                            ephemeral=True)
            return
        if player_helper.stats.get("phaseBuildsThisAction", 0) >= buildApt:
            await interaction.followup.send("This action has no Build activation left to swap.", ephemeral=True)
            return
        player_helper.stats["phaseSwappedThisAction"] = True
        player_helper.stats["phaseBuildsThisAction"] += 1
        game.update_player(player_helper)
        await UpgradeButtons.startUpgrade(game, player, interaction, True, "phase", "1")
