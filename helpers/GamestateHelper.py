import asyncio
import json

import discord
import config
from helpers.DrawHelper import DrawHelper
from helpers.PlayerHelper import PlayerHelper
import os
from jproperties import Properties
import random
from discord.ui import View, Button
import concurrent.futures

class GamestateHelper:
    def __init__(self, game_id :discord.TextChannel= None, nameID:str =None):
        if game_id is not None:
            nameID = game_id.name
        if "-" in nameID:
            game_id = nameID.split("-")[0]
        else:
            game_id = nameID
        self.game_id = game_id
        self.gamestate = self.get_gamestate()
    

    def getPlayersID(self, player):
        return player["player_name"].replace(">@","").replace(">","")
    def setRound(self, round:int):
         self.gamestate["roundNum"] = round
         self.update()

    async def endGame(self, interaction:discord.Interaction):
        guild = interaction.guild
        category = interaction.channel.category
        role = discord.utils.get(guild.roles, name=self.game_id)  
        for channel in guild.channels:  
            if isinstance(channel, discord.TextChannel) and self.game_id in channel.name:  
                await channel.delete()    
        if len(category.channels) < 1:
            await category.delete()
        chronicles_channel = discord.utils.get(guild.channels, name='game-chronicles')  
        if chronicles_channel and isinstance(chronicles_channel, discord.TextChannel):  
            message_to_send = self.game_id+ ' has concluded!'  
            message = await chronicles_channel.send(message_to_send)  
            thread = await message.create_thread(name=self.game_id) 
            drawing = DrawHelper(self.gamestate)
            await thread.send(file=drawing.show_map())
            await thread.send(file=drawing.show_stats())
            await thread.send(role.mention + " final state here")
        if role:  
            await role.delete()  
        if os.path.exists(f"{config.gamestate_path}/{self.game_id}_saveFile.json"):   
            os.remove(f"{self.game_id}_saveFile.json")


    def getLocationFromID(self, id):
        return next((tile for tile in self.gamestate["board"] if self.gamestate["board"][tile]["sector"] == str(id)), None)

    def get_gamestate(self):
        with open(f"{config.gamestate_path}/{self.game_id}.json", "r") as f:
            gamestate = json.load(f)
        return gamestate
    
    def get_saveFile(self):
        if not os.path.exists(f"{config.gamestate_path}/{self.game_id}_saveFile.json"):  
            data = {  
                "oldestSaveNum": 0,  
                "newestSaveNum": 0  
            }
            with open(f"{config.gamestate_path}/{self.game_id}_saveFile.json", 'w') as json_file:  
                json.dump(data, json_file, indent=4)  
        with open(f"{config.gamestate_path}/{self.game_id}_saveFile.json", "r") as f:
            saveFile = json.load(f)
        return saveFile

    def addPlayers(self, list):
        for i in list:
            if i[0] not in self.gamestate["players"]:
                self.gamestate["players"].update({i[0]: {"player_name": f"<@{str(i[0])}>"}})
        self.update()

    def tile_draw(self, ring):
        ring = int(int(ring)/100)
        if ring <= 3:
            random.shuffle(self.gamestate[f"tile_deck_{ring}00"])
            tile = self.gamestate[f"tile_deck_{ring}00"].pop(0)
            self.update()
            return tile
        else:
            random.shuffle(self.gamestate[f"tile_deck_300"])
            tile = self.gamestate[f"tile_deck_300"].pop(0)
            self.update()
            return tile

    def tile_discard(self, sector):
        self.gamestate["tile_discard"].append(sector)
        self.update()

    @staticmethod
    def getShipFullName(shipAbbreviation):
        if shipAbbreviation == "int":
            return "interceptor"
        elif shipAbbreviation == "cru":
            return "cruiser"
        elif shipAbbreviation == "drd":
            return "dreadnought"
        elif shipAbbreviation == "sb":
            return "starbase"
    @staticmethod
    def getShipShortName(shipName:str):
        shipName = shipName.lower()
        if shipName == "interceptor":
            return "int"
        elif shipName == "cruiser":
            return "cru"
        elif shipName == "dreadnought":
            return "drd"
        elif shipName == "starbase":
            return "sb"
        elif shipName == "orbital":
            return "orb"
        elif shipName == "monolith":
            return "mon"
        else:
            return shipName

    def getShortFactionNameFromFull(self, fullName):
        if fullName == "Descendants of Draco":
            return "draco"
        elif fullName == "Mechanema":
            return "mechanema"
        elif fullName == "Planta":
            return "planta"
        elif fullName == "Orian Hegemony" or fullName == "Orion Hegemony":
            return "orion"
        elif fullName == "Hydran Progress":
            return "hydran"
        elif fullName == "Eridani Empire":
            return "eridani"
        elif "Terran" in fullName:
            return fullName.lower().replace(" ","_")


    def rotate_tile(self, position, orientation):
        tile = self.gamestate["board"][position]
        tile.update({"orientation": (tile["orientation"]+orientation) % 360})
        self.gamestate["board"][position] = tile
        self.update()
    def add_tile(self, position, orientation, sector, owner=None):

        with open("data/sectors.json") as f:
            tile_data = json.load(f)
        try:
            tile = tile_data[sector]
            if owner != None:
                tile["owner"] = owner
                self.gamestate["players"][self.get_player_from_color(owner)]["owned_tiles"].append(position)

            if tile["ancient"] or tile["guardian"] or tile["gcds"]:
                adv = ""
                if self.gamestate["advanced_ai"]:
                    adv = "adv"
                anc, grd, gcds = tile["ancient"],tile["guardian"], tile["gcds"]
                if anc:
                    tile["player_ships"].append("ai-anc"+adv)
                    if tile["ancient"] > 1:
                        tile["player_ships"].append("ai-anc"+adv)
                if grd:
                    tile["player_ships"].append("ai-grd" + adv)
                if gcds:
                    tile["player_ships"].append("ai-gcds" + adv)
            tile.update({"sector": sector})
            tile.update({"orientation": orientation})
        except KeyError:
            tile = {"sector": sector, "orientation": orientation}
        self.gamestate["board"][position] = tile

        configs = Properties()
        with open("data/tileAdjacencies.properties", "rb") as f:
            configs.load(f)
        if position != None and sector != "sector3back":
            tiles = configs.get(position)[0].split(",")
            for adjTile in tiles:
                if adjTile not in self.gamestate["board"]:
                    self.add_tile(adjTile, 0, "sector3back")
        self.update()

    def add_control(self, color, position):
        self.gamestate["board"][position]["owner"] = color
        if position not in self.gamestate["players"][self.get_player_from_color(color)]["owned_tiles"]:
            self.gamestate["players"][self.get_player_from_color(color)]["owned_tiles"].append(position)
        amount = max(0, self.gamestate["players"][self.get_player_from_color(color)]["influence_discs"] - 1)
        self.gamestate["players"][self.get_player_from_color(color)]["influence_discs"] = amount
        self.update()

    def remove_control(self, color, position):
        self.gamestate["board"][position]["owner"] = 0
        self.gamestate["players"][self.get_player_from_color(color)]["owned_tiles"].remove(position)
        amount = min(15, self.gamestate["players"][self.get_player_from_color(color)]["influence_discs"] + 1)
        self.gamestate["players"][self.get_player_from_color(color)]["influence_discs"] = amount
        self.update()

    def add_warp(self, position):
        self.gamestate["board"][position]["warp"]=1
        self.update()

    def updateNamesAndOutRimTiles(self, interaction:discord.Interaction):
        for player in self.gamestate["players"]:
            if "username" not in self.gamestate["players"][player]:
                self.gamestate["players"][player]["username"] = interaction.guild.get_member(int(player)).display_name
        if len(self.gamestate[f"tile_deck_300"]) == 0:
            keysToRemove = []
            for key,value in self.gamestate[f"board"].items():
                if value["sector"] == "sector3back":
                    keysToRemove.append(key)
            for key in keysToRemove:
                del self.gamestate[f"board"][key]

        self.update()
    def add_units(self, unit_list, position):
        color = unit_list[0].split("-")[0]
        player = self.get_player_from_color(color)
        for i in unit_list:
            if "int" in i:
                self.gamestate["players"][player]["ship_stock"][0] -= 1
            if "cru" in i:
                self.gamestate["players"][player]["ship_stock"][1] -= 1
            if "drd" in i:
                self.gamestate["players"][player]["ship_stock"][2] -= 1
            if "sb" in i:
                self.gamestate["players"][player]["ship_stock"][3] -= 1
            self.gamestate["board"][position]["player_ships"].append(i)
        self.update()
    def displayPlayerStats(self, player):
        money = player["money"]
        moneyIncrease = "+"+str(player["population_track"][player["money_pop_cubes"]-1]) 
        moneyIncrease2 = "Error"
        if player["money_pop_cubes"]-2 > -1:
            moneyIncrease2 = "+"+str(player["population_track"][player["money_pop_cubes"]-2])
        moneyDecrease = str(player["influence_track"][player["influence_discs"]])
        moneyDecrease2 = "Error"
        if player["influence_discs"]-1 > -1:
            moneyDecrease2 = str(player["influence_track"][player["influence_discs"]-1])
        science = player["science"]
        scienceIncrease = player["population_track"][player["science_pop_cubes"]-1]
        scienceIncrease = "+"+str(scienceIncrease)
        materials = player["materials"]
        materialsIncrease = player["population_track"][player["material_pop_cubes"]-1]
        materialsIncrease = "+"+str(materialsIncrease)
        msg = f"\nYour current economic situation is as follows:\nMoney: {money} ({moneyIncrease} - {moneyDecrease})\nScience: {science} ({scienceIncrease})\nMaterials: {materials} ({materialsIncrease})\nIf you spend another disk, your maintenance cost will go from -{moneyDecrease} to -{moneyDecrease2}. If you drop another money cube, your income will go from {moneyIncrease} to {moneyIncrease2}"
        return msg
            
        
            
    def add_pop_specific(self, originalType:str, type:str, number:int, position:str, playerID):
        if "orbital" not in originalType:
            if self.gamestate["players"][playerID]["colony_ships"] > 0:
                self.gamestate["players"][playerID]["colony_ships"] = self.gamestate["players"][playerID]["colony_ships"]-1
            else:
                return False
        if  f"{originalType}_pop" in self.gamestate["board"][position]:
            self.gamestate["board"][position][f"{originalType}_pop"][number] = self.gamestate["board"][position][f"{originalType}_pop"][number]+1
        else:
            self.gamestate["board"][position][f"{originalType}_pop"] = [1]
        self.gamestate["players"][playerID][type.replace("adv","")+"_pop_cubes"] = self.gamestate["players"][playerID][type.replace("adv","")+"_pop_cubes"]-1
        self.update()
        return True

    def refresh_two_colony_ships(self,  playerID):
        #"base_colony_ships"
        minNum = min(self.gamestate["players"][playerID]["colony_ships"]+2, self.gamestate["players"][playerID]["base_colony_ships"])
        self.gamestate["players"][playerID]["colony_ships"] = minNum
        self.update()
        return minNum

    def add_pop(self, pop_list, position, playerID):
        neutralPop = 0
        for i in pop_list:
            length = len(self.gamestate["board"][position][i])
            if self.gamestate["board"][position][i][0]+1 <= length:
                self.gamestate["board"][position][i][0] = self.gamestate["board"][position][i][0]+1
            if "neutral" not in i and "orbital" not in i:    
                self.gamestate["players"][playerID][i.replace("adv","")+"_cubes"] = self.gamestate["players"][playerID][i.replace("adv","")+"_cubes"]-1
            else: 
                neutralPop += 1
        self.update()
        return neutralPop
    def remove_pop(self, pop_list, position, playerID):
        neutralPop = 0
        for i in pop_list:
            if position != "dummy":
                for val,num in enumerate(self.gamestate["board"][position][i]):
                    if(num > 0):
                        self.gamestate["board"][position][i][val] = num-1
                        break
            if "neutral" not in i and "orbital" not in i:
                self.gamestate["players"][playerID][i.replace("adv","")+"_cubes"] = self.gamestate["players"][playerID][i.replace("adv","")+"_cubes"]+1
            else:
                neutralPop += 1

        self.update()
        return neutralPop

    def remove_units(self, unit_list, position):
        color = unit_list[0].split("-")[0]
        player = self.get_player_from_color(color)
        for i in unit_list:
            if i in self.gamestate["board"][position]["player_ships"]:
                if "int" in i:
                    self.gamestate["players"][player]["ship_stock"][0] += 1
                if "cru" in i:
                    self.gamestate["players"][player]["ship_stock"][1] += 1
                if "drd" in i:
                    self.gamestate["players"][player]["ship_stock"][2] += 1
                if "sb" in i:
                    self.gamestate["players"][player]["ship_stock"][3] += 1
                self.gamestate["board"][position]["player_ships"].remove(i)
        self.update()

    def upkeep(self):
        for player in self.gamestate["players"]:
            p1 = PlayerHelper(player, self.get_player(player))
            p1.upkeep()
        tech_draws = self.gamestate["player_count"]+3
        while tech_draws > 0:
            random.shuffle(self.gamestate["tech_deck"])
            picked_tech = self.gamestate["tech_deck"].pop(0)
            if picked_tech == "clo":
                picked_tech ="cld"
            self.gamestate["available_techs"].append(picked_tech)
            with open("data/techs.json", "r") as f:
                tech_data = json.load(f)
            if tech_data[picked_tech]["track"] == "any":
                pass
            else:
                tech_draws -= 1
        if "roundNum" in self.gamestate:
            self.gamestate["roundNum"] += 1
        else:
            self.gamestate["roundNum"] = 2
        self.update()

    def player_setup(self, player_id, faction, color):
        if self.gamestate["setup_finished"] == 1:
            return ("The game has already been setup!")

        with open("data/factions.json", "r") as f:
            faction_data = json.load(f)

        self.gamestate["players"][str(player_id)].update({"color": color})
        self.gamestate["players"][str(player_id)].update(faction_data[faction])
        self.gamestate["players"][str(player_id)].update({"passed": False})
        self.gamestate["players"][str(player_id)].update({"perma_passed": False})
        self.update()
        #return(f"{name} is now setup!")

    def setup_finished(self):

        for i in self.gamestate["players"]:
            if len(self.gamestate["players"][i]) < 3:
                return(f"{self.gamestate['players'][i]['player_name']} still needs to be setup!")
            else:
                p1 = PlayerHelper(i, self.get_player(i))
                home = self.get_system_coord(p1.stats["home_planet"])
                if p1.stats["name"] == "Orion Hegemony":
                    self.gamestate["board"][home]["player_ships"].append(p1.stats["color"]+"-cru")
                else:
                    self.gamestate["board"][home]["player_ships"].append(p1.stats["color"] + "-int")

                if p1.stats["name"] == "Eridani Empire":
                    random.shuffle(self.gamestate["reputation_tiles"])
                    p1.stats["reputation_track"][0] = self.gamestate["reputation_tiles"].pop(0)
                    p1.stats["reputation_track"][1] = self.gamestate["reputation_tiles"].pop(0)
                    self.update_player(p1)

        self.gamestate["setup_finished"] = 1
        self.update()
    
    def setup_techs_and_outer_rim(self, count:int):
        self.gamestate["player_count"] = count
        draw_count = {2: [5, 12], 3: [8, 14], 4: [14, 16], 5: [16, 18], 6: [18, 20]}

        third_sector_tiles = ["301", "302", "303", "304", "305", "306", "307", "308", "309", "310", "311", "312", "313", "314",
                              "315", "316", "317","318", "381", "382"]
        sector_draws = draw_count[self.gamestate["player_count"]][0]
        tech_draws = draw_count[self.gamestate["player_count"]][1]

        with open("data/techs.json", "r") as f:
            tech_data = json.load(f)

        while sector_draws > 0:
            random.shuffle(third_sector_tiles)
            self.gamestate["tile_deck_300"].append(third_sector_tiles.pop(0))
            sector_draws -= 1

        while tech_draws > 0:
            random.shuffle(self.gamestate["tech_deck"])
            picked_tech = self.gamestate["tech_deck"].pop(0)
            if picked_tech == "clo":
                picked_tech ="cld"
            self.gamestate["available_techs"].append(picked_tech)

            if tech_data[picked_tech]["track"] == "any":
                pass
            else:
                tech_draws -= 1
        self.update()



    def playerResearchTech(self, playerid, tech, type):
        self.gamestate["available_techs"].remove(tech)
        self.gamestate["players"][playerid][type+"_tech"].append(tech)
        with open("data/techs.json", "r") as f:
            tech_data = json.load(f)
        tech_details = tech_data.get(tech)
        self.gamestate["players"][playerid]["influence_discs"] += tech_details["infdisc"]
        if tech_details["activ1"] != 0:
            self.gamestate["players"][playerid][f"{tech_details['activ1']}_apt"] += 1
            if tech_details["activ1"] == "upgrade":
                self.gamestate["players"][playerid][f"{tech_details['activ1']}_apt"] += 1
        self.update()
    
    def playerReturnTech(self, playerid, tech, type):
        self.gamestate["available_techs"].append(tech)
        self.gamestate["players"][playerid][type+"_tech"].remove(tech)
        with open("data/techs.json", "r") as f:
            tech_data = json.load(f)
        tech_details = tech_data.get(tech)
        self.gamestate["players"][playerid]["influence_discs"] -= tech_details["infdisc"]
        if tech_details["activ1"] != 0:
            self.gamestate["players"][playerid][f"{tech_details['activ1']}_apt"] -= 1
            if tech_details["activ1"] == "upgrade":
                self.gamestate["players"][playerid][f"{tech_details['activ1']}_apt"] -= 1
        self.update()
    def update(self):
        with open(f"{config.gamestate_path}/{self.game_id}.json", "w") as f:
            json.dump(self.gamestate, f)

    def getNumberOfSaveFiles(self):
        saveFile = self.get_saveFile()
        newSaveNum = saveFile["newestSaveNum"]
        oldSaveNum = saveFile["oldestSaveNum"]
        return newSaveNum - oldSaveNum + 1

    def backUpToLastSaveFile(self):
        saveFile = self.get_saveFile()
        newSaveNum = str(saveFile["newestSaveNum"])
        if newSaveNum in saveFile:
            newestSave = saveFile[newSaveNum]
            self.gamestate = newestSave
            saveFile["newestSaveNum"] = saveFile["newestSaveNum"]-1
            self.update()
            del saveFile[newSaveNum]
            with open(f"{config.gamestate_path}/{self.game_id}_saveFile.json", "w") as f:
                json.dump(saveFile, f)
            return True
        else:
            return False

    def updateSaveFile(self):
        saveFile = self.get_saveFile()
        with open(f"{config.gamestate_path}/{self.game_id}_saveFile.json", "w") as f:
            if saveFile["newestSaveNum"] > saveFile["oldestSaveNum"] + 3:
                if str(saveFile["oldestSaveNum"]) in saveFile:
                    del saveFile[str(saveFile["oldestSaveNum"])]
                saveFile["oldestSaveNum"] = saveFile["oldestSaveNum"]+1

            saveFile[str(saveFile["newestSaveNum"]+1)] = self.gamestate
            saveFile["newestSaveNum"] = saveFile["newestSaveNum"]+1
            json.dump(saveFile, f)

    def get_player(self, player_id):
        if str(player_id) not in self.gamestate["players"]:
            return None
        return self.gamestate["players"][str(player_id)]

    def get_player_from_color(self, color):
        for i in self.gamestate["players"]:
            if self.gamestate["players"][i]["color"] == color:
                return i

    def fillInDiscTiles(self):
        listOfDisc = []
        with open("data/discoverytiles.json") as f:
            discTile_data = json.load(f)
        for tile in discTile_data:
            for x in range(discTile_data[tile]["num"]):
                listOfDisc.append(tile)
        random.shuffle(listOfDisc)
        self.gamestate["discTiles"]= listOfDisc
        self.update()

    def get_short_faction_name(self, full_name):
        if full_name == "Descendants of Draco":
            return "draco"
        elif full_name == "Mechanema":
            return "mechanema"
        elif full_name == "Planta":
            return "planta"
        elif full_name == "Orian Hegemony" or full_name == "Orion Hegemony":
            return "orion"
        elif full_name == "Hydran Progress":
            return "hydran"
        elif full_name == "Eridani Empire":
            return "eridani"
        elif "Terran" in full_name:
            return full_name.lower().replace(" ","_")
    
    def formRelationsBetween(self, player1, player2):
        for x,tile in enumerate(player1["reputation_track"]):
            if isinstance(tile, str) and (tile == "amb" or tile == "mixed"):
                player1["reputation_track"][x]=tile+"-"+self.get_short_faction_name(player2["name"])+"-"+player2["color"]
                break
        for x,tile in enumerate(player2["reputation_track"]):
            if isinstance(tile, str) and (tile == "amb" or tile == "mixed"):
                player2["reputation_track"][x]=tile+"-"+self.get_short_faction_name(player1["name"])+"-"+player1["color"]
                break

        self.update()
    def breakRelationsBetween(self, player1, player2):
        for x,tile in enumerate(player1["reputation_track"]):
            if player2["color"] in tile:
                player1["reputation_track"][x]=tile.split("-")[0]
                break
        for x,tile in enumerate(player2["reputation_track"]):
            if player1["color"] in tile:
                player2["reputation_track"][x]=tile.split("-")[0]
                break

        self.update()

    def getNextDiscTile(self, tile:str):
        nextTile = self.gamestate["discTiles"].pop()
        self.gamestate["board"][tile]["disctile"]=0
        self.update()
        return nextTile
    def setTurnOrder(self, order):
        self.gamestate["turn_order"]=order
        self.update()

    def update_player(self, *args):

        for ar in args:
            self.gamestate["players"][ar.player_id] = ar.stats
        self.update()

    def get_system_coord(self, sector):
        for i in (self.gamestate["board"]):
            if self.gamestate["board"][i]["sector"] == sector:
                return(i)
        return(False)


    def get_owned_tiles(self, player):
        tile_map = self.gamestate["board"]
        color = player["color"]
        tiles = []
        for tile in tile_map:
            if "owner" in tile_map[tile] and tile_map[tile]["owner"] == color:
                tiles.append(tile)
        return tiles

    async def send_files(self, interaction, files, thread, message, view):
        for file in files:
            await thread.send(message,file=file,view=view)

    async def showUpdate(self, message:str, interaction: discord.Interaction, bot):
        self.updateNamesAndOutRimTiles(interaction)
        if "-" in interaction.channel.name:
            thread_name = interaction.channel.name.split("-")[0]+"-bot-map-updates"
            thread = discord.utils.get(interaction.channel.threads, name=thread_name)
            if thread is not None:
                # Sending a message to the thread
                drawing = DrawHelper(self.gamestate)
                view = View()
                view.add_item(Button(label="Show Game",style=discord.ButtonStyle.blurple, custom_id="showGame"))
                view.add_item(Button(label="Show Reputation",style=discord.ButtonStyle.gray, custom_id="showReputation"))
                map = drawing.show_map()
                stats = drawing.show_stats()
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run_coroutine_threadsafe, self.send_files(interaction, [map,stats], thread, message, view),bot.loop)
                # await thread.send(message,file=drawing.show_map())
                # await thread.send(message,file=drawing.show_stats(), view=view)

    def getPlayerFromHSLocation(self, location):
        tileID = self.get_gamestate()["board"][location]["sector"]
        return next((player for player in self.get_gamestate()["players"] if str(self.get_gamestate()["players"][player]["home_planet"]) == tileID), None)
    def getPlayerFromPlayerName(self, player_name):
        return next((player for player in self.get_gamestate()["players"] if str(self.get_gamestate()["players"][player]["player_name"]) == player_name), None)
    



    def is_everyone_passed(self):
        listHS = [201,203,205,207,209,211]
        for number in listHS:
            nextPlayer = self.getPlayerFromHSLocation(str(number))
            if nextPlayer is not None and not self.get_gamestate()["players"].get(nextPlayer, {}).get("passed", False):
                return False
        return True

    def get_next_player(self, player):

        if "turn_order" not in self.get_gamestate() or player["player_name"] not in self.get_gamestate()["turn_order"]:
            listHS = [201,203,205,207,209,211]
            playerHSID = player["home_planet"]
            tileLocation = int(self.getLocationFromID(playerHSID))
            index = listHS.index(tileLocation)
            if index is None:
                return None
            newList = listHS[index+1:] + listHS[:index] + [listHS[index]]
            for number in newList:
                nextPlayer = self.getPlayerFromHSLocation(str(number))
                if nextPlayer is not None and not self.get_gamestate()["players"].get(nextPlayer, {}).get("perma_passed", False):
                    return self.get_gamestate()["players"][nextPlayer]
            return None
        else:
            listPlayers = self.get_gamestate()["turn_order"]
            index = listPlayers.index(player["player_name"])
            newList = listPlayers[index+1:] + listPlayers[:index] + [listPlayers[index]]
            for player_name in newList:
                nextPlayer = self.getPlayerFromPlayerName(player_name)
                if nextPlayer is not None and not self.get_gamestate()["players"].get(nextPlayer, {}).get("perma_passed", False):
                    return self.get_gamestate()["players"][nextPlayer]
            return None
        # """

        # :param player: takes in a players stats in dict form. NOT a PlayerHelper object!
        # :return:
        # """
        # player_systems = []
        # player_home = player["home_planet"]
        # for i in ["201", "203", "205", "207", "209", "211"]:
        #     if "owner" in self.gamestate["board"][i] and self.gamestate["board"][i]["owner"] != 0:
        #         player_systems.append(i)
        # tile = self.get_system_coord(player_home)
        # index = player_systems.index(tile) + 1
        # index = index % len(player_systems)
        # new_player_color = self.gamestate["board"][player_systems[index]]["owner"]
        # return self.get_player_from_color(new_player_color)

