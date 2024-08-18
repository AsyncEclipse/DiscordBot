import discord
from discord.ui import View
from Buttons.Explore import ExploreButtons
from Buttons.Population import PopulationButtons
from Buttons.Turn import TurnButtons
from helpers.GamestateHelper import GamestateHelper
from helpers.PlayerHelper import PlayerHelper
from discord.ui import View, Button
from jproperties import Properties

class InfluenceButtons:

    @staticmethod  
    def areTwoTilesAdjacent(game: GamestateHelper, tile1, tile2, configs):  

        def is_adjacent(tile_a, tile_b):  
            for index, adjTile in enumerate(configs.get(tile_a)[0].split(",")):  
                tile_orientation_index = (index + 6 + int(int(game.get_gamestate()["board"][tile_a]["orientation"]) / 60)) % 6  
                if adjTile == tile_b and "wormholes" in game.get_gamestate()["board"][tile_a] and tile_orientation_index in game.get_gamestate()["board"][tile_a]["wormholes"]:   
                    return True  
            return False  
        
        return is_adjacent(tile1, tile2) and is_adjacent(tile2, tile1)  

    @staticmethod  
    def getTilesToInfluence(game: GamestateHelper, player):  
        configs = Properties()  
        with open("data/tileAdjacencies.properties", "rb") as f:  
            configs.load(f)  
        tilesViewed = []
        tilesToInfluence = []
        playerTiles = ExploreButtons.getListOfTilesPlayerIsIn(game, player)  
        for tile in playerTiles:  
            for adjTile in configs.get(tile)[0].split(","):  
                if adjTile not in tilesViewed and InfluenceButtons.areTwoTilesAdjacent(game, tile, adjTile, configs):
                    tilesViewed.append(adjTile)
                    if "owner" in game.get_gamestate()["board"][adjTile] and game.get_gamestate()["board"][adjTile]["owner"]==0:
                        tilesToInfluence.append(adjTile)
            if tile not in tilesViewed:
                    tilesViewed.append(tile)
                    if "owner" in game.get_gamestate()["board"][tile] and game.get_gamestate()["board"][tile]["owner"]==0:
                        tilesToInfluence.append(tile)
        return tilesToInfluence
    @staticmethod  
    async def startInfluence(game: GamestateHelper, p1, interaction: discord.Interaction):  
        view = View()
        view.add_item(Button(label=f"Remove Influence", style=discord.ButtonStyle.red, custom_id=f"FCID{p1["color"]}_removeInfluenceStart"))  
        if len(InfluenceButtons.getTilesToInfluence(game,p1)) > 0:
            view.add_item(Button(label=f"Add  Influence", style=discord.ButtonStyle.green, custom_id=f"FCID{p1["color"]}_addInfluenceStart"))  
        view.add_item(Button(label="Refresh 2 Colony Ships", style=discord.ButtonStyle.blurple, custom_id=f"FCID{p1["color"]}_refreshPopShips"))
        view.add_item(Button(label="Put Down Population", style=discord.ButtonStyle.gray, custom_id=f"FCID{p1["color"]}_startPopDrop"))
        view.add_item(Button(label="Conclude Influence Action", style=discord.ButtonStyle.red, custom_id=f"FCID{p1["color"]}_finishInfluenceAction"))
        view.add_item(Button(label="Restart Turn", style=discord.ButtonStyle.gray, custom_id=f"FCID{p1["color"]}_restartTurn")) 
        await interaction.message.delete()
        await interaction.response.send_message( f"{interaction.user.mention} you can remove up to two disks and influence up to 2 spaces. You can also refresh 2 colony ships or put down population at any time during this resolution", view=view)

    @staticmethod  
    async def addInfluenceStart(game: GamestateHelper, p1, interaction: discord.Interaction):  
        view = View()
        for tile in InfluenceButtons.getTilesToInfluence(game, p1):
            view.add_item(Button(label=tile, style=discord.ButtonStyle.blurple, custom_id=f"FCID{p1["color"]}_addInfluenceFinish_"+tile))  
        await interaction.response.send_message( f"{interaction.user.mention} choose the tile you would like to influence", view=view)
    @staticmethod  
    async def addInfluenceFinish(game: GamestateHelper, p1, interaction: discord.Interaction, buttonID:str):  
        tileLoc = buttonID.split("_")[1]
        game.add_control(p1["color"],tileLoc)  
        await interaction.response.send_message( f"{interaction.user.mention} acquired control of "+tileLoc)
        await interaction.message.delete()

    @staticmethod  
    async def refreshPopShips(game: GamestateHelper, player, interaction: discord.Interaction, buttonID:str):  
        numShips = game.refresh_two_colony_ships(game.get_player_from_color(player["color"]))
        view = View.from_message(interaction.message)
        for button in view.children:  
            if buttonID in button.custom_id:  
                view.remove_item(button)
        await interaction.response.send_message( f"{interaction.user.mention} now has "+str(numShips)+" colony ships available to use")
        await interaction.message.edit(view=view) 

    @staticmethod  
    async def finishInfluenceAction(game: GamestateHelper, player, interaction: discord.Interaction, player_helper:PlayerHelper):  
        player_helper.spend_influence_on_action("influence")
        game.update_player(player_helper)
        next_player = game.get_next_player(player)
        view = TurnButtons.getStartTurnButtons(game, game.get_player(next_player))
        await interaction.message.delete()
        await interaction.response.send_message(f"<@{next_player}> use these buttons to do your turn. ",view=view)
    
    @staticmethod  
    async def removeInfluenceStart(game: GamestateHelper, player, interaction: discord.Interaction):  
        view = View()
        for tile in game.get_owned_tiles(player):
            view.add_item(Button(label=tile, style=discord.ButtonStyle.blurple, custom_id=f"FCID{player["color"]}_removeInfluenceFinish_"+tile))  
        await interaction.response.send_message( f"{interaction.user.mention} choose the tile you would like to remove influence from", view=view)
    @staticmethod  
    async def removeInfluenceFinish(game: GamestateHelper, p1, interaction: discord.Interaction, buttonID:str):  
        tileLoc = buttonID.split("_")[1]
        game.remove_control(p1["color"],tileLoc)  
        await interaction.response.send_message( f"{interaction.user.mention} relinquished control of "+tileLoc)
        for pop in PopulationButtons.findFullPopulation(game, p1, tileLoc):
            game.remove_pop([pop+"_pop"],tileLoc,game.get_player_from_color(p1["color"]))
            if "neutral" in pop:
                view=View()
                planetTypes = ["money","science","material"]
                for planetT in planetTypes:
                    view.add_item(Button(label=planetT.capitalize(), style=discord.ButtonStyle.blurple, custom_id=f"FCID{p1["color"]}_addCubeToTrack_"+planetT))
                await interaction.channel.send( f"A neutral cube was removed, please tell the bot what track it came from", view=view)
            else:
                await interaction.channel.send( f"Removed 1 "+pop.replace("adv","")+" population")
        await interaction.message.delete()
    @staticmethod  
    async def addCubeToTrack(game: GamestateHelper, p1, interaction: discord.Interaction, buttonID:str):
        pop = buttonID.split("_")[1]
        game.remove_pop([pop+"_pop"],"dummy",game.get_player_from_color(p1["color"]))
        await interaction.response.send_message( f"Added 1 "+pop.replace("adv","")+" population back to the relevant track")
        await interaction.message.delete()