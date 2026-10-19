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
    def getTechnoMagicView(game: GamestateHelper, player, pos: str):
        tile = game.gamestate["board"][pos]
        installed = tile.get("tmParts", {}).get(player["color"], {})
        view = View()
        for ship in game.getShipsWithParts(player):
            if (f"{player['color']}-{game.getShipShortName(ship)}" in tile.get("player_ships", [])
                    and not installed.get(ship, {}).get("install")):
                view.add_item(Button(label=ship.capitalize(), style=discord.ButtonStyle.blurple,
                                     custom_id=f"FCID{player['color']}_technoMagic_{pos}_{ship}"))
        for ship, record in installed.items():
            if record.get("install"):
                view.add_item(Button(label=f"Undo {ship.capitalize()}", style=discord.ButtonStyle.gray,
                                     custom_id=f"FCID{player['color']}_undoUpgrade_1_tm{pos}_{ship}"))
        view.add_item(Button(label="Restart Techno-Magic", style=discord.ButtonStyle.red,
                             custom_id=f"FCID{player['color']}_restartTechnoMagic_{pos}"))
        return view

    @staticmethod
    def resetTechnoMagic(game: GamestateHelper, player, pos: str, ship=None):
        records = game.gamestate["board"][pos].get("tmParts", {}).get(player["color"], {})
        for blueprint, record in records.items():
            if ship is not None and blueprint != ship:
                continue
            if not record.pop("install", None):
                continue
            parts = list(record["base"])
            for tile in game.gamestate["board"].values():
                install = tile.get("tmParts", {}).get(player["color"], {}).get(blueprint, {}).get("install")
                if install:
                    parts[install[0]] = install[2]
            player[f"{blueprint}_parts"] = parts
        game.update_player(PlayerHelper(game.get_player_from_color(player["color"]), player))

    @staticmethod
    async def restartTechnoMagic(game: GamestateHelper, player, interaction: discord.Interaction, pos: str):
        UpgradeButtons.resetTechnoMagic(game, player, pos)
        await interaction.message.edit(content=f"{player['player_name']}, choose your Techno-Magic upgrades again.",
                                       view=UpgradeButtons.getTechnoMagicView(game, player, pos))

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
        # only a discovery tile part can be saved for a later Upgrade action
        if discTileUpgrade in DISCOVERY_PART_IDS:
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
                                            f"{actions}_{ship}_{i}_{discTileUpgrade}_{str(index)}{partsShown}")))
        if discTileUpgrade.startswith("tm"):
            view.add_item(Button(label="Restart Techno-Magic", style=discord.ButtonStyle.red,
                                 custom_id=f"FCID{player['color']}_restartTechnoMagic_{discTileUpgrade[2:]}"))
        else:
            view.add_item(Button(label="Choose Different Ship", style=discord.ButtonStyle.gray,
                                 custom_id=(f"FCID{player['color']}_chooseDifferentShip_"
                                            f"{actions}_{discTileUpgrade}")))
        if discTileUpgrade in DISCOVERY_PART_IDS:
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
        if discTileUpgrade not in ("dummy", "free") and not discTileUpgrade.startswith("tm"):
            await UpgradeButtons.chooseUpgrade(game, player, interaction,
                                               customID + "_" + discTileUpgrade, player_helper)
            return

        available_parts = player_helper.getAvailableShipParts()
        if discTileUpgrade.startswith("tm"):
            # Techno-Magic: no removing ship parts, and no Ancient ship parts
            available_parts = {part for part in available_parts
                               if part != "empty" and part not in DISCOVERY_PART_IDS}
        drawing = DrawHelper(game.gamestate)
        with open("data/parts.json", "r") as f:
            part_stats = json.load(f)

        view.add_item(Button(label="Undo", style=discord.ButtonStyle.red,
                             custom_id=f"FCID{player['color']}_upgradeShip_{actions}_{ship}_{discTileUpgrade}_partsShown"))
        for i in available_parts:
            part_details = part_stats.get(i)
            partName = part_details["name"].lower().replace(" ", "_") if part_details else i
            if len(view.children) >= 25:
                break
            view.add_item(Button(label=part_stats[i]["name"], style=discord.ButtonStyle.blurple,
                                 custom_id=(f"FCID{player['color']}_chooseUpgrade_{actions}_{ship}_"
                                            f"{oldPart}_{i}_{indexOfOldPart}_{discTileUpgrade}"),
                                 emoji=Emoji.getEmojiByName(partName)))
        if discTileUpgrade.startswith("tm"):
            view.add_item(Button(label="Restart Techno-Magic", style=discord.ButtonStyle.red,
                                 custom_id=f"FCID{player['color']}_restartTechnoMagic_{discTileUpgrade[2:]}"))
        removal_note = "" if discTileUpgrade.startswith("tm") else " Remove as a free action by selecting 'Empty'."
        await UpgradeButtons.showMenu(interaction, f"{interaction.user.mention}, replace "
                                      f"{part_stats[oldPart]['name']} on your {ship} with which part?"
                                      f"{removal_note}", view)
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
        with open("data/parts.json", "r") as f:
            part_stats = json.load(f)
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
        if not isFreeRemoval and newPart != oldPart and discTileUpgrade != "free":
            actions -= 1
            if actions == player['upgrade_apt'] - 1 and discTileUpgrade == "dummy":
                player_helper.spend_influence_on_action("upgrade")
        if newPart in DISCOVERY_PART_IDS and newPart in player_helper.stats["ancient_parts"]:
            player_helper.stats["ancient_parts"].remove(newPart)
        oldName = "Nothing" if newPart == "mus" else part_stats[oldPart]['name']
        player_helper.stats[f"{ship}_parts"] = newParts
        if discTileUpgrade.startswith("tm"):
            pos = discTileUpgrade[2:]
            game.gamestate["board"][pos]["tmParts"][player["color"]][ship]["install"] = (index, oldPart, newPart)
        if not discTileUpgrade.startswith("tm"):
            player_helper.stats["upgradeUndo"] = undo
        player_helper.specifyDetailsOfAction(f"Replaced {oldName} with {part_stats[newPart]['name']}"
                                             f" on their {ship.capitalize()}.")
        game.update_player(player_helper)
        drawing = DrawHelper(game.gamestate)
        image = await asyncio.to_thread(drawing.player_area, player_helper.stats)
        view = View()
        if actions > 0 and (discTileUpgrade == "free" or not player.get("passed")):
            for ship2 in game.getShipsWithParts(player):
                shipEmoji = Emoji.getEmojiByName(player['color'] + game.getShipShortName(ship2))
                view.add_item(Button(label=ship2.capitalize(), emoji=shipEmoji, style=discord.ButtonStyle.blurple,
                                     custom_id=f"FCID{player['color']}_upgradeShip_{str(actions)}_{ship2}_{discTileUpgrade}"))
        if discTileUpgrade == "free":
            view.add_item(Button(label="Done", style=discord.ButtonStyle.red,
                                 custom_id=f"FCID{player['color']}_deleteMsg"))
        else:
            view.add_item(Button(label="Finish Action", style=discord.ButtonStyle.red,
                                 custom_id=f"FCID{player['color']}_finishAction"))
        view.add_item(Button(label="Undo", style=discord.ButtonStyle.gray,
                             custom_id=f"FCID{player['color']}_undoUpgrade_{customID.split('_')[1]}_{discTileUpgrade}"))
        if interaction.message is not None:
            await interaction.message.delete()
        await interaction.channel.send(f"{player['player_name']} replaced {oldName} with {part_stats[newPart]['name']}"
                                       f" on their {ship.capitalize()} which now looks like this:",
                                       file=await asyncio.to_thread(drawing.show_player_ship,
                                                                    image, ship, player_helper.stats["name"]))
        if discTileUpgrade in ("dummy", "free"):
            await interaction.channel.send(f"{player['player_name']}, choose which ship you would like to upgrade "
                                           "or finish.", view=view)
        elif discTileUpgrade.startswith("tm"):
            view = UpgradeButtons.getTechnoMagicView(game, player, discTileUpgrade[2:])
            await interaction.channel.send(f"{player['player_name']}, choose another combat blueprint to upgrade"
                                           " or undo this Techno-Magic part.", view=view)

    @staticmethod
    async def undoUpgrade(game: GamestateHelper, player, interaction: discord.Interaction,
                          customID: str, player_helper: PlayerHelper):
        parts = customID.split("_")
        # Undo buttons posted before the upgrade mode joined the id carry only the action count
        mode = parts[2] if len(parts) > 2 else "dummy"
        if mode.startswith("tm"):
            UpgradeButtons.resetTechnoMagic(game, player, mode[2:], parts[3])
            view = UpgradeButtons.getTechnoMagicView(game, player, mode[2:])
            await interaction.message.edit(content=f"{player['player_name']}, undid the Techno-Magic part."
                                           " Choose a combat blueprint to upgrade.", view=view)
            return
        undo = player.get("upgradeUndo")
        if undo is None:
            await interaction.followup.send("There is no upgrade to undo.", ephemeral=True)
            return
        player_helper.stats.clear()
        player_helper.stats.update(undo)
        game.update_player(player_helper)
        await interaction.message.delete()
        await interaction.channel.send(f"{player['player_name']} undid their last part swap.")
        await UpgradeButtons.startUpgrade(game, player, interaction, False, mode, parts[1])

    @staticmethod
    async def showMenu(interaction: discord.Interaction, content: str, view: View):
        # slash commands have no message to edit
        if interaction.message is None:
            await interaction.channel.send(content, view=view)
        else:
            await interaction.message.edit(content=content, view=view)
