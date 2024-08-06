import discord
from discord.ext import commands
from commands import tile_commands
from helpers.DrawHelper import DrawHelper
from helpers.GamestateHelper import GamestateHelper
from commands.setup_commands import SetupCommands
from discord.ui import View, Button
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from jproperties import Properties
import json

from helpers.PlayerHelper import PlayerHelper

class ButtonListener(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @staticmethod  
    def getPlayerFromHSLocation(game, location):  
        tileID = game.get_gamestate()["board"][location]["sector"]  
        return next((player for player in game.get_gamestate()["players"] if str(game.get_gamestate()["players"][player]["home_planet"]) == tileID), None)  

    @staticmethod  
    def getLocationFromID(game, id):  
        return next((tile for tile in game.get_gamestate()["board"] if game.get_gamestate()["board"][tile]["sector"] == str(id)), None)
    @staticmethod
    def getNextPlayer(player, game):
        listHS = [201,203,205,207,209,211]
        playerHSID = player["home_planet"]
        tileLocation = int(ButtonListener.getLocationFromID(game, playerHSID))
        index = listHS.index(tileLocation)  
        if index is None:  
            return None 
        newList = listHS[index+1:] + listHS[:index] + [listHS[index]] 
        for number in newList:
            nextPlayer = ButtonListener.getPlayerFromHSLocation(game, str(number))
            if nextPlayer is not None and not game.get_gamestate()["players"].get(nextPlayer, {}).get("passed", False):  
                return game.get_gamestate()["players"][nextPlayer]
        return None

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


    def calculate_cost(self, tech_details, tech_type,player):
        prev_tech_count = (  
            len(player[f"{tech_type}_tech"]) if tech_type != "any"  
            else max(len(player["nano_tech"]), len(player["grid_tech"]), len(player["military_tech"]))  
        )  
        discount = player["tech_track"][6 - prev_tech_count]  
        return max(tech_details["base_cost"] + discount, tech_details["min_cost"])  

    async def handle_wild_tech_selection(self, view, tech_details, tech,player):
        for tech_type, button_style in [("grid", discord.ButtonStyle.success),   
                                        ("nano", discord.ButtonStyle.primary),   
                                        ("military", discord.ButtonStyle.danger)]:  
            cost = ButtonListener.calculate_cost(tech_details, tech_type,player)  
            view.add_item(Button(label=f"{tech_type.capitalize()} ({cost})",   
                                style=button_style,   
                                custom_id=f"getTech_{tech}_{tech_type}"))  
        return view

    async def handle_specific_tech_selection(self, interaction, game, player, tech_details, tech_type, tech):
        cost = ButtonListener.calculate_cost(tech_details, tech_type,player)  
        game.playerResearchTech(str(interaction.user.id), tech, tech_type)  
        player = game.get_player(interaction.user.id)  
        player_helper = PlayerHelper(interaction.user.id, player)  

        if player["science"] >= cost:  
            msg = player_helper.adjust_science(-cost)  
            game.update_player(player_helper)  
            await interaction.response.send_message(msg)  
        else:  
            paid = min(cost, player["science"])  
            msg = player_helper.adjust_science(-paid)  
            game.update_player(player_helper)  
            view = View()
            trade_value = player['trade_value']
            for resource_type, button_style in [("materials", discord.ButtonStyle.secondary),   
                                        ("money", discord.ButtonStyle.primary)]: 
                if(player[resource_type] >= trade_value):
                    view.add_item(Button(label=f"Pay {trade_value} {resource_type.capitalize()}",   
                                    style=button_style,   
                                    custom_id=f"payAtRatio_{resource_type}")) 
            view.add_item(Button(label="Done Paying", style=discord.ButtonStyle.danger, custom_id="deleteMsg"))  
            await interaction.response.send_message(  
                f"Attempted to pay a cost of {str(cost)}\n{msg}\n Please pay the rest of the cost by trading other resources at your trade ratio ({trade_value}:1)",view=view  
            )  

    @commands.Cog.listener()
    async def on_interaction(self, interaction):
        if interaction.type == discord.InteractionType.component:
            if interaction.data["custom_id"].startswith("place_tile"):
                await interaction.response.defer(thinking=True)
                game = GamestateHelper(interaction.channel)
                msg = interaction.data["custom_id"].split("_")
                game.add_tile(msg[2], int(msg[4]), msg[3])
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
            if interaction.data['custom_id'] == "passForRound":
                game = GamestateHelper(interaction.channel)
                player = game.get_player(interaction.user.id)  
                player_helper = PlayerHelper(interaction.user.id, player)  
                player_helper.passTurn()
                game.update_player(player_helper)
                nextPlayer = ButtonListener.getNextPlayer(player,game)
                if nextPlayer != None:
                    view = PlayerHelper.getStartTurnButtons(nextPlayer)
                    await interaction.response.send_message(nextPlayer["player_name"]+ " use buttons to do your turn",view=view)
                else:
                    await interaction.response.send_message("All players have passed")
                await interaction.message.delete()
            if interaction.data['custom_id'] == "endTurn":
                game = GamestateHelper(interaction.channel)
                player = game.get_player(interaction.user.id)  
                nextPlayer = ButtonListener.getNextPlayer(player,game)
                if nextPlayer != None:
                    view = PlayerHelper.getStartTurnButtons(nextPlayer)
                    await interaction.response.send_message(nextPlayer["player_name"]+ " use buttons to do your turn",view=view)
                else:
                    await interaction.response.send_message("All players have passed")
                await interaction.message.delete()
            if interaction.data['custom_id'] == "startExplore":
                game = GamestateHelper(interaction.channel)
                player = game.get_player(interaction.user.id)  
                player_helper = PlayerHelper(interaction.user.id, player)  
                player_helper.spend_influence_on_action("explore")
                game.update_player(player_helper)
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
                            tilesViewed.append(adjTile)
                            view.add_item(Button(label=str(adjTile), style=discord.ButtonStyle.primary, custom_id="exploreTile_" + str(adjTile)))  
                await interaction.response.send_message(f"{interaction.user.mention} select the tile you would like to explore",view=view)
                if player["explore_apt"] > 1:
                    view.add_item(Button(label="Decline 2nd Explore", style=discord.ButtonStyle.danger, custom_id="deleteMsg"))  
                    await interaction.channel.send(f"{interaction.user.mention} select the second tile you would like to explore.", view=view)
                view = View()
                view.add_item(Button(label="End Turn", style=discord.ButtonStyle.danger, custom_id="endTurn"))
                await interaction.channel.send(f"{interaction.user.mention} when you're finished resolving your action, you may end turn with this button.", view=view)
                await interaction.message.delete()
            if interaction.data['custom_id'].startswith("exploreTile_"):
                await interaction.response.defer(thinking=True)
                game = GamestateHelper(interaction.channel)
                drawing = DrawHelper(game.gamestate)
                view = View()
                player = game.get_player(interaction.user.id)
                msg = interaction.data["custom_id"].split("_")
                if len(msg) > 2:
                    tileID = msg[2]
                    game.tile_discard(msg[3])
                else:
                    tileID = game.tile_draw(msg[1])
                    if player["name"]=="Descendants of Draco":
                        tileID2 = game.tile_draw(msg[1])
                        image = drawing.base_tile_image(tileID)
                        image2 = drawing.base_tile_image(tileID2)
                        await interaction.followup.send("Option #1",file=drawing.show_single_tile(image))
                        await interaction.channel.send("Option #2",file=drawing.show_single_tile(image2))
                        view.add_item(Button(label="Option #1",style=discord.ButtonStyle.success, custom_id=f"exploreTile_{msg[1]}_{tileID}_{tileID2}"))
                        view.add_item(Button(label="Option #2",style=discord.ButtonStyle.success, custom_id=f"exploreTile_{msg[1]}_{tileID2}_{tileID}"))
                        await interaction.channel.send(f"{interaction.user.mention} select the tile you wish to resolve.",view=view)
                        await interaction.message.delete()
                        return

                image = drawing.base_tile_image(tileID)
                configs = Properties()  
                with open("data/tileAdjacencies.properties", "rb") as f:  
                    configs.load(f)  
                wormholeStringsViewed = []
                with open("data/sectors.json") as f:
                    tile_data = json.load(f)
                tile = tile_data[tileID]
                playerTiles = ButtonListener.getListOfTilesPlayerIsIn(self, game, player)  
                count = 1
                for x in range(6):
                    rotation = x * 60
                    wormholeString = ''.join(str((wormhole + x) % 6) for wormhole in tile["wormholes"])  
                    if wormholeString in wormholeStringsViewed: continue
                    wormholeStringsViewed.append(wormholeString)
                    rotationWorks = False
                    for index, adjTile in enumerate(configs.get(msg[1])[0].split(",")):  
                        tile_orientation_index = (index + 6 + x) % 6  
                        if adjTile in playerTiles and tile_orientation_index in tile["wormholes"]:
                            rotationWorks = True
                            break
                    if rotationWorks:
                        context = Image.new("RGBA", (345*3, 300*3), (255, 255, 255, 0))
                        image = drawing.base_tile_image_with_rotation(tileID,rotation,tile["wormholes"])
                        context.paste(image,(345, 300),mask=image)
                        coords = [(345, 0), (605, 150),(605, 450),(345, 600), (85, 450),(85, 150)]  
                        for index, adjTile in enumerate(configs.get(msg[1])[0].split(",")):
                            if adjTile in game.get_gamestate()["board"]:
                                adjTileImage = drawing.board_tile_image(adjTile)
                                context.paste(adjTileImage,coords[index],mask=adjTileImage)
                        font = ImageFont.truetype("arial.ttf", size=50)  
                        ImageDraw.Draw(context).text((10, 10), f"Option #{count}", (255, 255, 255), font=font,  
                                        stroke_width=2, stroke_fill=(0, 0, 0))
                        bytes = BytesIO()
                        context.save(bytes, format="PNG")
                        bytes.seek(0)
                        file = discord.File(bytes, filename="tile_image.png")
                        view.add_item(Button(label="Option #"+str(count),style=discord.ButtonStyle.success, custom_id=f"place_tile_{msg[1]}_{tileID}_{rotation}"))
                        count += 1
                        await interaction.channel.send(file=file)

                view.add_item(Button(label="Discard Tile",style=discord.ButtonStyle.danger, custom_id=f"discard_tile_{tileID}"))
                await interaction.followup.send(f"{interaction.user.mention} select the orientation you prefer or discard the tile.",view=view)
                await interaction.message.delete()
            if interaction.data['custom_id'] == "deleteMsg":
                await interaction.message.delete()
            if interaction.data['custom_id'] == "startResearch":
                game = GamestateHelper(interaction.channel)
                player = game.get_player(interaction.user.id)  
                player_helper = PlayerHelper(interaction.user.id, player)  
                player_helper.spend_influence_on_action("research")
                game.update_player(player_helper)
                player = game.get_player(interaction.user.id) 
                view = View()
                view2 = View()
                techsAvailable = game.get_gamestate()["available_techs"]  
                with open("data/techs.json", "r") as f:
                    tech_data = json.load(f)  

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
                        tech_type = tech_details["track"]  
                        cost = ButtonListener.calculate_cost(tech_details,tech_type,player)   
                        tech_groups[tech_type].append((tech, tech_details["name"], cost))  
                displayedTechs = [] 
                buttonCount = 1
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
                            if buttonCount < 26:
                                view.add_item(Button(label=f"{tech_name} ({cost})", style=buttonStyle, custom_id=f"getTech_{tech}_{tech_type}"))  
                            else:
                                view2.add_item(Button(label=f"{tech_name} ({cost})", style=buttonStyle, custom_id=f"getTech_{tech}_{tech_type}"))
                            buttonCount+=1
                await interaction.response.send_message(f"{interaction.user.mention}, select the tech you would like to acquire. The discounted cost is in parentheses.", view=view)
                if buttonCount > 26:
                    await interaction.channel.send(view=view2)
                if player["research_apt"] > 1:
                    view.add_item(Button(label="Decline 2nd Tech", style=discord.ButtonStyle.danger, custom_id="deleteMsg"))  
                    await interaction.channel.send(f"{interaction.user.mention}, select the second tech you would like to acquire. The discounted cost is in parentheses.", view=view)
                    if buttonCount > 26:
                        await interaction.channel.send(view=view2)
                view = View()
                view.add_item(Button(label="End Turn", style=discord.ButtonStyle.danger, custom_id="endTurn"))
                await interaction.channel.send(f"{interaction.user.mention} when you're finished resolving your action, you may end turn with this button.", view=view)
            if interaction.data['custom_id'].startswith("getTech_"):
                await interaction.message.delete()  
                game = GamestateHelper(interaction.channel)  
                buttonID = interaction.data["custom_id"].split("_")  
                tech = buttonID[1]  
                tech_type = buttonID[2]  
                view = View()   
                player = game.get_player(interaction.user.id) 
                with open("data/techs.json", "r") as f:  
                    tech_data = json.load(f)  
                tech_details = tech_data.get(tech)  
                if tech_type == "any":  
                    view = ButtonListener.handle_wild_tech_selection(view, tech_details, tech, player)  
                    await interaction.response.send_message(  
                        f"{interaction.user.mention}, select the row of tech you would like to place this wild tech in. The discounted cost is in parentheses.",   
                        view=view  
                    )  
                else:  
                    await ButtonListener.handle_specific_tech_selection(interaction, game, player, tech_details, tech_type,tech)
            if interaction.data['custom_id'].startswith("payAtRatio_"):
                game = GamestateHelper(interaction.channel)  
                buttonID = interaction.data["custom_id"].split("_")   
                resource_type = buttonID[1]  
                view = View()   
                player = game.get_player(interaction.user.id)
                trade_value = player["trade_value"]
                paid = min(trade_value, player[resource_type])  
                player_helper = PlayerHelper(interaction.user.id, player) 
                msg = player_helper.adjust_resource(resource_type,-paid)  
                game.update_player(player_helper)  
                view = View() 
                await interaction.response.send_message(msg)  

            if interaction.data["custom_id"] == "startBuild":
                game = GamestateHelper(interaction.channel)
                tiles = game.get_owned_tiles(interaction.user.id)
                tiles.sort()
                view = View()
                for tile in tiles:
                    view.add_item(Button(label=tile, style=discord.ButtonStyle.primary, custom_id=f"build_in_{tile}"))
                await interaction.response.send_message(f"{interaction.user.mention}, choose which tile you would like to build in.", view=view)
            if interaction.data["custom_id"].startswith("build_in_"):
                game = GamestateHelper(interaction.channel)
                p1 = game.get_player(interaction.user.id)
                msg = interaction.data["custom_id"].split("_")
                build_actions = p1["build_apt"]
                ship_list = []
                total_cost = 0
                view = View()
                view.add_item(Button(label=f"Interceptor ({p1["cost_interceptor"]})", style=discord.ButtonStyle.primary,
                                     custom_id=f"build_unit_int_{msg[2]}"))
                view.add_item(Button(label=f"Cruiser ({p1["cost_cruiser"]})", style=discord.ButtonStyle.primary,
                                     custom_id=f"build_unit_cru_{msg[2]}"))
                view.add_item(Button(label=f"Dreadnought ({p1["cost_dread"]})", style=discord.ButtonStyle.primary,
                                     custom_id=f"build_unit_drd_{msg[2]}"))
                if "stb" in p1["military_tech"]:
                    view.add_item(Button(label=f"Starbase ({p1["cost_starbase"]})", style=discord.ButtonStyle.success,
                                         custom_id=f"build_unit_sb_{msg[2]}"))
                if "orb" in p1["nano_tech"]:
                    view.add_item(Button(label=f"Orbital ({p1["cost_orbital"]})", style=discord.ButtonStyle.success,
                                         custom_id=f"build_unit_orb_{msg[2]}"))
                if "mon" in p1["nano_tech"]:
                    view.add_item(Button(label=f"Monolith ({p1["cost_monolith"]})", style=discord.ButtonStyle.success,
                                         custom_id=f"build_unit_mon_{msg[2]}"))
                view.add_item(Button(label="Done", style=discord.ButtonStyle.danger,
                                     custom_id=f"build_finished_{msg[2]}"))
                await interaction.response.send_message(f"{interaction.user.mention}, you have {p1["materials"]} materials to spend"
                                                        f" on up to {p1["build_apt"]} objects in this system.", view=view)
                