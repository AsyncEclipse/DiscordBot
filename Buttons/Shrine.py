import asyncio
import json
import discord
from discord.ui import View
from Buttons.DiscoveryTile import DiscoveryTileButtons
from helpers.DrawHelper import DrawHelper
from helpers.EmojiHelper import Emoji
from helpers.GamestateHelper import GamestateHelper
from helpers.PlayerHelper import PlayerHelper
from discord.ui import View, Button

class ShrineButtons:

    @staticmethod  
    def getInitialShrineButtons(game: GamestateHelper, player):
        shrinePlanets = ShrineButtons.getShrinePlanets(game, player)
        view = View()
        for shrinePlan in shrinePlanets:
            type = shrinePlan.split("_")[0]
            tile = shrinePlan.split("_")[1]
            for count,shrineType in enumerate(player["shrine_type"]):
                if (type == shrineType or type == "neutral") and player["shrine_in_storage"][count] == 1 and player["shrine_cost"][count] <= ShrineButtons.getResourceAvailable(type,player, game):
                    view.add_item(Button(label=f"{type.capitalize()} (Tile {tile})", emoji=Emoji.getEmojiByName(type), style=discord.ButtonStyle.gray, custom_id=f"FCID{player['color']}_placeShrineInitial_{type}_{tile}"))
                    break 
        view.add_item(Button(label=f"Decline Placement", style=discord.ButtonStyle.red, custom_id=f"FCID{player['color']}_deleteMsg"))
        return view

    @staticmethod  
    def getResourceAvailable(resource:str, player, game:GamestateHelper):
        extra = 0
        matAval = player["materials"] + int(player["money"]/player["trade_value"]) + int(player["science"]/player["trade_value"])+extra
        moneyAval = player["money"] + int(player["science"]/player["trade_value"]) + int(player["materials"]/player["trade_value"])+extra
        scienceAval = player["science"] + int(player["money"]/player["trade_value"]) + int(player["materials"]/player["trade_value"])+extra
        if player["colony_ships"] > 0 and game.get_short_faction_name(player["name"]) == "magellan":
            extra +=player["colony_ships"]
        if resource == "material":
            return matAval
        elif resource == "science":
            return scienceAval
        elif resource == "money":
            return  moneyAval
        else:
            val = max(matAval,moneyAval)
            return max(scienceAval,val)

    @staticmethod  
    def getShrinePlanets(game: GamestateHelper, player):
        tiles = game.get_owned_tiles(player)
        tiles.sort()
        shrinePlanets = []
        for tile in tiles:
            tileState = game.get_gamestate()["board"][tile]
            planetTypes = ["money","science","material","neutral","moneyadv","scienceadv","materialadv","neutraladv"]
            for planetT in planetTypes:
                type = planetT.replace("adv","")
                if f"{planetT}_pop" in tileState and tileState[f"{planetT}_pop"] != [] and type+"_shrine" not in tileState and type+"_"+tile not in shrinePlanets:
                    shrinePlanets.append(type+"_"+tile)
        return shrinePlanets
    @staticmethod  
    async def placeShrineInitial(game:GamestateHelper, player, interaction:discord.Interaction, customID:str):
        type = customID.split("_")[1]
        tile = customID.split("_")[2]
        view = View()
        drawing = DrawHelper(game.gamestate)
        for count,shrineType in enumerate(player["shrine_type"]):
            if (type == shrineType or type == "neutral") and player["shrine_in_storage"][count] == 1 and player["shrine_cost"][count] <= ShrineButtons.getResourceAvailable(type,player, game):
                view.add_item(Button(label=f"{shrineType.capitalize()} (Cost {str(player["shrine_cost"][count])})", style=discord.ButtonStyle.gray, emoji=Emoji.getEmojiByName(type), custom_id=f"FCID{player['color']}_placeShrineFinal_{type}_{tile}_{str(count)}"))
        await interaction.channel.send("Please select the shrine type and cost you would like to pay",view=view, file=drawing.show_shrine_board(player))
        await interaction.message.delete()
    
    @staticmethod  
    async def placeShrineFinal(game:GamestateHelper, player, interaction:discord.Interaction, customID:str, player_helper:PlayerHelper):
        planetType = customID.split("_")[1]
        tile = customID.split("_")[2]
        count = int(customID.split("_")[3])
        shrineType = player["shrine_type"][count]
        resourceType = shrineType.replace("material","materials")
        shrineCost = player["shrine_cost"][count]
        player_helper.stats["shrine_in_storage"][count]=0
        game.addShrine(tile, planetType)
        output = player_helper.adjust_resource(resourceType, min(shrineCost, player[resourceType]))
        game.update_player(player_helper)
        await interaction.channel.send(player["player_name"]+" placed a "+resourceType+" shrine in tile "+tile+" on a "+planetType+" planet "+output)
        if shrineCost > player[resourceType]:
            view = View()
            trade_value = player['trade_value']
            for resource_type, button_style in [("materials", discord.ButtonStyle.gray),   
                                        ("money", discord.ButtonStyle.green), ("science", discord.ButtonStyle.blurple)]: 
                if(player[resource_type] >= trade_value):
                    view.add_item(Button(label=f"Pay {trade_value} {resource_type.capitalize()}",   
                                    style=button_style,   
                                    custom_id=f"FCID{player['color']}_payAtRatio_{resource_type}")) 
            if player["colony_ships"] > 0 and game.get_short_faction_name(player["name"]) == "magellan":
                emojiC = Emoji.getEmojiByName("colony_ship")
                view.add_item(Button(label=f"Get 1 {resourceType}", style=discord.ButtonStyle.red, emoji=emojiC, custom_id=f"FCID{player['color']}_magColShipForResource_{resourceType}"))
            view.add_item(Button(label="Done Paying", style=discord.ButtonStyle.red, custom_id=f"FCID{player['color']}_deleteMsg"))  
            await interaction.channel.send(  
                f"Attempted to pay a cost of {str(shrineCost)}\n Please pay the rest of the cost by trading other resources at your trade ratio ({trade_value}:1)"  
            )  
            await interaction.channel.send("Payment buttons",view=view)
        nums = [0,1,2]
        if count == nums[0] or count == nums[1] or count == nums[2]:
            if player_helper.stats["shrine_in_storage"][nums[0]] == 0 and player_helper.stats["shrine_in_storage"][nums[1]] == 0 and player_helper.stats["shrine_in_storage"][nums[2]] == 0:
                await interaction.channel.send(player["player_name"]+" placed the third shrine from a row on their shrine board and gains the wormhole generator ability")
        nums = [3,4,5]
        if count == nums[0] or count == nums[1] or count == nums[2]:
            if player_helper.stats["shrine_in_storage"][nums[0]] == 0 and player_helper.stats["shrine_in_storage"][nums[1]] == 0 and player_helper.stats["shrine_in_storage"][nums[2]] == 0:
                await interaction.channel.send(player["player_name"]+" placed the third shrine from a row on their shrine board and gains a discovery tile")
                game.addDiscTile(game.getLocationFromID(player["home_planet"]))
                await DiscoveryTileButtons.exploreDiscoveryTile(game, game.getLocationFromID(player["home_planet"]),interaction,player)
        nums = [6,7,8]
        if count == nums[0] or count == nums[1] or count == nums[2]:
            if player_helper.stats["shrine_in_storage"][nums[0]] == 0 and player_helper.stats["shrine_in_storage"][nums[1]] == 0 and player_helper.stats["shrine_in_storage"][nums[2]] == 0:
                await interaction.channel.send(player["player_name"]+" placed the third shrine from a row on their shrine board and gained an influence disc")
                player_helper.stats["influence_discs"] +=1
                game.update_player(player_helper)
        
        await interaction.message.delete()