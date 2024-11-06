import json
import discord
from discord.ui import View
from helpers.EmojiHelper import Emoji
from helpers.GamestateHelper import GamestateHelper
from helpers.DrawHelper import DrawHelper
from discord.ui import View, Button
from jproperties import Properties

from helpers.PlayerHelper import PlayerHelper


class DiplomaticRelationsButtons:

    @staticmethod
    def getMinorSpeciesCost(minor_species:str):
        minor = minor_species.lower()
        if "cube" in minor:
            return 9
        if "monolith" in minor:
            return 6
        if "three" in minor or "reputation" in minor:
            return 8
        return 4

    @staticmethod
    async def startMinorRelations(game: GamestateHelper, player, interaction: discord.Interaction):
        view = View()
        drawing = DrawHelper(game.gamestate) 
        money = player["money"] + int(player["science"]/player["trade_value"]) + int(player["materials"]/player["trade_value"])
        if player["colony_ships"] > 0 and game.get_short_faction_name(player["name"]) == "magellan":
            money +=player["colony_ships"]
        for minor in game.gamestate["minor_species"]:
            buttonID = f"FCID{player['color']}_formMinorRelations_"+minor
            cost = DiplomaticRelationsButtons.getMinorSpeciesCost(minor)
            label = minor + " ("+str(cost)+")"
            if cost <= money:
                view.add_item(Button(label=label, style=discord.ButtonStyle.blurple, custom_id=buttonID))
        await interaction.channel.send( f"{player['player_name']}, choose which minor species you would like to recruit", view=view, file = drawing.show_minor_species())

    @staticmethod
    async def formMinorRelations(game: GamestateHelper, player, interaction: discord.Interaction, buttonID:str, player_helper:PlayerHelper):
        await interaction.message.delete()
        minor = buttonID.split("_")[1]
        game.formMinorSpeciesRelations(player, minor)
        await interaction.channel.send(player["player_name"]+" formed relations with the minor species that gives the benefit of "+minor)
        cost = DiplomaticRelationsButtons.getMinorSpeciesCost(minor)
        paid = min(player["money"], cost)
        await interaction.channel.send(player_helper.adjust_money(-paid))
        if paid < cost:
            view = View()
            trade_value = player['trade_value']
            val = paid
            for resource_type, button_style in [("materials", discord.ButtonStyle.gray),   
                                        ("science", discord.ButtonStyle.blurple)]: 
                if(player[resource_type] >= trade_value):
                    val += int(player[resource_type]/trade_value)
                    view.add_item(Button(label=f"Pay {trade_value} {resource_type.capitalize()}",   
                                    style=button_style,   
                                    custom_id=f"FCID{player['color']}_payAtRatio_{resource_type}")) 
            if player["colony_ships"] > 0 and game.get_short_faction_name(player["name"]) == "magellan":
                emojiC = Emoji.getEmojiByName("colony_ship")
                view.add_item(Button(label=f"Get 1 Money", style=discord.ButtonStyle.red, emoji=emojiC, custom_id=f"FCID{player['color']}_magColShipForResource_money"))
            view.add_item(Button(label="Done Paying", style=discord.ButtonStyle.red, custom_id=f"FCID{player['color']}_deleteMsg"))  
            await interaction.channel.send(  
                f"Attempted to pay a cost of {str(cost)}\n Please pay the rest of the cost by trading other resources at your trade ratio ({trade_value}:1)",view=view  
            )  
        game.update_player(player_helper) 
        if "Cube" in minor:
            view = View()
            p = player
            if p["material_pop_cubes"] > 0:
                view.add_item(Button(label="Material", style=discord.ButtonStyle.gray, custom_id=f"FCID{p['color']}_reducePopFor_material"))
            if p["science_pop_cubes"] > 0:
                view.add_item(Button(label="Science", style=discord.ButtonStyle.gray, custom_id=f"FCID{p['color']}_reducePopFor_science"))
            if p["money_pop_cubes"] > 0:
                view.add_item(Button(label="Money", style=discord.ButtonStyle.gray, custom_id=f"FCID{p['color']}_reducePopFor_money"))
            await interaction.channel.send( f"{p['player_name']} choose what type of cube to put on the ambassador", view=view)
    @staticmethod
    async def startDiplomaticRelations(game: GamestateHelper, player, interaction: discord.Interaction):
        view = View()
        for p2 in DiplomaticRelationsButtons.getPlayersWithWhichDiplomatcRelationsCanBeFormed(game, player):
            buttonID = f"FCID{player['color']}_offerRelationsTo_"+game.get_gamestate()["players"][p2]["color"]
            label = f"{game.get_gamestate()['players'][p2]['name']}"
            view.add_item(Button(label=label, style=discord.ButtonStyle.blurple, custom_id=buttonID))
        await interaction.channel.send( f"{player['player_name']}, choose which player you would like to offer diplomatic relations to", view=view)
    @staticmethod
    def getPlayersWithWhichDiplomatcRelationsCanBeFormed(game: GamestateHelper, player):
        from Buttons.Influence import InfluenceButtons
        players = []
        configs = Properties()
        if "5playerhyperlane" in game.gamestate and game.gamestate["5playerhyperlane"]:
            with open("data/tileAdjacencies_5p.properties", "rb") as f:
                configs.load(f)
        else:
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
        await interaction.channel.send( f"{game.get_gamestate()['players'][pID]['player_name']} your relations have been refused by {player['player_name']}")
        await interaction.message.delete()

    @staticmethod
    async def acceptRelationsWith(game: GamestateHelper, player, interaction: discord.Interaction, buttonID:str):
        p2 = buttonID.split("_")[1]
        pID = game.get_player_from_color(p2)
        await interaction.followup.send( f"{game.get_gamestate()['players'][pID]['player_name']} your relations have been accepted by {player['player_name']}")
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
    
   




