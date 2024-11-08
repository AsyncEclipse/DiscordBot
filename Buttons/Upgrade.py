import asyncio
import json
import discord
from discord.ui import View
from helpers.EmojiHelper import Emoji
from helpers.GamestateHelper import GamestateHelper
from helpers.PlayerHelper import PlayerHelper
from helpers.DrawHelper import DrawHelper
from discord.ui import View, Button
from helpers.ShipHelper import PlayerShip

class UpgradeButtons:

    @staticmethod
    async def startUpgrade(game: GamestateHelper, player, interaction: discord.Interaction, button:bool, discTileUpgrade:str):
        ships = ["interceptor","cruiser","dread","starbase"]
        drawing = DrawHelper(game.gamestate)
        image = await asyncio.to_thread(drawing.player_area,player)
        view = View()
        actions = str(player['upgrade_apt'])
        if not button:
            actions = "1"
        for ship in ships:
            shipEmoji = Emoji.getEmojiByName(player['color']+game.getShipShortName(ship))
            view.add_item(Button(label=ship.capitalize(), emoji = shipEmoji, style=discord.ButtonStyle.blurple, custom_id=f"FCID{player['color']}_upgradeShip_{actions}_{ship}_{discTileUpgrade}"))
        await interaction.followup.send(file=await asyncio.to_thread(drawing.show_player_ship_area,image),ephemeral=True)
        if discTileUpgrade != "dummy":
            view.add_item(Button(label="Save For Future Upgrade Action", style=discord.ButtonStyle.red, custom_id=f"FCID{player['color']}_deleteMsg"))
        if button:
            await interaction.message.delete()
            if discTileUpgrade == "dummy":
                view.add_item(Button(label="Restart Turn", style=discord.ButtonStyle.gray, custom_id=f"FCID{player['color']}_restartTurn"))
        
        await interaction.channel.send(
            f"{interaction.user.mention}, choose which ship you would like to upgrade.", view=view)

    @staticmethod
    async def upgradeShip(game: GamestateHelper, player, interaction: discord.Interaction, customID : str, player_helper:PlayerHelper):
        view = View()
        actions = customID.split("_")[1]
        ship = customID.split("_")[2]
        discTileUpgrade = customID.split("_")[3]
        player_helper.setOldShipParts(ship)
        game.update_player(player_helper)
        if discTileUpgrade == "mus":
            await UpgradeButtons.chooseUpgrade(game, player, interaction, f"chooseUpgrade_{actions}_{ship}_dummy_mus_mus",player_helper)
            return
        with open("data/parts.json", "r") as f:
            part_stats = json.load(f)
        for i in set(player[f"{ship}_parts"]):
            if i == "mus":
                continue
            part_details = part_stats.get(i)
            partName = part_details["name"].lower().replace(" ", "_") if part_details else i
            view.add_item(Button(label=part_stats[i]["name"], style=discord.ButtonStyle.blurple, emoji= Emoji.getEmojiByName(partName), custom_id=f"FCID{player['color']}_selectOldPart_{actions}_{ship}_{i}_{discTileUpgrade}"))
        await interaction.message.edit(content=f"{interaction.user.mention}, pick which part to replace or remove.",
                                                view=view)
    @staticmethod
    async def selectOldPart(game: GamestateHelper, player, interaction: discord.Interaction, customID : str, player_helper:PlayerHelper):
        view = View()
        actions = customID.split("_")[1]
        ship = customID.split("_")[2]
        oldPart = customID.split("_")[3]
        discTileUpgrade = customID.split("_")[4]

        if discTileUpgrade != "dummy":
            await UpgradeButtons.chooseUpgrade(game, player, interaction, customID+"_"+discTileUpgrade,player_helper)
            return


        available_parts = ["ioc", "elc", "nud", "hul", "nus","empty"]
        drawing = DrawHelper(game.gamestate)
        with open("data/parts.json", "r") as f:
            part_stats = json.load(f)
        for tech in part_stats:
            if tech in player["military_tech"]:
                available_parts.append(tech)
            if tech in player["grid_tech"]:
                available_parts.append(tech)
            if tech in player["nano_tech"]:
                available_parts.append(tech)
            if "ancient_parts" in player and tech in player["ancient_parts"]:
                available_parts.append(tech)
        available_parts = set(available_parts)
        with open("data/parts.json", "r") as f:
                part_data = json.load(f)
        
           
        for i in available_parts:
            part_details = part_data.get(i)
            partName = part_details["name"].lower().replace(" ", "_") if part_details else i
            
            view.add_item(Button(label=part_stats[i]["name"], style=discord.ButtonStyle.blurple, custom_id=f"FCID{player['color']}_chooseUpgrade_{actions}_{ship}_{oldPart}_{i}_{discTileUpgrade}", emoji=Emoji.getEmojiByName(partName)))
        await interaction.message.edit(content=f"{interaction.user.mention}, replace "
                                                        f"{part_stats[oldPart]['name']} with which part? Remove as a free action by selecting 'Empty'.", view=view)
        view.add_item(Button(label="Go back 1 Step", style=discord.ButtonStyle.red, custom_id=f"FCID{player['color']}_upgradeShip_{actions}_{ship}_{discTileUpgrade}"))
        await interaction.followup.send("Available parts", file=await asyncio.to_thread(drawing.availablePartsFile,available_parts),ephemeral=True)
    @staticmethod
    async def chooseUpgrade(game: GamestateHelper, player, interaction: discord.Interaction, customID : str,player_helper : PlayerHelper):
        actions = int(customID.split("_")[1])
        ship = customID.split("_")[2]
        oldPart = customID.split("_")[3]
        newPart = customID.split("_")[4]
        discTileUpgrade = customID.split("_")[5]
        with open("data/parts.json", "r") as f:
            part_stats = json.load(f)
        index = 0
        if newPart != "mus":
            index = player[f"{ship}_parts"].index(oldPart)
        if newPart != "empty":
            if newPart != oldPart:
                actions -= 1
                if actions == player['upgrade_apt']-1 and discTileUpgrade == "dummy":
                    player_helper.spend_influence_on_action("upgrade")
        else:
            newPart = player[f"old_{ship}_parts"][index]
        if newPart in ["anm", "axc", "cod", "fls", "hyg", "ins", "iod", "iom", "iot", "jud", "mus", "ricon", "shh", "som", "socha", "mos","plt", "nod"] and newPart in player_helper.stats["ancient_parts"]:
            player_helper.stats["ancient_parts"].remove(newPart)
        oldName = ""
        if newPart == "mus":
            player_helper.stats[f"{ship}_parts"].append("mus")
            oldName = "Nothing"
        else:
            player_helper.stats[f"{ship}_parts"][index] = newPart
            oldName = part_stats[oldPart]['name']
        shipCheck = PlayerShip(player_helper.stats, ship)
        if not shipCheck.check_valid_ship():
            await interaction.followup.send("Your ship is not valid! Please try a different part",ephemeral=True)
            return
        player_helper.specifyDetailsOfAction(f"Replaced {oldName} with {part_stats[newPart]['name']} on their {ship.capitalize()}.")
        game.update_player(player_helper)
        drawing = DrawHelper(game.gamestate)
        image = await asyncio.to_thread(drawing.player_area,player_helper.stats)
        view = View()
        if actions > 0 and ("passed" not in player or player["passed"] != True):
            ships = ["interceptor","cruiser","dread","starbase"]
            for ship2 in ships:
                shipEmoji = Emoji.getEmojiByName(player['color']+game.getShipShortName(ship2))
                view.add_item(Button(label=ship2.capitalize(),emoji=shipEmoji, style=discord.ButtonStyle.blurple, custom_id=f"FCID{player['color']}_upgradeShip_{str(actions)}_{ship2}_dummy"))
        view.add_item(Button(label="Finish Action", style=discord.ButtonStyle.red,
                             custom_id=f"FCID{player['color']}_finishAction"))
        await interaction.message.delete()
        await interaction.channel.send(f"{player['player_name']} replaced {oldName} with {part_stats[newPart]['name']} on their {ship.capitalize()} which now looks like this",file=await asyncio.to_thread(drawing.show_player_ship,image, ship))
        if discTileUpgrade == "dummy":
            await interaction.channel.send(
                f"{player['player_name']}, choose which ship you would like to upgrade or finish your action.",
                view=view)


