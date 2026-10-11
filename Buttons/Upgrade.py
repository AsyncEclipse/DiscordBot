import asyncio
import json
import discord
from helpers.EmojiHelper import Emoji
from helpers.GamestateHelper import GamestateHelper
from helpers.PlayerHelper import PlayerHelper
from helpers.DrawHelper import DrawHelper
from discord.ui import View, Button
from helpers.ShipHelper import PlayerShip


class UpgradeButtons:
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
        if discTileUpgrade != "dummy":
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
                                            f"{actions}_{ship}_{i.replace('_','')}_{discTileUpgrade}_{str(index)}")))
            if i == "iot_exile":
                player_helper.stats[f"{ship}_parts"] = ["iotexile" if s == "iot_exile" else s for s in player_helper.stats[f"{ship}_parts"]]  
                game.update_player(player_helper)
        view.add_item(Button(label="Choose Different Ship", style=discord.ButtonStyle.gray,
                                 custom_id=(f"FCID{player['color']}_chooseDifferentShip_"
                                            f"{actions}_{discTileUpgrade}")))
        if discTileUpgrade != "dummy":
            view.add_item(Button(label="Save For Future Upgrade Action", style=discord.ButtonStyle.red,
                                 custom_id=f"FCID{player['color']}_deleteMsg"))
        await interaction.message.edit(content=(f"{interaction.user.mention}, "
                                                f"pick which part of your {ship} to replace or remove."),
                                       view=view)

    @staticmethod
    async def selectOldPart(game: GamestateHelper, player, interaction: discord.Interaction,
                            customID: str, player_helper: PlayerHelper):
        view = View()
        actions = customID.split("_")[1]
        ship = customID.split("_")[2]
        oldPart = customID.split("_")[3]
        discTileUpgrade = customID.split("_")[4]
        indexOfOldPart = customID.split("_")[5]
        if discTileUpgrade != "dummy":
            await UpgradeButtons.chooseUpgrade(game, player, interaction,
                                               customID + "_" + discTileUpgrade, player_helper)
            return

        available_parts = player_helper.getAvailableShipParts()
        drawing = DrawHelper(game.gamestate)
        with open("data/parts.json", "r") as f:
            part_stats = json.load(f)

        view.add_item(Button(label="Undo", style=discord.ButtonStyle.red,
                             custom_id=f"FCID{player['color']}_upgradeShip_{actions}_{ship}_{discTileUpgrade}"))
        for i in available_parts:
            part_details = part_stats.get(i)
            partName = part_details["name"].lower().replace(" ", "_") if part_details else i
            if len(view.children) >= 25:
                break
            view.add_item(Button(label=part_stats[i]["name"], style=discord.ButtonStyle.blurple,
                                 custom_id=(f"FCID{player['color']}_chooseUpgrade_{actions}_{ship}_"
                                            f"{oldPart}_{i}_{indexOfOldPart}_{discTileUpgrade}"),
                                 emoji=Emoji.getEmojiByName(partName)))
        await interaction.message.edit(content=f"{interaction.user.mention}, replace "
                                       f"{part_stats[oldPart]['name']} on your {ship} with which part? "
                                       "Remove as a free action by selecting 'Empty'.", view=view)
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
        isFreeRemoval = newPart == "empty"
        if isFreeRemoval:
            newPart = player[f"old_{ship}_parts"][index]
        newParts = list(player[f"{ship}_parts"])
        if newPart == "mus":
            newParts.append("mus")
        else:
            newParts[index] = newPart
        # Validate before charging anything: an illegal build must not cost the player a disc.
        candidate = dict(player_helper.stats)
        candidate[f"{ship}_parts"] = newParts
        if not PlayerShip(candidate, ship).check_valid_ship():
            await interaction.followup.send("Your ship is not valid! Please try a different part", ephemeral=True)
            return
        if not isFreeRemoval and newPart != oldPart:
            actions -= 1
            if actions == player['upgrade_apt'] - 1 and discTileUpgrade == "dummy":
                player_helper.spend_influence_on_action("upgrade")
        ancientTech = ["anm", "axc", "cod", "fls", "hyg", "ins", "iod", "iom", "iot",
                       "jud", "mus", "ricon", "shh", "som", "socha", "mos", "plt", "nod"]
        if newPart in ancientTech and newPart in player_helper.stats["ancient_parts"]:
            player_helper.stats["ancient_parts"].remove(newPart)
        oldName = "Nothing" if newPart == "mus" else part_stats[oldPart]['name']
        player_helper.stats[f"{ship}_parts"] = newParts
        player_helper.specifyDetailsOfAction(f"Replaced {oldName} with {part_stats[newPart]['name']}"
                                             f" on their {ship.capitalize()}.")
        game.update_player(player_helper)
        drawing = DrawHelper(game.gamestate)
        image = await asyncio.to_thread(drawing.player_area, player_helper.stats)
        view = View()
        if actions > 0 and not player.get("passed"):
            for ship2 in game.getShipsWithParts(player):
                shipEmoji = Emoji.getEmojiByName(player['color'] + game.getShipShortName(ship2))
                view.add_item(Button(label=ship2.capitalize(), emoji=shipEmoji, style=discord.ButtonStyle.blurple,
                                     custom_id=f"FCID{player['color']}_upgradeShip_{str(actions)}_{ship2}_dummy"))
        view.add_item(Button(label="Finish Action", style=discord.ButtonStyle.red,
                             custom_id=f"FCID{player['color']}_finishAction"))
        view.add_item(Button(label="Restart Turn", style=discord.ButtonStyle.gray,
                             custom_id=f"FCID{player['color']}_restartTurn"))
        await interaction.message.delete()
        await interaction.channel.send(f"{player['player_name']} replaced {oldName} with {part_stats[newPart]['name']}"
                                       f" on their {ship.capitalize()} which now looks like this:",
                                       file=await asyncio.to_thread(drawing.show_player_ship,
                                                                    image, ship, player_helper.stats["name"]))
        if discTileUpgrade == "dummy":
            await interaction.channel.send(f"{player['player_name']}, choose which ship you would like to upgrade "
                                           "or finish your action.", view=view)
