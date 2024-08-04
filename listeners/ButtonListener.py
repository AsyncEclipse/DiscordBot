import discord
from discord.ext import commands
from commands import tile_commands
from helpers.DrawHelper import DrawHelper
from helpers.GamestateHelper import GamestateHelper
from commands.setup_commands import SetupCommands
from discord.ui import View, Button
from jproperties import Properties
import json

class ButtonListener(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


    def doesPlayerHaveUnpinnedShips(self, player, playerShips):
        playerShips = 0
        opponentShips = 0
        if playerShips == 0:
            return False
        
        for ship in playerShips:
            if ship.contains(player["color"]):
                playerShips = playerShips +1
            else:
                opponentShips = opponentShips +1
        return playerShips > opponentShips         
    def getListOfTilesPlayerIsIn(self, game, player):
        tile_map = game.get_gamestate()["board"]
        tiles = []
        for tile in tile_map: 
            if ("owner" in tile_map[tile] and tile_map[tile]["owner"] == player["color"]) or ("player_ships" in tile_map[tile] and ButtonListener.doesPlayerHaveUnpinnedShips(self,player,tile_map[tile]["player_ships"])):
                tiles.append(tile)
        return tiles



    @commands.Cog.listener()
    async def on_interaction(self, interaction):
        if interaction.type == discord.InteractionType.component:
            if interaction.data["custom_id"].startswith("place_tile"):
                await interaction.response.defer(thinking=True)
                game = GamestateHelper(interaction.channel)
                msg = interaction.data["custom_id"].split("_")
                game.add_tile(msg[2], 0, msg[3])
                await interaction.followup.send(f"Tile added to position {msg[2]}")
                await interaction.message.delete()
            if interaction.data['custom_id'].startswith("discard_tile"):
                game = GamestateHelper(interaction.channel)
                msg = interaction.data["custom_id"].split("_")
                game.tile_discard(msg[2])
                await interaction.channel.send("Tile discarded")
                await interaction.message.delete()
            if interaction.data['custom_id'] == "showGame":  
                game = GamestateHelper(interaction.channel)
                await interaction.response.defer(thinking=True)
                drawing = DrawHelper(game.gamestate)
                await interaction.followup.send(file=drawing.show_game())
                view = View()
                button = Button(label="Show Game",style=discord.ButtonStyle.primary, custom_id="showGame")
                view.add_item(button)
                await interaction.channel.send(view=view)
            if interaction.data['custom_id'] == "startExplore":
                game = GamestateHelper(interaction.channel)
                player = game.get_player(interaction.user.id)  
                configs = Properties()  
                with open("data/tileAdjacencies.properties", "rb") as f:  
                    configs.load(f)  
                view = View()
                tilesViewed = []
                playerTiles = ButtonListener.getListOfTilesPlayerIsIn(self, game, player)  
                for tile in playerTiles:  
                    for index, adjTile in enumerate(configs.get(tile)[0].split(",")):  
                        tile_orientation_index = (index + 6 + int(game.get_gamestate()["board"][tile]["orientation"] / 60)) % 6  
                        if (  
                            adjTile not in tilesViewed and  
                            tile_orientation_index in game.get_gamestate()["board"][tile]["wormholes"] and  
                            "back" in game.get_gamestate()["board"][str(adjTile)]["sector"]  
                        ):  
                            view.add_item(Button(label=str(adjTile), style=discord.ButtonStyle.primary, custom_id="exploreTile_" + str(adjTile)))  
                await interaction.response.send_message(f"{interaction.user.mention} select the tile you would like to explore",view=view)
            if interaction.data['custom_id'].startswith("exploreTile_"):
                game = GamestateHelper(interaction.channel)
                msg = interaction.data["custom_id"].split("_")
                tile = game.tile_draw(msg[1])
                drawing = DrawHelper(game.gamestate)
                await interaction.response.defer(thinking=True)
                image = drawing.base_tile_image(tile)
                await interaction.followup.send(file=drawing.show_single_tile(image))
                view = View()
                button = Button(label="Place Tile",style=discord.ButtonStyle.success, custom_id=f"place_tile_{msg[1]}_{tile}")
                button2 = Button(label="Discard Tile",style=discord.ButtonStyle.danger, custom_id=f"discard_tile_{tile}")
                view.add_item(button)
                view.add_item(button2)
                await interaction.channel.send(view=view)
                await interaction.message.delete()
            if interaction.data['custom_id'] == "startResearch":
                game = GamestateHelper(interaction.channel)
                player = game.get_player(interaction.user.id)  
                
                view = View()
                techsAvailable = game.get_gamestate()["available_techs"]  
                with open("data/techs.json", "r") as f:
                    tech_data = json.load(f)
                def calculate_cost(tech_details):  
                    prevTech = 0  
                    if tech_details["track"] != "any":  
                        prevTech = len(player[tech_details["track"] + "_tech"])  
                    else:  
                        prevTech = max(len(player["nano_tech"]), len(player["grid_tech"]), len(player["military_tech"]))  
                    
                    discount = player["tech_track"][6-prevTech]  
                    return max(tech_details["base_cost"] - discount, tech_details["min_cost"])  

                tech_groups = {  
                    "nano": [],  
                    "grid": [],  
                    "military": [],  
                    "any": []  
                }  
                # Group techs by type and calculate their costs  
                for tech in techsAvailable:  
                    tech_details = tech_data.get(tech)  
                    if tech_details:  
                        cost = calculate_cost(tech_details)  
                        tech_type = tech_details["track"]  
                        tech_groups[tech_type].append((tech, tech_details["name"], cost))  
                displayedTechs = [] 
                for tech_type in tech_groups:  
                    sorted_techs = sorted(tech_groups[tech_type], key=lambda x: x[2])  # Sort by cost  
                    for tech, tech_name, cost in sorted_techs:  
                        buttonStyle = discord.ButtonStyle.danger  
                        if tech_type == "grid":  
                            buttonStyle = discord.ButtonStyle.success  
                        elif tech_type == "nano":  
                            buttonStyle = discord.ButtonStyle.primary  
                        elif tech_type == "any":  
                            buttonStyle = discord.ButtonStyle.secondary  
                        if(tech not in displayedTechs):
                            displayedTechs.append(tech)
                            view.add_item(Button(label=f"{tech_name} ({cost})", style=buttonStyle, custom_id=f"getTech_{tech}"))  
                await interaction.response.send_message(f"{interaction.user.mention}, select the tech you would like to acquire. The discounted cost is in parentheses.", view=view)  
