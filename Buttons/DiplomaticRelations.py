import json
import discord
from discord.ui import View
from helpers.GamestateHelper import GamestateHelper
from helpers.DrawHelper import DrawHelper
from discord.ui import View, Button
from jproperties import Properties

from helpers.PlayerHelper import PlayerHelper


class DiplomaticRelationsButtons:


    @staticmethod
    async def startDiplomaticRelations(game: GamestateHelper, player, interaction: discord.Interaction):
        view = View()
        for p2 in DiplomaticRelationsButtons.getPlayersWithWhichDiplomatcRelationsCanBeFormed(game, player):
            buttonID = f"FCID{player['color']}_offerRelationsTo_"+game.get_gamestate()["players"][p2]["color"]
            label = f"{game.get_gamestate()['players'][p2]['name']}"
            view.add_item(Button(label=label, style=discord.ButtonStyle.blurple, custom_id=buttonID))
        await interaction.channel.send( f"{interaction.user.mention}, choose which player you would like to offer diplomatic relations to", view=view)
    @staticmethod
    def getPlayersWithWhichDiplomatcRelationsCanBeFormed(game: GamestateHelper, player):
        from Buttons.Influence import InfluenceButtons
        players = []
        configs = Properties()
        with open("data/tileAdjacencies.properties", "rb") as f:
            configs.load(f)
        for p2 in game.get_gamestate()["players"]:
            if game.get_gamestate()["players"][p2]["color"] == player["color"]:
                continue
            if "traitor" in game.get_gamestate()["players"][p2] and game.get_gamestate()["players"][p2]["traitor"] == True:
                continue
            allowable = False
            alreadyFriends = False
            for tile in game.get_gamestate()["players"][p2]["owned_tiles"]:
                for tile2 in player["owned_tiles"]:
                    if InfluenceButtons.areTwoTilesAdjacent(game, tile, tile2, configs, False):
                        for rep in game.get_gamestate()["players"][p2]["reputation_track"]:
                            if isinstance(rep, str) and player["color"] in rep:
                                alreadyFriends = True
                        allowable = True
            if allowable and not alreadyFriends:
                players.append(p2)

        return players


    @staticmethod
    async def offerRelationsTo(game: GamestateHelper, player, interaction: discord.Interaction, buttonID:str):
        view = View()
        p2 = buttonID.split("_")[1]
        buttonID1 = f"FCID{p2}_acceptRelationsWith_"+player["color"]
        buttonID2 = f"FCID{p2}_declineRelationsWith_"+player["color"]
        pID = game.get_player_from_color(p2)
        view.add_item(Button(label="Accept", style=discord.ButtonStyle.green, custom_id=buttonID1))
        view.add_item(Button(label="Decline", style=discord.ButtonStyle.red, custom_id=buttonID2))
        await interaction.channel.send( f"{game.get_gamestate()['players'][pID]['player_name']}, choose whether you will accept diplomatic relations from {interaction.user.mention}", view=view)
        await interaction.message.delete()

    @staticmethod
    async def declineRelationsWith(game: GamestateHelper, player, interaction: discord.Interaction, buttonID:str):
        p2 = buttonID.split("_")[1]
        pID = game.get_player_from_color(p2)
        await interaction.channel.send( f"{game.get_gamestate()['players'][pID]['player_name']} your relations have been refused by {interaction.user.mention}")
        await interaction.message.delete()

    @staticmethod
    async def acceptRelationsWith(game: GamestateHelper, player, interaction: discord.Interaction, buttonID:str):
        p2 = buttonID.split("_")[1]
        pID = game.get_player_from_color(p2)
        await interaction.followup.send( f"{game.get_gamestate()['players'][pID]['player_name']} your relations have been accepted by {interaction.user.mention}")
        p2 = game.get_gamestate()["players"][pID]
        game.formRelationsBetween(player,p2)

        for p in [player,p2]:
            view = View()
        
            if p["material_pop_cubes"] > 0:
                view.add_item(Button(label="Material", style=discord.ButtonStyle.gray, custom_id=f"FCID{p['color']}_reducePopFor_material"))
            if p["science_pop_cubes"] > 0:
                view.add_item(Button(label="Science", style=discord.ButtonStyle.gray, custom_id=f"FCID{p['color']}_reducePopFor_science"))
            if p["money_pop_cubes"] > 0:
                view.add_item(Button(label="Money", style=discord.ButtonStyle.gray, custom_id=f"FCID{p['color']}_reducePopFor_money"))
            await interaction.channel.send( f"{p['player_name']} choose what type of cube to put on the ambassador", view=view)

        if "dummy" not in buttonID:
            await interaction.message.delete()

    @staticmethod
    async def breakRelationsWith(game: GamestateHelper, player, p2, interaction: discord.Interaction):
        
        await interaction.followup.send( f"{p2['player_name']} your relations have been broken with {interaction.user.mention}")
        game.breakRelationsBetween(player,p2)
        for p in [player,p2]:
            view=View()
            planetTypes = ["money","science","material"]
            for planetT in planetTypes:
                if p[planetT+"_pop_cubes"] < 13:
                    view.add_item(Button(label=planetT.capitalize(), style=discord.ButtonStyle.blurple, custom_id=f"FCID{p['color']}_addCubeToTrack_"+planetT))
            await interaction.channel.send( f"{p['player_name']} a cube with no set track was removed, please tell the bot what track you want it to go on", view=view)

    
    @staticmethod
    async def reducePopFor(game: GamestateHelper, player_helper :PlayerHelper, interaction: discord.Interaction, buttonID:str):
        type = buttonID.split("_")[1]
        if type == "money":
            player_helper.adjust_money_cube(-1)
        if type == "science":
            player_helper.adjust_science_cube(-1)
        if type == "material":
            player_helper.adjust_material_cube(-1)
        game.update_player(player_helper)
        await interaction.channel.send( f"{interaction.user.mention} put a {type} cube down")
        await interaction.message.delete()
    
   




