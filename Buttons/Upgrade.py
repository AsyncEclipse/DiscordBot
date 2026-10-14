import asyncio
import copy
import json
import discord
from helpers.EmojiHelper import Emoji
from helpers.GamestateHelper import GamestateHelper
from helpers.PlayerHelper import DISCOVERY_PART_IDS, PlayerHelper
from helpers.DrawHelper import DrawHelper
from discord.ui import View, Button
from helpers.ShipHelper import PlayerShip


class UpgradeButtons:
    @staticmethod
    async def startAncientInstinctUpgrade(game: GamestateHelper, player, interaction: discord.Interaction,
                                          tech: str):
        with open("data/parts.json", "r") as f:
            part_stats = json.load(f)
        player_helper = PlayerHelper(game.get_player_from_color(player["color"]), player)
        if (player["name"] != "Atlantians" or not player.get("ancientInstinctResearchAction")
                or player.get("ancientInstinctUsed")
                or tech not in player.get("ancientInstinctAvailableTechs", [])
                or tech not in player_helper.getTechs() or tech not in part_stats):
            await interaction.followup.send("That Ancient Instinct upgrade is not available.", ephemeral=True)
            return
        drawing = DrawHelper(game.gamestate)
        image = await asyncio.to_thread(drawing.player_area, player)
        view = View()
        for ship in game.getShipsWithParts(player):
            ship_emoji = Emoji.getEmojiByName(player['color'] + game.getShipShortName(ship))
            view.add_item(Button(label=ship.capitalize(), emoji=ship_emoji, style=discord.ButtonStyle.blurple,
                                 custom_id=f"FCID{player['color']}_upgradeShip_1_{ship}_free_ai_{tech}"))
        if not view.children:
            await interaction.followup.send("You have no ships available to upgrade.", ephemeral=True)
            return
        await interaction.followup.send(file=await asyncio.to_thread(drawing.show_player_ship_area, image),
                                        ephemeral=True)
        await interaction.channel.send(f"{interaction.user.mention}, choose a ship to upgrade with "
                                       f"{part_stats[tech]['name']}.", view=view)

    @staticmethod
    async def startUpgrade(game: GamestateHelper, player, interaction: discord.Interaction,
                           button: bool, discTileUpgrade: str, action:str):
        drawing = DrawHelper(game.gamestate)
        image = await asyncio.to_thread(drawing.player_area, player)
        view = View()
        actions = str(player['upgrade_apt'])
        if not button:
            actions = "1"
        if action != "dum":
            actions = action
        for ship in game.getShipsWithParts(player):
            shipEmoji = Emoji.getEmojiByName(player['color'] + game.getShipShortName(ship))
            view.add_item(Button(label=ship.capitalize(), emoji=shipEmoji, style=discord.ButtonStyle.blurple,
                                 custom_id=f"FCID{player['color']}_upgradeShip_{actions}_{ship}_{discTileUpgrade}"))
        await interaction.followup.send(file=await asyncio.to_thread(drawing.show_player_ship_area, image),
                                        ephemeral=True)
        if discTileUpgrade not in ("dummy", "free"):
            view.add_item(Button(label="Save For Future Upgrade Action", style=discord.ButtonStyle.red,
                                 custom_id=f"FCID{player['color']}_deleteMsg"))
        if button:
            await interaction.message.delete()
            if discTileUpgrade == "dummy":
                view.add_item(Button(label="Restart Turn", style=discord.ButtonStyle.gray,
                                     custom_id=f"FCID{player['color']}_restartTurn"))
                if actions == str(player['upgrade_apt']):
                    await interaction.channel.send(f"{player['player_name']} is using their turn to upgrade")

        await interaction.channel.send(
            f"{interaction.user.mention}, choose which ship you would like to upgrade.", view=view)

    @staticmethod
    async def upgradeShip(game: GamestateHelper, player, interaction: discord.Interaction,
                          customID: str, player_helper: PlayerHelper):
        view = View()
        actions = customID.split("_")[1]
        ship = customID.split("_")[2]
        discTileUpgrade = customID.split("_")[3]
        is_ancient_instinct = len(customID.split("_")) > 4 and customID.split("_")[4] == "ai"
        ancient_instinct_tech = customID.split("_")[5] if is_ancient_instinct else None
        custom_id_suffix = f"_ai_{ancient_instinct_tech}" if is_ancient_instinct else ""
        # set by the part menu's Undo, so the parts image is not sent twice
        partsShown = "_partsShown" if customID.endswith("_partsShown") else ""
        player_helper.renameOldExileParts(ship)
        player_helper.setOldShipParts(ship)
        game.update_player(player_helper)
        if discTileUpgrade == "mus":
            await UpgradeButtons.chooseUpgrade(game, player, interaction,
                                               f"chooseUpgrade_{actions}_{ship}_dummy_mus_5_mus", player_helper)
            return
        with open("data/parts.json", "r") as f:
            part_stats = json.load(f)
        for index,i in enumerate(player[f"{ship}_parts"]):
            if i == "mus":
                continue
            oldPart = player_helper.stats[f"old_{ship}_parts"][index]
            lab = part_stats[i]["name"]
            if oldPart != i:
                lab += " (Loc: "+str(index)+")"
            part_details = part_stats.get(i)
            partName = part_details["name"].lower().replace(" ", "_") if part_details else i
            view.add_item(Button(label=lab, style=discord.ButtonStyle.red,
                                 emoji=Emoji.getEmojiByName(partName),
                                 custom_id=(f"FCID{player['color']}_selectOldPart_"
                                            f"{actions}_{ship}_{i}_{discTileUpgrade}_{str(index)}"
                                            f"{custom_id_suffix}{partsShown}")))
        view.add_item(Button(label="Choose Different Ship", style=discord.ButtonStyle.gray,
                             custom_id=(f"FCID{player['color']}_chooseDifferentShip_"
                                        f"{actions}_{discTileUpgrade}{custom_id_suffix}")))
        if discTileUpgrade not in ("dummy", "free"):
            view.add_item(Button(label="Save For Future Upgrade Action", style=discord.ButtonStyle.red,
                                 custom_id=f"FCID{player['color']}_deleteMsg"))
        await UpgradeButtons.showMenu(interaction, f"{interaction.user.mention}, "
                                                   f"pick which part of your {ship} to replace or remove.", view)

    @staticmethod
    async def selectOldPart(game: GamestateHelper, player, interaction: discord.Interaction,
                            customID: str, player_helper: PlayerHelper):
        view = View()
        actions = customID.split("_")[1]
        ship = customID.split("_")[2]
        oldPart = customID.split("_")[3]
        discTileUpgrade = customID.split("_")[4]
        indexOfOldPart = customID.split("_")[5]
        is_ancient_instinct = len(customID.split("_")) > 6 and customID.split("_")[6] == "ai"
        ancient_instinct_tech = customID.split("_")[7] if is_ancient_instinct else None
        if discTileUpgrade not in ("dummy", "free"):
            await UpgradeButtons.chooseUpgrade(game, player, interaction,
                                               customID + "_" + discTileUpgrade, player_helper)
            return

        available_parts = player_helper.getAvailableShipParts()
        if is_ancient_instinct:
            available_parts = ({ancient_instinct_tech} if ancient_instinct_tech in available_parts
                               and ancient_instinct_tech != oldPart else set())
        drawing = DrawHelper(game.gamestate)
        with open("data/parts.json", "r") as f:
            part_stats = json.load(f)

        instinct_suffix = f"_ai_{ancient_instinct_tech}" if is_ancient_instinct else ""
        parts_shown_suffix = "_partsShown" if is_ancient_instinct else ""
        view.add_item(Button(label="Undo", style=discord.ButtonStyle.red,
                             custom_id=f"FCID{player['color']}_upgradeShip_{actions}_{ship}_"
                                       f"{discTileUpgrade}{instinct_suffix}{parts_shown_suffix}"))
        for i in available_parts:
            part_details = part_stats.get(i)
            partName = part_details["name"].lower().replace(" ", "_") if part_details else i
            if len(view.children) >= 25:
                break
            view.add_item(Button(label=part_stats[i]["name"], style=discord.ButtonStyle.blurple,
                                 custom_id=(f"FCID{player['color']}_chooseUpgrade_{actions}_{ship}_"
                                            f"{oldPart}_{i}_{indexOfOldPart}_{discTileUpgrade}{instinct_suffix}"),
                                 emoji=Emoji.getEmojiByName(partName)))
        prompt = (f"{interaction.user.mention}, replace {part_stats[oldPart]['name']} on your {ship} "
                  f"with {part_stats[ancient_instinct_tech]['name']}?" if is_ancient_instinct else
                  f"{interaction.user.mention}, replace {part_stats[oldPart]['name']} on your {ship} "
                  "with which part? Remove as a free action by selecting 'Empty'.")
        await UpgradeButtons.showMenu(interaction, prompt, view)
        if customID.endswith("_partsShown"):
            return
        await interaction.followup.send("Available parts",
                                        file=await asyncio.to_thread(drawing.availablePartsFile, available_parts),
                                        ephemeral=True)

    @staticmethod
    async def chooseUpgrade(game: GamestateHelper, player, interaction: discord.Interaction,
                            customID: str, player_helper: PlayerHelper):
        actions = int(customID.split("_")[1])
        ship = customID.split("_")[2]
        oldPart = customID.split("_")[3]
        newPart = customID.split("_")[4]
        discTileUpgrade = customID.split("_")[6]
        indexOfOldPart = customID.split("_")[5]
        is_ancient_instinct = len(customID.split("_")) > 7 and customID.split("_")[7] == "ai"
        ancient_instinct_tech = customID.split("_")[8] if is_ancient_instinct else None
        with open("data/parts.json", "r") as f:
            part_stats = json.load(f)
        if is_ancient_instinct and (player["name"] != "Atlantians" or discTileUpgrade != "free"
                                    or not player.get("ancientInstinctResearchAction")
                                    or player.get("ancientInstinctUsed")
                                    or ancient_instinct_tech not in player.get("ancientInstinctAvailableTechs", [])
                                    or newPart != ancient_instinct_tech
                                    or ancient_instinct_tech not in player_helper.getTechs()
                                    or ancient_instinct_tech not in part_stats or newPart == oldPart):
            await interaction.followup.send("That Ancient Instinct upgrade is not available.", ephemeral=True)
            return
        index = 0
        if newPart != "mus":
            index = player[f"{ship}_parts"].index(oldPart)
            index = int(indexOfOldPart)
        # in free mode "empty" really empties the slot instead of reverting it
        isFreeRemoval = newPart == "empty" and discTileUpgrade != "free"
        if isFreeRemoval:
            newPart = player[f"old_{ship}_parts"][index]
        newParts = list(player[f"{ship}_parts"])
        if newPart == "mus":
            newParts.append("mus")
        else:
            newParts[index] = newPart
        # an illegal build must not cost the player a disc
        candidate = dict(player_helper.stats)
        candidate[f"{ship}_parts"] = newParts
        if not PlayerShip(candidate, ship).check_valid_ship():
            await interaction.followup.send("Your ship is not valid! Please try a different part", ephemeral=True)
            return
        undo = copy.deepcopy({k: v for k, v in player_helper.stats.items() if k != "upgradeUndo"})
        if is_ancient_instinct:
            player_helper.stats["ancientInstinctUsed"] = True
            player_helper.stats["upgradeUndoAncientInstinctTech"] = ancient_instinct_tech
        else:
            player_helper.stats["upgradeUndoAncientInstinctTech"] = None
        if not isFreeRemoval and newPart != oldPart and discTileUpgrade != "free":
            actions -= 1
            if actions == player['upgrade_apt'] - 1 and discTileUpgrade == "dummy":
                player_helper.spend_influence_on_action("upgrade")
        if newPart in DISCOVERY_PART_IDS and newPart in player_helper.stats["ancient_parts"]:
            player_helper.stats["ancient_parts"].remove(newPart)
        oldName = "Nothing" if newPart == "mus" else part_stats[oldPart]['name']
        player_helper.stats[f"{ship}_parts"] = newParts
        player_helper.stats["upgradeUndo"] = undo
        player_helper.specifyDetailsOfAction(f"Replaced {oldName} with {part_stats[newPart]['name']}"
                                             f" on their {ship.capitalize()}.")
        game.update_player(player_helper)
        drawing = DrawHelper(game.gamestate)
        image = await asyncio.to_thread(drawing.player_area, player_helper.stats)
        view = View()
        if not is_ancient_instinct and actions > 0 and not player.get("passed"):
            for ship2 in game.getShipsWithParts(player):
                shipEmoji = Emoji.getEmojiByName(player['color'] + game.getShipShortName(ship2))
                view.add_item(Button(label=ship2.capitalize(), emoji=shipEmoji, style=discord.ButtonStyle.blurple,
                                     custom_id=f"FCID{player['color']}_upgradeShip_{str(actions)}_{ship2}_dummy"))
        view.add_item(Button(label="Finish Action", style=discord.ButtonStyle.red,
                             custom_id=f"FCID{player['color']}_finishAction"))
        view.add_item(Button(label="Undo", style=discord.ButtonStyle.gray,
                             custom_id=(f"FCID{player['color']}_undoUpgrade_{customID.split('_')[1]}_ai_"
                                        f"{ancient_instinct_tech}"
                                        if is_ancient_instinct else
                                        f"FCID{player['color']}_undoUpgrade_{customID.split('_')[1]}")))
        if interaction.message is not None:
            await interaction.message.delete()
        await interaction.channel.send(f"{player['player_name']} replaced {oldName} with {part_stats[newPart]['name']}"
                                       f" on their {ship.capitalize()} which now looks like this:",
                                       file=await asyncio.to_thread(drawing.show_player_ship,
                                                                    image, ship, player_helper.stats["name"]))
        if discTileUpgrade == "dummy" or is_ancient_instinct:
            prompt = (f"{player['player_name']}, finish this action or undo your Ancient Instinct upgrade."
                      if is_ancient_instinct else
                      f"{player['player_name']}, choose which ship you would like to upgrade or finish your action.")
            await interaction.channel.send(prompt, view=view)

    @staticmethod
    async def undoUpgrade(game: GamestateHelper, player, interaction: discord.Interaction,
                          customID: str, player_helper: PlayerHelper):
        undo = player.get("upgradeUndo")
        if undo is None:
            await interaction.followup.send("There is no upgrade to undo.", ephemeral=True)
            return
        custom_parts = customID.split("_")
        ancient_instinct_tech = player.get("upgradeUndoAncientInstinctTech")
        if ancient_instinct_tech:
            if (len(custom_parts) < 4 or custom_parts[2] != "ai" or custom_parts[3] != ancient_instinct_tech
                    or not player.get("ancientInstinctResearchAction") or player.get("ancientInstinctUsed") is not True
                    or ancient_instinct_tech not in player.get("ancientInstinctAvailableTechs", [])):
                await interaction.followup.send("That upgrade can no longer be undone.", ephemeral=True)
                return
        elif len(custom_parts) > 2 and custom_parts[2] == "ai":
            await interaction.followup.send("That Ancient Instinct upgrade is not available.", ephemeral=True)
            return
        player_helper.stats.clear()
        player_helper.stats.update(undo)
        player_helper.stats["upgradeUndoAncientInstinctTech"] = None
        game.update_player(player_helper)
        await interaction.message.delete()
        await interaction.channel.send(f"{player['player_name']} undid their last part swap.")
        if ancient_instinct_tech:
            await UpgradeButtons.startAncientInstinctUpgrade(game, player, interaction, ancient_instinct_tech)
            return
        await UpgradeButtons.startUpgrade(game, player, interaction, False, "dummy", customID.split("_")[1])

    @staticmethod
    async def showMenu(interaction: discord.Interaction, content: str, view: View):
        # slash commands have no message to edit
        if interaction.message is None:
            await interaction.channel.send(content, view=view)
        else:
            await interaction.message.edit(content=content, view=view)
