import asyncio
import copy
import json
import logging
import discord
from helpers import FactionData
from helpers.EmojiHelper import Emoji
from helpers.GamestateHelper import GamestateHelper
from helpers.PlayerHelper import DISCOVERY_PART_IDS, PlayerHelper
from helpers.DrawHelper import DrawHelper
from discord.ui import View, Button
from helpers.ShipHelper import PlayerShip


# (source, target) -> (ships spent, ships gained, materials gained)
ADAPTIVE_SWAPS = {
    ("int", "cru"): (2, 1, 1),
    ("cru", "drd"): (2, 1, 2),
    ("cru", "int"): (1, 2, -1),
    ("drd", "cru"): (1, 2, -2),
}
STOCK_INDEX = {"int": 0, "cru": 1, "drd": 2}


class UpgradeButtons:
    @staticmethod
    def addInfinitePossibilitiesButton(view: View, game: GamestateHelper, player, return_to: str):
        """Children of Cog: one free Upgrade activation accompanying a Build/Move action."""
        if (FactionData.has(player, "infinite_possibilities")
                and not player.get("infinitePossibilitiesUsed") and not player.get("passed")
                and game.getShipsWithParts(player)):
            view.add_item(Button(label="Infinite Possibilities: Upgrade", style=discord.ButtonStyle.green,
                                 custom_id=f"FCID{player['color']}_infiniteUpgrade_{return_to}"))

    @staticmethod
    def is_drive(part):
        with open("data/parts.json", "r") as f:
            return json.load(f).get(part, {}).get("range", 0) > 0

    @staticmethod
    def must_keep_drive(player, ship, part):
        """A Harvester may replace its Drive, but may not leave the slot without one."""
        return ship == "starbase" and FactionData.has(player, "harvester") and UpgradeButtons.is_drive(part)

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
        view.add_item(Button(label="Finish Techno-Magic", style=discord.ButtonStyle.green,
                             custom_id=f"FCID{player['color']}_finishTechnoMagic_{pos}"))
        view.add_item(Button(label="Restart Techno-Magic", style=discord.ButtonStyle.red,
                             custom_id=f"FCID{player['color']}_restartTechnoMagic_{pos}"))
        view.add_item(Button(label="Show Current Combat Turn", style=discord.ButtonStyle.blurple,
                             custom_id=f"FCID{player['color']}_refreshCombatPrompt_{pos}"))
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
        if game.gamestate["board"].get(pos, {}).get("technoMagicReady", {}).get(player["color"]):
            await interaction.followup.send("You have already finished Techno-Magic.", ephemeral=True)
            return
        UpgradeButtons.resetTechnoMagic(game, player, pos)
        await interaction.message.edit(content=f"{player['player_name']}, choose your Techno-Magic upgrades again.",
                                       view=UpgradeButtons.getTechnoMagicView(game, player, pos))

    @staticmethod
    async def startUpgrade(game: GamestateHelper, player, interaction: discord.Interaction,
                           button: bool, discTileUpgrade: str, action:str):
        drawing = DrawHelper(game.gamestate)
        image = await asyncio.to_thread(drawing.player_area, player)
        view = View()
        actions = str(FactionData.action_apt(player, "upgrade"))
        if not button:
            actions = "1"
        if action != "dum":
            actions = action
        if button and FactionData.has(player, "battle_focus"):
            player["battleFocusUsed"] = []
            game.update_player(PlayerHelper(game.get_player_from_color(player["color"]), player))
        used = set(player.get("battleFocusUsed", []))
        for ship in game.getShipsWithParts(player):
            if (FactionData.has(player, "battle_focus") and discTileUpgrade != "free"
                    and PlayerHelper.blueprint_key(game.getShipShortName(ship)) in used):
                continue
            shipEmoji = Emoji.getEmojiByName(player['color'] + game.getShipShortName(ship))
            view.add_item(Button(label=ship.capitalize(), emoji=shipEmoji, style=discord.ButtonStyle.blurple,
                                 custom_id=f"FCID{player['color']}_upgradeShip_{actions}_{ship}_{discTileUpgrade}"))
        if (discTileUpgrade in ("dummy", "free") and int(actions) > 0
                and FactionData.has(player, "adaptive_transformation")):
            view.add_item(Button(label="Adaptive Transformation", style=discord.ButtonStyle.green,
                                 custom_id=f"FCID{player['color']}_adaptiveStart_{actions}_{discTileUpgrade}"))
        if discTileUpgrade == "free" and player.get("infiniteUpgradeReturn") is not None:
            # the move/build disc is already spent; let Cog skip the free upgrade
            view.add_item(Button(label="Skip Upgrade", style=discord.ButtonStyle.red,
                                 custom_id=f"FCID{player['color']}_finishInfiniteUpgrade"))
        if not view.children:
            view.add_item(Button(label="Finish Action", style=discord.ButtonStyle.red,
                                 custom_id=f"FCID{player['color']}_finishAction"))
        await interaction.followup.send(file=await asyncio.to_thread(drawing.show_player_ship_area, image),
                                        ephemeral=True)
        # only a discovery tile part can be saved for a later Upgrade action
        if discTileUpgrade in DISCOVERY_PART_IDS:
            view.add_item(Button(label="Save For Future Upgrade Action", style=discord.ButtonStyle.red,
                                 custom_id=f"FCID{player['color']}_saveDiscoveryPart"))
        if button:
            await interaction.message.delete()
            if discTileUpgrade == "dummy":
                view.add_item(Button(label="Restart Turn", style=discord.ButtonStyle.gray,
                                     custom_id=f"FCID{player['color']}_restartTurn"))
                if actions == str(FactionData.action_apt(player, "upgrade")):
                    await interaction.channel.send(f"{player['player_name']} is using their turn to upgrade")

        message = f"{interaction.user.mention}, choose which ship you would like to upgrade."
        if player.get("infiniteUpgradeReturn") is not None:
            message += " Infinite Possibilities: one free Upgrade activation, then return to Build/Move if any remain."
        if FactionData.has(player, "battle_focus") and discTileUpgrade == "dummy":
            message += f" Battle Focus: {actions} Upgrade activations left; each must use a different ship class."
        await interaction.channel.send(message, view=view)

    @staticmethod
    async def finishInfiniteUpgrade(game: GamestateHelper, player, interaction: discord.Interaction,
                                   player_helper: PlayerHelper):
        """Return from the free Cog upgrade to the Build/Move action, or finish it."""
        return_to = player.pop("infiniteUpgradeReturn", "finish")
        player.pop("infiniteUpgradeAvailable", None)
        player.pop("adaptiveUndo", None)
        player.pop("upgradeUndo", None)
        game.update_player(player_helper)
        if interaction.message is not None:
            await interaction.message.delete()
        if return_to == "build":
            from Buttons.Build import BuildButtons
            await BuildButtons.startBuild(game, player, interaction, "startBuild2", player_helper)
        elif return_to.startswith("move"):
            from Buttons.Move import MoveButtons
            move_count = return_to.removeprefix("move") or "1"
            await MoveButtons.startMove(game, player, interaction, f"startMove_{move_count}", False)
        else:
            from Buttons.Turn import TurnButtons
            await TurnButtons.finishAction(player, game, interaction, player_helper)

    @staticmethod
    async def upgradeShip(game: GamestateHelper, player, interaction: discord.Interaction,
                          customID: str, player_helper: PlayerHelper):
        view = View()
        actions = customID.split("_")[1]
        ship = customID.split("_")[2]
        discTileUpgrade = customID.split("_")[3]
        # set by the part menu's Undo, so the parts image is not sent twice
        partsShown = "_partsShown" if customID.endswith("_partsShown") else ""
        if (FactionData.has(player, "battle_focus") and discTileUpgrade != "free"
                and PlayerHelper.blueprint_key(ship) in player.get("battleFocusUsed", [])):
            await interaction.followup.send("Battle Focus: you already upgraded that ship class this action.",
                                            ephemeral=True)
            return
        player_helper.renameOldExileParts(ship)
        player_helper.setOldShipParts(ship)
        game.update_player(player_helper)
        if discTileUpgrade == "mus":
            return await UpgradeButtons.chooseUpgrade(game, player, interaction,
                                                      f"chooseUpgrade_{actions}_{ship}_dummy_mus_5_mus", player_helper)
        with open("data/parts.json", "r") as f:
            part_stats = json.load(f)
        phase_slots = PlayerHelper.get_phase_module_slots(player, ship)
        for index,i in enumerate(player[f"{ship}_parts"]):
            if i == "mus" or index in phase_slots:
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
                                 custom_id=f"FCID{player['color']}_saveDiscoveryPart"))
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
        if int(indexOfOldPart) in PlayerHelper.get_phase_module_slots(player, ship):
            await interaction.followup.send("The Phase Module is built in and cannot be replaced.", ephemeral=True)
            return
        if discTileUpgrade not in ("dummy", "free", "phase") and not discTileUpgrade.startswith("tm"):
            return await UpgradeButtons.chooseUpgrade(game, player, interaction,
                                                      customID + "_" + discTileUpgrade, player_helper)

        available_parts = player_helper.getAvailableShipParts()
        if discTileUpgrade.startswith("tm"):
            # Techno-Magic: no removing ship parts, and no Ancient ship parts
            available_parts = {part for part in available_parts
                               if part != "empty" and part not in DISCOVERY_PART_IDS}
        slot_note = ""
        if UpgradeButtons.must_keep_drive(player, ship, oldPart):
            available_parts = {part for part in available_parts
                               if part != "empty" and UpgradeButtons.is_drive(part)}
            slot_note = " A Harvester must keep a Drive in this slot."
        spine_slot = int(indexOfOldPart) in PlayerHelper.get_spine_cannon_slots(player, ship)
        if spine_slot:
            # a Spine Cannon slot may be upgraded, but only with a gun
            available_parts = {part for part in available_parts
                               if part != "empty" and PlayerHelper.is_spine_gun(part)}
            slot_note = " This is a Spine Cannon slot, so it only accepts a gun (not a Missile or Rift Weapon)."
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
        removal_note = "" if discTileUpgrade.startswith("tm") or spine_slot \
            else " Selecting 'Empty' removes an installed tile for free, revealing the printed blueprint part."
        await UpgradeButtons.showMenu(interaction, f"{interaction.user.mention}, replace "
                                      f"{part_stats[oldPart]['name']} on your {ship} with which part?"
                                      f"{removal_note}{slot_note}", view)
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
        cog_free = (discTileUpgrade == "free" and FactionData.has(player, "infinite_possibilities")
                    and player.get("infiniteUpgradeReturn") is not None)
        if cog_free and not player.get("infiniteUpgradeAvailable"):
            await interaction.followup.send("That free upgrade activation was already used.", ephemeral=True)
            return
        if UpgradeButtons.must_keep_drive(player, ship, oldPart) and (
                newPart == "empty" or not UpgradeButtons.is_drive(newPart)):
            await interaction.followup.send("A Harvester must keep a Drive in this slot.", ephemeral=True)
            return
        with open("data/parts.json", "r") as f:
            part_stats = json.load(f)
        index = 0
        if newPart != "mus":
            index = int(indexOfOldPart)
            parts = player[f"{ship}_parts"]
            if not 0 <= index < len(parts) or parts[index] != oldPart:
                await interaction.followup.send("That ship slot has changed. Please use the latest upgrade menu.",
                                                ephemeral=True)
                return
        # The manual editor allows an empty slot over a printed part.
        isFreeRemoval = newPart == "empty" and (discTileUpgrade != "free" or cog_free)
        if isFreeRemoval:
            newPart = player[f"old_{ship}_parts"][index]
            if newPart == oldPart:
                await interaction.followup.send("That is the printed blueprint part; there is no installed tile to remove.",
                                                ephemeral=True)
                return False
        if (FactionData.has(player, "battle_focus") and discTileUpgrade == "dummy"
                and PlayerHelper.blueprint_key(ship) in player.get("battleFocusUsed", [])):
            await interaction.followup.send("That ship class already used this action's upgrade.", ephemeral=True)
            return
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
            if actions == FactionData.action_apt(player, "upgrade") - 1 and discTileUpgrade == "dummy":
                player_helper.spend_influence_on_action("upgrade")
            if FactionData.has(player, "battle_focus") and discTileUpgrade == "dummy":
                used = player_helper.stats.setdefault("battleFocusUsed", [])
                key = PlayerHelper.blueprint_key(ship)
                if key not in used:
                    used.append(key)
        if newPart in DISCOVERY_PART_IDS and newPart in player_helper.stats["ancient_parts"]:
            player_helper.stats["ancient_parts"].remove(newPart)
        oldName = "Nothing" if newPart == "mus" else part_stats[oldPart]['name']
        player_helper.stats[f"{ship}_parts"] = newParts
        if player_helper.stats.get("researchUpgrade") == discTileUpgrade:
            player_helper.stats.pop("researchUpgrade", None)
        if cog_free and not isFreeRemoval:
            player_helper.stats["infiniteUpgradeAvailable"] = False
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
        used = set(player_helper.stats.get("battleFocusUsed", []))
        free_editor = discTileUpgrade == "free" and not cog_free
        if actions > 0 and not player.get("passed") and (discTileUpgrade != "free" or free_editor):
            for ship2 in game.getShipsWithParts(player):
                if (FactionData.has(player, "battle_focus") and not free_editor
                        and PlayerHelper.blueprint_key(ship2) in used):
                    continue
                shipEmoji = Emoji.getEmojiByName(player['color'] + game.getShipShortName(ship2))
                view.add_item(Button(label=ship2.capitalize(), emoji=shipEmoji, style=discord.ButtonStyle.blurple,
                                     custom_id=(f"FCID{player['color']}_upgradeShip_"
                                                f"{actions}_{ship2}_{discTileUpgrade}")))
        if FactionData.has(player, "adaptive_transformation") and actions > 0 \
                and discTileUpgrade == "dummy":
            view.add_item(Button(label="Adaptive Transformation", style=discord.ButtonStyle.green,
                                 custom_id=f"FCID{player['color']}_adaptiveStart_{actions}_{discTileUpgrade}"))
        if discTileUpgrade == "phase":
            build_apt = FactionData.action_apt(player_helper.stats, "build")
            if player_helper.stats.get("passed") or player_helper.stats.get("pulsarBuild"):
                build_apt = 1
            if player_helper.stats.get("phaseBuildsThisAction", 0) < build_apt:
                view.add_item(Button(label="Build Activation", style=discord.ButtonStyle.green,
                                     custom_id=f"FCID{player['color']}_phaseTechResume"))
        if discTileUpgrade == "free":
            if cog_free:
                view.add_item(Button(label="Finish Upgrade", style=discord.ButtonStyle.red,
                                     custom_id=f"FCID{player['color']}_finishInfiniteUpgrade"))
            else:
                view.add_item(Button(label="Done", style=discord.ButtonStyle.red,
                                     custom_id=f"FCID{player['color']}_deleteMsg"))
        else:
            view.add_item(Button(label="Finish Action", style=discord.ButtonStyle.red,
                                 custom_id=f"FCID{player['color']}_finishAction"))
        view.add_item(Button(label="Undo", style=discord.ButtonStyle.gray,
                             custom_id=f"FCID{player['color']}_undoUpgrade_{customID.split('_')[1]}_{discTileUpgrade}"))
        if interaction.message is not None:
            try:
                await interaction.message.delete()
            except discord.DiscordServerError:
                logging.getLogger(__name__).warning("Upgrade saved, but Discord could not delete its old menu",
                                                    exc_info=True)
        await interaction.channel.send(f"{player['player_name']} replaced {oldName} with {part_stats[newPart]['name']}"
                                       f" on their {ship.capitalize()} which now looks like this:",
                                       file=await asyncio.to_thread(drawing.show_player_ship,
                                                                    image, ship, player_helper.stats["name"]))
        if discTileUpgrade == "free" and cog_free:
            await interaction.channel.send(f"{player['player_name']}, Infinite Possibilities: the free upgrade is complete.",
                                           view=view)
        elif discTileUpgrade == "free":
            await interaction.channel.send(f"{player['player_name']}, choose which ship you would like to upgrade "
                                           "or finish your action.", view=view)
        elif discTileUpgrade == "dummy":
            focus = (f" Battle Focus: {actions} Upgrade activations left; used classes: {', '.join(sorted(used)) or 'none'}."
                     if FactionData.has(player, "battle_focus") else "")
            await interaction.channel.send(f"{player['player_name']}, choose which ship you would like to upgrade "
                                           f"or finish your action.{focus}", view=view)
        elif discTileUpgrade == "phase":
            await interaction.channel.send(f"{player['player_name']}, you may continue the Build action"
                                           " or undo this part swap.", view=view)
        elif discTileUpgrade.startswith("tm"):
            view = UpgradeButtons.getTechnoMagicView(game, player, discTileUpgrade[2:])
            await interaction.channel.send(f"{player['player_name']}, choose another combat blueprint to upgrade"
                                           " or undo this Techno-Magic part.", view=view)

        return True

    @staticmethod
    def adaptiveSwaps(game: GamestateHelper, player, pos: str):
        """(source, target, materials) for each legal Adaptive Transformation in one sector."""
        ships = game.gamestate["board"][pos].get("player_ships", [])
        color = player["color"]
        counts = {ship: ships.count(f"{color}-{ship}") for ship in ("int", "cru", "drd")}
        stock = player["ship_stock"]
        swaps = []
        for (source, target), (source_count, target_count, materials) in ADAPTIVE_SWAPS.items():
            if counts[source] < source_count or stock[STOCK_INDEX[target]] < target_count:
                continue
            if materials < 0 and player["materials"] < -materials:
                continue
            swaps.append((source, target, materials))
        return swaps

    @staticmethod
    async def adaptiveStart(game: GamestateHelper, player, interaction: discord.Interaction,
                            customID: str):
        parts = customID.split("_")
        actions, mode = parts[1], parts[2]
        if mode not in ("dummy", "free"):
            await interaction.followup.send("That Adaptive Transformation is no longer legal.", ephemeral=True)
            return
        view = View()
        for pos in game.gamestate["board"]:
            if UpgradeButtons.adaptiveSwaps(game, player, pos):
                view.add_item(Button(label=game.get_tile_label(pos), style=discord.ButtonStyle.blurple,
                                     custom_id=f"FCID{player['color']}_adaptiveSector_{pos}_{actions}_{mode}"))
        if not view.children:
            await interaction.followup.send("No sector has the ships and materials for an Adaptive"
                                            " Transformation.", ephemeral=True)
            return
        await interaction.message.delete()
        await interaction.channel.send(f"{player['player_name']}, choose the sector for Adaptive Transformation.",
                                       view=view)

    @staticmethod
    async def adaptiveSector(game: GamestateHelper, player, interaction: discord.Interaction,
                             customID: str):
        parts = customID.split("_")
        pos, actions, mode = parts[1], parts[2], parts[3]
        view = View()
        names = {"int": "Interceptor", "cru": "Cruiser", "drd": "Dreadnought"}
        for source, target, materials in UpgradeButtons.adaptiveSwaps(game, player, pos):
            source_count, target_count, _materials = ADAPTIVE_SWAPS[(source, target)]
            if materials > 0:
                label = (f"{source_count} {names[source]}s -> {target_count} {names[target]}"
                         f" (+{materials} Materials)")
            else:
                label = (f"{source_count} {names[source]} -> {target_count} {names[target]}s"
                         f" ({materials} Materials)")
            view.add_item(Button(label=label, style=discord.ButtonStyle.blurple,
                                 custom_id=(f"FCID{player['color']}_adaptiveSwap_{source}_{target}_{pos}"
                                            f"_{actions}_{mode}")))
        view.add_item(Button(label="Back to Upgrade", style=discord.ButtonStyle.gray,
                             custom_id=f"FCID{player['color']}_backToUpgrade_{actions}_{mode}"))
        await interaction.message.delete()
        await interaction.channel.send(f"{player['player_name']}, choose the Adaptive Transformation in {pos}.",
                                       view=view)

    @staticmethod
    async def backToUpgrade(game: GamestateHelper, player, interaction: discord.Interaction,
                            customID: str):
        parts = customID.split("_")
        actions, mode = parts[1], parts[2]
        await interaction.message.delete()
        await UpgradeButtons.startUpgrade(game, player, interaction, False, mode, actions)

    @staticmethod
    async def adaptiveSwap(game: GamestateHelper, player, interaction: discord.Interaction,
                           customID: str, player_helper: PlayerHelper):
        parts = customID.split("_")
        source, target, pos, actions, mode = parts[1], parts[2], parts[3], int(parts[4]), parts[5]
        if mode not in ("dummy", "free") or (source, target) not in ADAPTIVE_SWAPS:
            await interaction.followup.send("That Adaptive Transformation is no longer legal.", ephemeral=True)
            return
        source_count, target_count, materials = ADAPTIVE_SWAPS[(source, target)]
        swap = (source, target, materials)
        if swap not in UpgradeButtons.adaptiveSwaps(game, player, pos):
            await interaction.followup.send("That Adaptive Transformation is no longer legal.", ephemeral=True)
            return
        if actions < 1:
            await interaction.followup.send("This action has no Upgrade activation left.", ephemeral=True)
            return
        previous_actions = actions
        undo = copy.deepcopy({key: value for key, value in player_helper.stats.items()
                              if key != "adaptiveUndo"})
        removed = [f"{player['color']}-{source}"] * source_count
        added = [f"{player['color']}-{target}"] * target_count
        game.remove_units(removed, pos)
        game.add_units(added, pos)
        player_helper.adjust_materials(swap[2])
        if mode == "free":
            actions = 0
            cog_free = player.get("infiniteUpgradeReturn") is not None
            if cog_free:
                player_helper.stats["infiniteUpgradeAvailable"] = False
        else:
            actions -= 1
            if actions == FactionData.action_apt(player, "upgrade") - 1:
                player_helper.spend_influence_on_action("upgrade")
        player_helper.specifyDetailsOfAction(
            f"Adaptive Transformation: {source_count} {source} -> {target_count} {target} in {pos}.")
        player_helper.stats["adaptiveUndo"] = {"stats": undo, "pos": pos, "removed": removed,
                                                "added": added, "actions": previous_actions, "mode": mode}
        game.update_player(player_helper)
        await interaction.message.delete()
        await interaction.channel.send(f"{player['player_name']} used Adaptive Transformation in {pos}:"
                                       f" {source_count} {source} became {target_count} {target};"
                                       f" {'gained' if materials > 0 else 'paid'} {abs(materials)} materials.")
        view = View()
        if mode == "free":
            if player.get("infiniteUpgradeReturn") is not None:
                view.add_item(Button(label="Finish Upgrade", style=discord.ButtonStyle.red,
                                     custom_id=f"FCID{player['color']}_finishInfiniteUpgrade"))
            else:
                view.add_item(Button(label="Done", style=discord.ButtonStyle.red,
                                     custom_id=f"FCID{player['color']}_deleteMsg"))
        else:
            if actions > 0:
                view.add_item(Button(label="Transform Again", style=discord.ButtonStyle.green,
                                     custom_id=f"FCID{player['color']}_adaptiveStart_{actions}_{mode}"))
                used = set(player_helper.stats.get("battleFocusUsed", []))
                for ship in game.getShipsWithParts(player):
                    if (FactionData.has(player, "battle_focus")
                            and PlayerHelper.blueprint_key(game.getShipShortName(ship)) in used):
                        continue
                    shipEmoji = Emoji.getEmojiByName(player['color'] + game.getShipShortName(ship))
                    view.add_item(Button(label=ship.capitalize(), emoji=shipEmoji,
                                         style=discord.ButtonStyle.blurple,
                                         custom_id=(f"FCID{player['color']}_upgradeShip_"
                                                    f"{actions}_{ship}_dummy")))
            view.add_item(Button(label="Finish Action", style=discord.ButtonStyle.red,
                                 custom_id=f"FCID{player['color']}_finishAction"))
        view.add_item(Button(label="Undo", style=discord.ButtonStyle.gray,
                             custom_id=f"FCID{player['color']}_undoAdaptive"))
        await interaction.channel.send(f"{player['player_name']}, choose your next Upgrade activation.", view=view)

    @staticmethod
    async def undoAdaptive(game: GamestateHelper, player, interaction: discord.Interaction,
                           player_helper: PlayerHelper):
        undo = player.get("adaptiveUndo")
        if undo is None:
            await interaction.followup.send("There is no Adaptive Transformation to undo.", ephemeral=True)
            return
        tile = game.gamestate["board"][undo["pos"]]
        if any(tile["player_ships"].count(ship) < undo["added"].count(ship)
               for ship in undo["added"]):
            await interaction.followup.send("Those ships have moved; the transformation can no longer be undone.",
                                            ephemeral=True)
            return
        game.remove_units(undo["added"], undo["pos"])
        game.add_units(undo["removed"], undo["pos"])
        player_helper.stats.clear()
        player_helper.stats.update(undo["stats"])
        player_helper.stats.pop("adaptiveUndo", None)
        game.update_player(player_helper)
        await interaction.message.delete()
        await interaction.channel.send(f"{player['player_name']} undid the Adaptive Transformation.")
        await UpgradeButtons.startUpgrade(game, player, interaction, False,
                                          "free" if undo["mode"] == "free" else "dummy",
                                          str(undo["actions"]))

    @staticmethod
    async def undoUpgrade(game: GamestateHelper, player, interaction: discord.Interaction,
                          customID: str, player_helper: PlayerHelper):
        parts = customID.split("_")
        # Undo buttons posted before the upgrade mode joined the id carry only the action count
        mode = parts[2] if len(parts) > 2 else "dummy"
        if mode.startswith("tm"):
            if game.gamestate["board"].get(mode[2:], {}).get("technoMagicReady", {}).get(player["color"]):
                await interaction.followup.send("You have already finished Techno-Magic.", ephemeral=True)
                return
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
