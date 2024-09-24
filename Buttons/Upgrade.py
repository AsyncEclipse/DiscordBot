import json
import discord
from discord.ui import View
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
        image = drawing.player_area(player)
        view = View()
        actions = str(player['upgrade_apt'])
        for ship in ships:
            view.add_item(Button(label=ship.capitalize(), style=discord.ButtonStyle.blurple, custom_id=f"FCID{player['color']}_upgradeShip_{actions}_{ship}_{discTileUpgrade}"))

        if button and discTileUpgrade != "dummy":
            view.add_item(Button(label="End Turn", style=discord.ButtonStyle.red, custom_id=f"FCID{player['color']}_endTurn"))
            view.add_item(Button(label="Restart Turn", style=discord.ButtonStyle.gray, custom_id=f"FCID{player['color']}_restartTurn"))
            await interaction.message.delete()
        if discTileUpgrade == "dummy":
            await interaction.response.send_message(file=drawing.show_player_ship_area(image),ephemeral=True)
        else:
            await interaction.response.send_message(file=drawing.show_player_ship_area(image),ephemeral=True)
            view.add_item(Button(label="Save For Future Upgrade Action", style=discord.ButtonStyle.red, custom_id=f"FCID{player['color']}_deleteMsg"))
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
        with open("data/parts.json", "r") as f:
            part_stats = json.load(f)
        for i in set(player[f"{ship}_parts"]):
            view.add_item(Button(label=part_stats[i]["name"], style=discord.ButtonStyle.blurple, custom_id=f"FCID{player['color']}_selectOldPart_{actions}_{ship}_{i}_{discTileUpgrade}"))
        await interaction.response.edit_message(content=f"{interaction.user.mention}, pick which part to replace or remove.",
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
        for i in available_parts:
            view.add_item(Button(label=part_stats[i]["name"], style=discord.ButtonStyle.blurple, custom_id=f"FCID{player['color']}_chooseUpgrade_{actions}_{ship}_{oldPart}_{i}_{discTileUpgrade}"))
        await interaction.response.edit_message(content=f"{interaction.user.mention}, replace "
                                                        f"{part_stats[oldPart]['name']} with which part? Remove as a free action by selecting 'Empty'.", view=view)
        await interaction.followup.send("Available parts", file=drawing.availablePartsFile(available_parts),ephemeral=True)
    @staticmethod
    async def chooseUpgrade(game: GamestateHelper, player, interaction: discord.Interaction, customID : str,player_helper : PlayerHelper):
        actions = int(customID.split("_")[1])
        ship = customID.split("_")[2]
        oldPart = customID.split("_")[3]
        newPart = customID.split("_")[4]
        discTileUpgrade = customID.split("_")[5]
        with open("data/parts.json", "r") as f:
            part_stats = json.load(f)
        index = player[f"{ship}_parts"].index(oldPart)
        if newPart != "empty":
            if newPart != oldPart:
                actions -= 1
                if actions == player['upgrade_apt']-1 and discTileUpgrade == "dummy":
                    player_helper.spend_influence_on_action("upgrade")
        else:
            newPart = player[f"old_{ship}_parts"][index]
        if newPart in ["anm", "axc", "cod", "fls", "hyg", "ins", "iod", "iom", "iot", "jud", "mus", "ricon", "shd", "som", "socha"] and newPart in player_helper.stats["ancient_parts"]:
            player_helper.stats["ancient_parts"].remove(newPart)
        player_helper.stats[f"{ship}_parts"][index] = newPart
        shipCheck = PlayerShip(player_helper.stats, ship)
        if not shipCheck.check_valid_ship():
            await interaction.channel.send("Your ship is not valid! Please try a different part", ephemeral=True)
            return
        
        game.update_player(player_helper)
        drawing = DrawHelper(game.gamestate)
        image = drawing.player_area(player_helper.stats)
        view = View()
        if actions > 0:
            ships = ["interceptor","cruiser","dread","starbase"]
            for ship2 in ships:
                view.add_item(Button(label=ship2.capitalize(), style=discord.ButtonStyle.blurple, custom_id=f"FCID{player['color']}_upgradeShip_{str(actions)}_{ship2}_dummy"))
        view.add_item(Button(label="End Turn", style=discord.ButtonStyle.red, custom_id=f"FCID{player['color']}_endTurn"))
        await interaction.message.delete()
        await interaction.channel.send(f"{interaction.user.mention} replaced {part_stats[oldPart]['name']} with {part_stats[newPart]['name']} on their {ship.capitalize()} which now looks like this",file=drawing.show_player_ship_area(image))
        if discTileUpgrade == "dummy":
            await interaction.channel.send(
                f"{interaction.user.mention}, choose which ship you would like to upgrade or end turn.", view=view)


