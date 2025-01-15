import asyncio
import json
import discord
from Buttons.Upgrade import UpgradeButtons
from helpers.GamestateHelper import GamestateHelper
from helpers.PlayerHelper import PlayerHelper
from helpers.DrawHelper import DrawHelper
from discord.ui import View, Button


class DiscoveryTileButtons:
    @staticmethod
    async def exploreDiscoveryTile(game: GamestateHelper, tile: str, interaction: discord.Interaction, player):
        # if "discTiles" not in game.gamestate:
        #    game.fillInDiscTiles()
        if game.gamestate["board"][tile]["disctile"] == 0:
            await interaction.followup.send("No discovery tile in tile " + tile)
            return
        disc = game.getNextDiscTile(tile)
        with open("data/discoverytiles.json") as f:
            discTile_data = json.load(f)
        discName = discTile_data[disc]["name"]
        drawing = DrawHelper(game.gamestate)
        file = await asyncio.to_thread(drawing.show_disc_tile, discName)
        msg = (f"{player['player_name']} you explored a discovery tile and found a {discName}. "
               "You may keep it for 2 points at the end of the game or use it for its ability.")

        view = View()
        view.add_item(Button(label="Use it for its ability", style=discord.ButtonStyle.green,
                             custom_id=f"FCID{player['color']}_usedDiscForAbility_{disc}_{tile}"))
        view.add_item(Button(label="Get 2 Points", style=discord.ButtonStyle.red, custom_id=f"FCID{player['color']}_keepDiscForPoints"))
        asyncio.create_task(interaction.channel.send(msg, view=view, file=file))

    @staticmethod
    async def keepDiscForPoints(game: GamestateHelper, player_helper: PlayerHelper, interaction: discord.Interaction):
        player_helper.acquire_disc_tile_for_points()
        game.update_player(player_helper)
        await interaction.message.edit(view=None)
        await interaction.channel.send(f"{player_helper.stats['player_name']} chose to keep the tile for 2 points")

    @staticmethod
    async def usedDiscForAbility(game: GamestateHelper, player_helper: PlayerHelper,
                                 interaction: discord.Interaction, buttonID: str, player):
        disc = buttonID.split("_")[1]
        tile = buttonID.split("_")[2]
        with open("data/discoverytiles.json") as f:
            discTile_data = json.load(f)
        discName = discTile_data[disc]["name"]
        await interaction.message.edit(view=None)
        await interaction.channel.send(f"{player['player_name']} chose to use the '{discName}' ability")
        if disc == "rep" or disc == "art":
            if "discoveryTileBonusPointTiles" not in player_helper.stats:
                player_helper.stats["discoveryTileBonusPointTiles"] = []
            player_helper.stats["discoveryTileBonusPointTiles"].append(disc)
            game.update_player(player_helper)
        if discTile_data[disc]["part"] != "":
            player_helper.stats["ancient_parts"].append(discTile_data[disc]["part"])
            if "magPartPoints" in player_helper.stats:
                player_helper.stats["magPartPoints"] += 1
            game.update_player(player_helper)
            await UpgradeButtons.startUpgrade(game, player, interaction, False, str(discTile_data[disc]["part"]),"dum")
        elif discTile_data[disc]["gain1"] != 0:
            techsAvailable = game.gamestate["available_techs"]
            with open("data/techs.json", "r") as f:
                tech_data = json.load(f)
            minCost = 20
            ownedTechs = player_helper.getTechs()
            for tech in techsAvailable:
                if tech in ownedTechs:
                    continue
                tech_details = tech_data.get(tech)
                minCost = min(minCost, tech_details["base_cost"])
            cheapestTechs = []
            for tech in techsAvailable:
                if tech in ownedTechs:
                    continue
                tech_details = tech_data.get(tech)
                if minCost == tech_details["base_cost"] and tech not in cheapestTechs:
                    cheapestTechs.append(tech)
            if len(cheapestTechs) > 1:
                view = View()
                for tech in cheapestTechs:
                    tech_details = tech_data.get(tech)
                    view.add_item(Button(label=tech_details["name"], style=discord.ButtonStyle.green,
                                         custom_id=f"FCID{player['color']}_getFreeTech_{tech}"))
                await interaction.channel.send("Choose the tech you would like to gain", view=view)
            else:
                await DiscoveryTileButtons.getFreeTech(game, interaction, "spoof_" + cheapestTechs[0], player)
        elif discTile_data[disc]["spawn"] != 0:
            if discTile_data[disc]["spawn"] == "cruiser":
                game.add_units([player["color"] + "-cru"], tile)
            if discTile_data[disc]["spawn"] == "orbital":
                game.add_units([player["color"] + "-orb"], tile)
            if discTile_data[disc]["spawn"] == "monolith":
                game.add_units([player["color"] + "-mon"], tile)
            if discTile_data[disc]["spawn"] == "warp":
                game.add_warp(tile)
            await interaction.channel.send(f"{player['player_name']} added a"
                                           f" {discTile_data[disc]['spawn']} to tile {tile}.")
            if discTile_data[disc]["material"] != 0:
                await interaction.channel.send(player_helper.adjust_materials(discTile_data[disc]["material"]))
        else:
            if discTile_data[disc]["material"] != 0:
                await interaction.channel.send(player_helper.adjust_materials(discTile_data[disc]["material"]))
            if discTile_data[disc]["science"] != 0:
                await interaction.channel.send(player_helper.adjust_science(discTile_data[disc]["science"]))
            if discTile_data[disc]["money"] != 0:
                await interaction.channel.send(player_helper.adjust_money(discTile_data[disc]["money"]))
            if discTile_data[disc]["any"] != 0:
                view = View()
                for resource_type, button_style in [("materials", discord.ButtonStyle.gray),
                                                    ("money", discord.ButtonStyle.blurple),
                                                    ("science", discord.ButtonStyle.green)]:
                    view.add_item(Button(label=f"Gain 3 {resource_type.capitalize()}",
                                         style=button_style,
                                         custom_id=f"FCID{player_helper.stats['color']}_gain3resource_{resource_type}"))
                await interaction.channel.send("You may gain 3 of any type of resource.", view=view)
        game.update_player(player_helper)

    @staticmethod
    async def getFreeTech(game: GamestateHelper, interaction: discord.Interaction, buttonID: str, player):
        tech = buttonID.split("_")[1]
        with open("data/techs.json", "r") as f:
            tech_data = json.load(f)
        tech_type = tech_data.get(tech)["track"]
        if "spoof" not in buttonID:
            await interaction.message.delete()
        if tech_type == "any":
            if len(buttonID.split("_")) == 3:
                tech_type = buttonID.split("_")[2]
            else:
                view = View()
                view.add_item(Button(label="Military (Pink)", style=discord.ButtonStyle.red,
                                         custom_id=f"FCID{player['color']}_getFreeTech_{tech}_military"))
                view.add_item(Button(label="Grid (Green)", style=discord.ButtonStyle.green,
                                         custom_id=f"FCID{player['color']}_getFreeTech_{tech}_grid"))
                view.add_item(Button(label="Nano (Yellow)", style=discord.ButtonStyle.gray,
                                         custom_id=f"FCID{player['color']}_getFreeTech_{tech}_nano"))
                await interaction.channel.send(f"{player['player_name']} please choose the track this ancient tech should go on.",
                                           view=view)
                return
        game.playerResearchTech(game.get_player_from_color(player["color"]), tech, tech_type)
        tech_details = tech_data.get(tech)
        image = DrawHelper.show_tech_ref_image(tech_details["name"], tech_details['track'])
        await interaction.channel.send(f"{player['player_name']} acquired the tech {tech_details['name']}.",
                                        file=image)
