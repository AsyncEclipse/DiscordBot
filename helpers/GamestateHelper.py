import asyncio
import json
import time
import portalocker 
import discord
import config
from helpers.DrawHelper import DrawHelper
from helpers.EmojiHelper import Emoji
from helpers.PlayerHelper import PlayerHelper
import os
from jproperties import Properties
import random
from discord.ui import View, Button


class GamestateHelper:
    def __init__(self, game_id: discord.TextChannel = None, nameID: str = None, overRideLock:bool=False):
        if game_id is not None:
            nameID = game_id.name
        self.file = None
        if "-" in nameID:
            game_id = nameID.split("-")[0]
        else:
            game_id = nameID
        self.game_id = game_id
        if overRideLock:
            self.release_lock()
        self.gamestate = self.get_gamestate()

    def getPlayersID(self, player):
        return player["player_name"].replace(">@", "").replace(">", "")

    def setRound(self, rnd: int):
        self.gamestate["roundNum"] = rnd
        self.update()

    def addShrine(self, tile, shrineType):
        self.gamestate["board"][tile][f"{shrineType}_shrine"] = 1
        if "shrines" in self.gamestate["board"][tile]:
            self.gamestate["board"][tile]["shrines"] += 1
        else:
            self.gamestate["board"][tile]["shrines"] = 1
        self.update()

    def initilizeKey(self, key):
        self.gamestate[key] = []
        self.update()

    def changeShip(self, ship, value):
        self.gamestate[ship+"_type"] = value
        self.update()
    def removeFromKey(self, key, deletion):
        if deletion in self.gamestate.get(key, []):
            self.gamestate[key].remove(deletion)
            self.update()

    def addToKey(self, key, addition):
        if addition not in self.gamestate.get(key, []):
            self.gamestate[key].append(addition)
            self.update()

    def saveLastButtonPressed(self, buttonID: str):
        self.gamestate["lastButton"] = buttonID
        self.update()

    def setLockedStatus(self, statusOfLock: bool):
        if statusOfLock:
            #self.gamestate["gameLocked"] = "yes"
            return self.acquire_lock()
        else:
            self.release_lock()
            return None
            #self.gamestate["gameLocked"] = "no"
        #self.update()

    def changeColor(self, colorOld, colorNew):
        def replace_string_in_dict(original_dict, old_string, new_string):
            new_dict = {}
            for key, value in original_dict.items():
                new_key = key.replace(old_string, new_string)
                if isinstance(value, dict):
                    new_value = replace_string_in_dict(value, old_string, new_string)
                elif isinstance(value, list):
                    new_value = [item.replace(old_string, new_string)
                                 if isinstance(item, str) else item for item in value]
                elif isinstance(value, str):
                    new_value = value.replace(old_string, new_string)
                else:
                    new_value = value
                new_dict[new_key] = new_value
            return new_dict
        modified_dict = replace_string_in_dict(self.gamestate, colorOld, colorNew)

        self.gamestate = modified_dict
        self.update()

    async def endGame(self, interaction: discord.Interaction):
        guild = interaction.guild
        self.gamestate["gameEnded"] = True
        self.update()
        category = interaction.channel.category
        role = discord.utils.get(guild.roles, name=self.game_id)
        for channel in guild.channels:
            if isinstance(channel, discord.TextChannel) and self.game_id in channel.name:
                await channel.delete()
        if len(category.channels) < 1:
            await category.delete()
        chronicles_channel = discord.utils.get(guild.channels, name='game-chronicles')
        if chronicles_channel and isinstance(chronicles_channel, discord.TextChannel):
            message_to_send = self.game_id + " has concluded!"
            message = await chronicles_channel.send(message_to_send)
            thread = await message.create_thread(name=self.game_id)
            drawing = DrawHelper(self.gamestate)
            map = await asyncio.to_thread(drawing.show_game)
            await thread.send(file=map)
            winner, highestScore, faction = self.getWinner()
            await thread.send(f"{role.mention} final state here. {winner} won with {highestScore} points.")
        if role:
            await role.delete()
        file_path = f"{config.gamestate_path}/{self.game_id}_saveFile.json"
        if os.path.exists(file_path):
            os.remove(file_path)

    def updatePingTime(self):
        self.gamestate["lastPingTime"] = time.time()
        self.update()

    def getWinner(self):
        winner = ""
        winnerFaction = ""
        highestScore = 0
        resources = 0
        for player in self.gamestate["players"]:
            playerObj = self.get_player(player)
            drawing = DrawHelper(self.gamestate)
            points = drawing.get_public_points(playerObj, False)
            totalResources = playerObj["science"] + playerObj["money"] + playerObj["materials"]
            if points > highestScore:
                highestScore = points
                winner = playerObj["player_name"]
                winnerFaction = playerObj["name"]
                resources = totalResources
            if points == highestScore:
                if totalResources > resources:
                    winner = playerObj["player_name"]
                    winnerFaction = playerObj["name"]
                    resources = totalResources
        return (winner, highestScore, winnerFaction)

    def setAdvancedAI(self, status: bool):
        self.gamestate["advanced_ai"] = status
        self.update()

    def setOutlines(self, status: bool):
        self.gamestate["turnOffLines"] = not status
        self.update()
    
    def setCommunityMode(self, status: bool):
        self.gamestate["communityMode"] = status
        self.update()

    def setFancyShips(self, status: bool):
        self.gamestate["fancy_ships"] = status
        self.update()

    async def declareWinner(self, interaction: discord.Interaction):
        self.gamestate["gameEnded"] = True
        self.update()
        drawing = DrawHelper(self.gamestate)
        winner, highestScore, faction = self.getWinner()
        if interaction.message:
            await interaction.message.delete()
        guild = interaction.guild
        role = discord.utils.get(guild.roles, name=self.game_id)
        stats = await asyncio.to_thread(drawing.show_game)
        await interaction.channel.send(f"{role.mention} {winner} is the winner with {highestScore} points",
                                       file=stats)
        view = View()
        view.add_item(Button(label="End Game", style=discord.ButtonStyle.blurple, custom_id="endGame"))
        await interaction.channel.send("Hit this button to cleanup the channels.", view=view)

    def getLocationFromID(self, id):
        return next((tile for tile in self.gamestate["board"]
                     if self.gamestate["board"][tile]["sector"] == str(id)),
                    None)

    def get_gamestate(self):
        f= open(f"{config.gamestate_path}/{self.game_id}.json", "r")
        self.file = f
        gamestate = json.load(f)
        return gamestate
    
    def is_file_open(self,file_path):  
        try:  
            os.rename(file_path, file_path)  
            return False  
        except OSError:  
            return True  
    
    def acquire_lock(self):  
        file_handle = self.file
        if self.file == None or not self.is_file_open(f"{config.gamestate_path}/{self.game_id}.json"):
            file_handle = open(f"{config.gamestate_path}/{self.game_id}.json", "r+")  
            self.file = file_handle
        try:  
            portalocker.lock(file_handle, portalocker.LOCK_EX | portalocker.LOCK_NB)  
        except portalocker.LockException:  
            file_handle.close()  
            return None 
        return file_handle  

    def release_lock(self):  
        file_handle = self.file 
        if file_handle == None or not self.is_file_open(f"{config.gamestate_path}/{self.game_id}.json"):
            file_handle = open(f"{config.gamestate_path}/{self.game_id}.json", "r")
        portalocker.unlock(file_handle)
        file_handle.close()  

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
        ring = int(int(ring) / 100)
        ring = min(3, ring)
        if all([len(self.gamestate[f"tile_deck_{ring}00"]) == 0,
                len(self.gamestate.get(f"tile_discard_deck_{ring}00", [])) > 0]):
            self.gamestate[f"tile_deck_{ring}00"] = self.gamestate[f"tile_discard_deck_{ring}00"]
            self.gamestate[f"tile_discard_deck_{ring}00"] = []
        random.shuffle(self.gamestate[f"tile_deck_{ring}00"])
        tile = self.gamestate[f"tile_deck_{ring}00"].pop(0)
        self.update()
        return tile

    def tile_draw_specific(self, ring, system):
        ring = int(int(ring) / 100)
        ring = min(3, ring)
        if system in self.gamestate[f"tile_deck_{ring}00"]:
            self.gamestate[f"tile_deck_{ring}00"].remove(system)
        self.update()
        return system

    def add_specific_tile_to_deck(self, ring, system):
        ring = int(int(ring) / 100)
        ring = min(3, ring)
        if system not in self.gamestate[f"tile_deck_{ring}00"]:
            self.gamestate[f"tile_deck_{ring}00"].append(system)
        self.update()
        return system

    def tile_discard(self, sector):
        firstNum = int(int(sector) / 100)
        firstNum = min(3, firstNum)
        if "tile_discard_deck_" + str(firstNum) + "00" not in self.gamestate:
            self.gamestate["tile_discard_deck_" + str(firstNum) + "00"] = []
        self.gamestate[f"tile_discard_deck_{firstNum}00"].append(sector)
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
        elif shipAbbreviation == "orb":
            return "orbital"
        elif shipAbbreviation == "mon":
            return "monolith"
        else:
            return shipAbbreviation

    @staticmethod
    def getShipShortName(shipName: str):
        shipName = shipName.lower()
        if shipName == "interceptor":
            return "int"
        elif shipName == "cruiser":
            return "cru"
        elif shipName == "dreadnought" or shipName == "dread":
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
        elif fullName == "Eridani Empire" or fullName == "Eridian Empire":
            return "eridani"
        elif fullName == "Wardens of Magellan":
            return "magellan"
        elif fullName == "Enlightened of Lyra":
            return "lyra"
        elif fullName == "Rho Indi Syndicate":
            return "rho"
        elif fullName == "The Exiles":
            return "exile"
        elif "Terran" in fullName:
            return fullName.lower().replace(" ", "_")

        return fullName

    def find_player_faction_name_from_color(self, color):
        if color == "ai" or self.get_player_from_color(color) == color:
            return color
        return self.gamestate["players"][self.get_player_from_color(color)]["name"]

    def rotate_tile(self, position, orientation):
        tile = self.gamestate["board"][position]
        tile.update({"orientation": (tile["orientation"] + orientation) % 360})
        self.gamestate["board"][position] = tile
        self.update()

    def addWarpPortal(self, position):
        tile = self.gamestate["board"][position]
        tile.update({"warp": 1})
        tile["warpPoint"] = 1
        self.gamestate["board"][position] = tile
        self.update()

    def add_tile(self, position, orientation, sector, owner=None):

        with open("data/sectors.json") as f:
            tile_data = json.load(f)
        try:
            tile = tile_data[sector]
            if owner is not None:
                tile["owner"] = owner
                if position not in self.gamestate["players"][self.get_player_from_color(owner)]["owned_tiles"]:
                    self.gamestate["players"][self.get_player_from_color(owner)]["owned_tiles"].append(position)

            if tile["ancient"] or tile["guardian"] or tile["gcds"]:
                adv = ""
                anc, grd, gcds = tile["ancient"], tile["guardian"], tile["gcds"]
                if anc:
                    tile["player_ships"].append("ai-anc" + adv)
                    if tile["ancient"] > 1:
                        tile["player_ships"].append("ai-anc" + adv)
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
        if self.gamestate.get("5playerhyperlane"):
            if self.gamestate.get("player_count") == 5:
                with open("data/tileAdjacencies_5p.properties", "rb") as f:
                    configs.load(f)
            elif self.gamestate.get("player_count") == 4:
                with open("data/tileAdjacencies_4p.properties", "rb") as f:
                    configs.load(f)
            else:
                with open("data/tileAdjacencies.properties", "rb") as f:
                    configs.load(f)
        else:
            with open("data/tileAdjacencies.properties", "rb") as f:
                configs.load(f)
        if position is not None and sector != "sector3back" and sector != "supernovaExploded":
            tiles = configs.get(position)[0].split(",")
            for adjTile in tiles:
                discard = 0
                if "tile_discard_deck_300" in self.gamestate:
                    discard = len(self.gamestate["tile_discard_deck_300"])
                if adjTile not in self.gamestate["board"] and len(self.gamestate["tile_deck_300"]) + discard > 0 and adjTile in configs:
                    self.add_tile(adjTile, 0, "sector3back")
        self.update()

    def add_control(self, color, position):
        self.gamestate["board"][position]["owner"] = color
        if position not in self.gamestate["players"][self.get_player_from_color(color)]["owned_tiles"]:
            self.gamestate["players"][self.get_player_from_color(color)]["owned_tiles"].append(position)
        amount = max(0, self.gamestate["players"][self.get_player_from_color(color)]["influence_discs"] - 1)
        self.gamestate["players"][self.get_player_from_color(color)]["influence_discs"] = amount
        self.update()

    def add_damage(self, ship, position, damage):
        if "damage_tracker" in self.gamestate["board"][position]:
            if ship in self.gamestate["board"][position]["damage_tracker"]:
                damage = self.gamestate["board"][position]["damage_tracker"][ship] + damage
            else:
                self.gamestate["board"][position]["damage_tracker"][ship] = [0]
        else:
            self.gamestate["board"][position]["damage_tracker"] = {}
            self.gamestate["board"][position]["damage_tracker"][ship] = [0]
        self.gamestate["board"][position]["damage_tracker"][ship] = damage
        self.update()
        return damage

    def repair_damage(self, ship, position):
        damage = 0
        if "damage_tracker" in self.gamestate["board"][position]:
            if all([ship in self.gamestate["board"][position]["damage_tracker"],
                    self.gamestate["board"][position]["damage_tracker"][ship] > 0]):
                damage = self.gamestate["board"][position]["damage_tracker"][ship] - 1
            else:
                self.gamestate["board"][position]["damage_tracker"][ship] = [0]
        else:
            self.gamestate["board"][position]["damage_tracker"] = {}
            self.gamestate["board"][position]["damage_tracker"][ship] = [0]
        self.gamestate["board"][position]["damage_tracker"][ship] = damage
        self.update()
        return damage

    def destroy_ship(self, ship: str, position, destroyer):
        if "orb" not in ship:
            self.remove_units([ship], position)
        else:
            self.remove_pop(["orbital_pop"], position,
                            self.get_player_from_color(self.gamestate["board"][position]["owner"]), True)

        if "damage_tracker" in self.gamestate["board"][position]:
            if ship in self.gamestate["board"][position]["damage_tracker"]:
                del self.gamestate["board"][position]["damage_tracker"][ship]
        if destroyer != "ai" and destroyer not in ship:
            key = "ships_destroyed_by_" + destroyer
            if key not in self.gamestate["board"][position]:
                self.gamestate["board"][position][key] = []
            self.gamestate["board"][position][key].append(ship.split("-")[1])
        self.update()

    def cleanAllTheTiles(self):
        for position in self.gamestate["board"]:
            self.gamestate["board"][position].pop("damage_tracker", None)
            self.gamestate["board"][position].pop("unitsToRetreat", None)
            for player in self.gamestate["players"]:
                color = self.gamestate["players"][player]["color"]
                key = "ships_destroyed_by_" + color
                self.gamestate["board"][position].pop(key, None)
                self.gamestate["board"][position].pop("retreatPenalty" + color, None)
            if "player_ships" in self.gamestate["board"][position]:
                self.fixshipsOrder(position)
        self.update()

    def getReputationTilesToDraw(self, position, color):
        key = "ships_destroyed_by_" + color
        count = 1
        if "retreatPenalty" + color in self.gamestate["board"][position]:
            count = 0
        if "damage_tracker" in self.gamestate["board"][position]:
            del self.gamestate["board"][position]["damage_tracker"]
        if key not in self.gamestate["board"][position]:
            self.update()
            return count
        else:
            for ship in self.gamestate["board"][position][key]:
                if "anc" in ship or ship == "sb" or ship == "int" or ship == "orb":
                    count += 1
                if ship == "cru" or "grd" in ship:
                    count += 2
                if ship == "drd" or "gcds" in ship:
                    count += 3
            del self.gamestate["board"][position][key]
        self.update()
        return min(5, count)

    def remove_control(self, color, position):
        self.gamestate["board"][position]["owner"] = 0
        if "currentAction" in self.gamestate["board"][position]:
            self.gamestate["board"][position]["currentAction"] = "move"
        self.gamestate["players"][self.get_player_from_color(color)]["owned_tiles"].remove(position)
        amount = min(15, self.gamestate["players"][self.get_player_from_color(color)]["influence_discs"] + 1)
        self.gamestate["players"][self.get_player_from_color(color)]["influence_discs"] = amount
        self.update()

    def add_warp(self, position):
        self.gamestate["board"][position]["warp"] = 1
        self.gamestate["board"][position]["warpDisc"] = 2
        self.update()

    def updatePlayerNames(self, interaction: discord.Interaction):
        if self.gamestate.get("communityMode",False):
            for player in self.gamestate["players"]:
                shortFaction = self.getShortFactionNameFromFull(self.gamestate["players"][player]["name"])
                if "terran" in shortFaction:
                    shortFaction += "_"
                emoji = Emoji.getEmojiByName(f"{shortFaction}token")
                role = discord.utils.get(interaction.guild.roles, name=self.gamestate["players"][player]["color"])
                if role != None:
                    self.gamestate["players"][player]["player_name"] = f"{role.mention} {emoji}"
        self.update()

    async def updateNamesAndOutRimTiles(self, interaction: discord.Interaction):
        for player in self.gamestate["players"]:
            if "username" not in self.gamestate["players"][player]:
                if not self.gamestate.get("communityMode",False):
                    self.gamestate["players"][player]["username"] = interaction.guild.get_member(int(player)).display_name
                else:
                    self.gamestate["players"][player]["username"] = "Team "+self.gamestate["players"][player]["color"]
            tiles = self.gamestate["players"][player]["owned_tiles"][:]
            for tile in tiles:
                if any(["owner" not in self.gamestate["board"][tile],
                        self.gamestate["board"][tile]["owner"] != self.gamestate["players"][player]["color"]]):
                    self.gamestate["players"][player]["owned_tiles"].remove(tile)

        if len(self.gamestate["tile_deck_300"]) == 0:
            role = discord.utils.get(interaction.guild.roles, name=self.game_id)
            if len(self.gamestate.get("tile_discard_deck_300", [])) > 0:
                self.gamestate["tile_deck_300"] = self.gamestate["tile_discard_deck_300"]
                self.gamestate["tile_discard_deck_300"] = []
                if role:
                    await interaction.channel.send(role.mention +
                                                   " shuffling the discarded outer rim tiles back into the deck")
            else:
                keysToRemove = []
                for key, value in self.gamestate["board"].items():
                    if value["sector"] == "sector3back":
                        keysToRemove.append(key)
                if role and len(keysToRemove) > 0:
                    await interaction.channel.send(role.mention + " the outer rim has run out of tiles to explore")
                for key in keysToRemove:
                    del self.gamestate["board"][key]
        self.update()

    def makeEveryoneNotTraitor(self):
        for player in self.gamestate["players"]:
            if "traitor" in self.gamestate["players"][player]:
                self.gamestate["players"][player]["traitor"] = False
        self.update()

    def add_units_illegal(self, unit_list, position):
        color = unit_list[0].split("-")[0]
        for i in unit_list:
            self.gamestate["board"][position]["player_ships"].append(i)
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
            if all([color == self.gamestate["board"][position]["owner"],
                    len(self.gamestate["board"][position]["player_ships"]) > 0]):
                self.gamestate["board"][position]["player_ships"].insert(0, i)
            else:
                self.gamestate["board"][position]["player_ships"].append(i)
        self.update()

    def displayPlayerStats(self, player):
        money = player["money"]
        moneyIncrease = f"+{player['population_track'][player['money_pop_cubes'] - 1]}"
        moneyIncrease2 = "Error"
        if player["money_pop_cubes"] - 2 >= 0:
            moneyIncrease2 = f"+{player['population_track'][player['money_pop_cubes'] - 2]}"
        influence_track = [30, 25, 21, 17, 13, 10, 7, 5, 3, 2, 1, 0, 0, 0, 0, 0]
        moneyDecrease = str(influence_track[player["influence_discs"]])
        moneyDecrease2 = "Error"
        if player["influence_discs"] > 0:
            moneyDecrease2 = "-"+str(influence_track[player["influence_discs"] - 1])
        else:
            moneyDecrease2 = "Illegal (discs have run out)"
        science = player["science"]
        moneyEmoji = Emoji.getEmojiByName("money")
        scienceEmoji = Emoji.getEmojiByName("science")
        materialEmoji = Emoji.getEmojiByName("material")
        scienceIncrease = player["population_track"][player["science_pop_cubes"] - 1]
        scienceIncrease = f"+{scienceIncrease}"
        materials = player["materials"]
        materialsIncrease = player["population_track"][player["material_pop_cubes"] - 1]
        materialsIncrease = f"+{materialsIncrease}"
        msg = "\n".join([". Your current economic situation is as follows:",
                         f"{moneyEmoji}: {money} ({moneyIncrease} - {moneyDecrease})",
                         f"{scienceEmoji}: {science} ({scienceIncrease})",
                         f"{materialEmoji}: {materials} ({materialsIncrease})"])
        if player["influence_discs"] > 0:
            msg +=f"\nIf you spend another disk, your maintenance cost will go from -{moneyDecrease} to {moneyDecrease2}."
        else:
            msg += "\nYou cannot do more actions because you are out of influence disks"
        if player['money_pop_cubes'] > 1:
            msg += f"\nIf you find a way to drop another money cube, your income will go from {moneyIncrease} to {moneyIncrease2}."
        else:
            msg += "\nYou cannot place more money cubes because they have all been placed."
        msg += f"\nYou have {player['colony_ships']}/{player['base_colony_ships']} colony ships ready at this time."
        return msg

    def setCombatants(self, players, pos):
        self.gamestate["board"][pos]["combatants"] = players
        self.update()

    def setCurrentSpeed(self, speed, pos):
        self.gamestate["board"][pos]["currentSpeed"] = speed
        self.update()

    def setRetreatingPenalty(self, color, pos):
        self.gamestate["board"][pos]["retreatPenalty" + color] = True
        self.update()

    def setRetreatingUnits(self, unitsToRetreat, pos):
        if "unitsToRetreat" not in self.gamestate["board"][pos]:
            self.gamestate["board"][pos]["unitsToRetreat"] = []
        self.gamestate["board"][pos]["unitsToRetreat"].append(unitsToRetreat)
        self.update()

    def removeCertainRetreatingUnits(self, unitsToRetreat, pos):
        if "unitsToRetreat" not in self.gamestate["board"][pos]:
            self.gamestate["board"][pos]["unitsToRetreat"] = []
        if unitsToRetreat in self.gamestate["board"][pos]["unitsToRetreat"]:
            self.gamestate["board"][pos]["unitsToRetreat"].remove(unitsToRetreat)
        self.update()

    def getRetreatingUnits(self, pos):
        if "unitsToRetreat" not in self.gamestate["board"][pos]:
            self.gamestate["board"][pos]["unitsToRetreat"] = []
            self.update()
        return self.gamestate["board"][pos]["unitsToRetreat"]

    def fixshipsOrder(self, pos):
        from collections import OrderedDict

        if "player_ships" not in self.gamestate["board"][pos]:
            return
        self.gamestate["board"][pos]["player_ships"] = [s for s in self.gamestate["board"][pos]["player_ships"] if "-" in s]
        arr = self.gamestate["board"][pos]["player_ships"]
        if len(arr) < 2:
            return
        colors_seen = OrderedDict()
        
        excludedColors = []
        colors_seen["ai"] = 0

        for item in arr:
            color = item.split('-')[0]
            if color not in colors_seen:
                if "mon" in item or "orb" in item:
                    if color not in excludedColors:
                        excludedColors.append(color)
                else:
                    colors_seen[color] = len(colors_seen)

        for color in excludedColors:
            if color not in colors_seen:
                colors_seen[color] = len(colors_seen)

        self.gamestate["board"][pos]["player_ships"] = sorted([s.replace("adv", "") for s in arr],
                                                              key=lambda x: colors_seen[x.split('-')[0]])
        self.update()

    def setCurrentRoller(self, roller, pos):
        self.gamestate["board"][pos]["currentRoller"] = roller
        self.update()

    def setAttackerAndDefender(self, attacker, defender, pos):
        if isinstance(self.gamestate["board"][pos]["owner"], str) and attacker == self.gamestate["board"][pos]["owner"]:
            attacker = defender
            defender = self.gamestate["board"][pos]["owner"]
        self.gamestate["board"][pos]["attacker"] = attacker
        self.gamestate["board"][pos]["defender"] = defender
        self.update()

    def setUnresolvedHits(self, amount, pos):
        self.gamestate["board"][pos]["unresolvedHits"] = amount
        self.update()

    def add_pop_specific(self, originalType: str, popType: str, number: int, position: str, playerID):
        if self.gamestate["players"][playerID]["colony_ships"] > 0:
            self.gamestate["players"][playerID]["colony_ships"] -= 1
        else:
            return False
        if f"{originalType}_pop" in self.gamestate["board"][position]:
            self.gamestate["board"][position][f"{originalType}_pop"][number] += 1
        else:
            self.gamestate["board"][position][f"{originalType}_pop"] = [1]
        if popType.replace("adv", "") + "_pop_cubes" in self.gamestate["players"][playerID]:
            self.gamestate["players"][playerID][popType.replace("adv", "") + "_pop_cubes"] -= 1
        self.update()
        return True
    

    def lookAtAllTheTiles(self, color):
        self.updateSaveFile()
        tiles = ["301", "302", "303", "304", "305", "306", "307", "308", "309", "310", "311", "312", "313",
                              "314", "315", "316", "317", "318", "381", "382", "398", "397", "399", "396", "394", "393",
                              "201","202","203","204","205","206","207","208","209","210","211","214","281","101","102",
                              "103","104","105","106","107","108","109","110"]
        ships = [color+"-int", color+"-int",color+"-int",color+"-int",color+"-int", color+"-int",color+"-int",color+"-int",
                 color+"-cru",color+"-cru",color+"-cru",color+"-cru", color+"-sb",
                  color+"-sb",color+"-sb",color+"-sb", color+"-drd",color+"-drd",color+"-orb",color+"-mon"]
        tileCount = 101
        for tile in tiles:
            self.add_tile(str(tileCount), 0, tile)
            self.add_units_illegal(ships,str(tileCount))
            if tileCount == 106:
                tileCount = 201
            elif tileCount == 212:
                tileCount = 301
            elif tileCount == 318:
                tileCount = 401
            elif tileCount == 424:
                tileCount = 501
            elif tileCount == 530:
                tileCount = 601
            else:
                tileCount = tileCount + 1

    def refresh_two_colony_ships(self,  playerID):
        # "base_colony_ships"
        minNum = min(self.gamestate["players"][playerID]["colony_ships"] + 2,
                     self.gamestate["players"][playerID]["base_colony_ships"])
        self.gamestate["players"][playerID]["colony_ships"] = minNum
        self.update()
        return minNum

    def refresh_one_colony_ship(self,  playerID):
        # "base_colony_ships"
        minNum = min(self.gamestate["players"][playerID]["colony_ships"] + 1,
                     self.gamestate["players"][playerID]["base_colony_ships"])
        self.gamestate["players"][playerID]["colony_ships"] = minNum
        self.update()
        return minNum

    def add_pop(self, pop_list, position, playerID):
        neutralPop = 0
        orbitalPop = 0
        for i in pop_list:
            length = 0
            if i in self.gamestate["board"][position]:
                length = len(self.gamestate["board"][position][i])
            if "orbital" not in i:
                if self.gamestate["board"][position][i][0] + 1 <= length:
                    self.gamestate["board"][position][i][0] += 1
            else:
                self.gamestate["board"][position][i] = [1]
                length = len(self.gamestate["board"][position][i])

            if self.gamestate["board"][position][i][0] <= length:
                if all(["neutral" not in i,
                        "orbital" not in i,
                        self.gamestate["players"][playerID][i.replace("adv", "") + "_cubes"] > 1]):
                    self.gamestate["players"][playerID][i.replace("adv", "") + "_cubes"] -= 1
                else:
                    if "neutral" not in i:
                        orbitalPop += 1
                    else:
                        neutralPop += 1
        self.update()
        return neutralPop, orbitalPop

    def remove_pop(self, pop_list, position, playerID, graveYard: bool):
        neutralPop = 0
        orbitalPop = 0
        for i in pop_list:
            found = False
            if position != "dummy":
                for val, num in enumerate(self.gamestate["board"][position][i]):
                    if num > 0:
                        self.gamestate["board"][position][i][val] = num - 1
                        found = True
                        break
            else:
                found = True
            if found:
                if not graveYard:
                    if "neutral" not in i and "orbital" not in i:
                        if  self.gamestate["players"][playerID][i.replace("adv", "") + "_cubes"] < 13:
                            self.gamestate["players"][playerID][i.replace("adv", "") + "_cubes"] += 1
                    else:
                        if "neutral" not in i:
                            orbitalPop += 1
                        else:
                            neutralPop += 1
                else:
                    if "graveYard" not in self.gamestate["players"][playerID]:
                        self.gamestate["players"][playerID]["graveYard"] = []
                    self.gamestate["players"][playerID]["graveYard"].append(i.replace("adv", ""))
        self.update()
        return neutralPop, orbitalPop

    def is_population_gone(self, pos):
        tile = self.gamestate["board"][pos]
        for planet in tile:
            if "pop" in planet:
                if tile[planet] and tile[planet][0] != 0:
                    return False
        return True

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
            else:
                if i + "adv" in self.gamestate["board"][position]["player_ships"]:
                    self.gamestate["board"][position]["player_ships"].remove(i + "adv")
        self.update()

    async def upkeep(self, interaction: discord.Interaction):
        from Buttons.Influence import InfluenceButtons

        for player in self.gamestate["players"]:
            p1 = PlayerHelper(player, self.get_player(player))
            neutrals, orbitals = p1.upkeep()
            for cube in range(orbitals):
                view = View()
                planetTypes = ["money", "science"]
                for planetT in planetTypes:
                    if p1.stats[f"{planetT}_pop_cubes"] < 12:
                        view.add_item(Button(label=planetT.capitalize(), style=discord.ButtonStyle.blurple,
                                             custom_id=f"FCID{p1.stats['color']}_addCubeToTrack_"+planetT))
                await interaction.channel.send(f"{p1.stats['player_name']} An orbital cube was found in your graveyard,"
                                               " please tell the bot what track you want it to go on", view=view)
            for cube in range(neutrals):
                view = View()
                planetTypes = ["money", "science", "material"]
                for planetT in planetTypes:
                    if p1.stats[f"{planetT}_pop_cubes"] < 13:
                        view.add_item(Button(label=planetT.capitalize(),
                                             style=discord.ButtonStyle.blurple,
                                             custom_id=f"FCID{p1.stats['color']}_addCubeToTrack_{planetT}"))
                await interaction.channel.send(f"{p1.stats['player_name']},"
                                               " a neutral cube was found in your graveyard,"
                                               " please tell the bot which track you want it to go on.",
                                               view=view)

        tech_draws = self.gamestate["player_count"] + 3
        tech_draws = min(tech_draws,11)
        newTechs = []
        while tech_draws > 0 and len(self.gamestate["tech_deck"]) > 0:
            random.shuffle(self.gamestate["tech_deck"])
            picked_tech = self.gamestate["tech_deck"].pop(0)
            if picked_tech == "clo":
                picked_tech = "cld"
            self.gamestate["available_techs"].append(picked_tech)
            newTechs.append(picked_tech)
            with open("data/techs.json", "r") as f:
                tech_data = json.load(f)
            if tech_data[picked_tech]["track"] == "any":
                pass
            else:
                tech_draws -= 1
        drawing = DrawHelper(self.gamestate)
        await interaction.channel.send(f"Tech drawn at the end of the round",
                                           file=await asyncio.to_thread(drawing.show_select_techs,"New Techs",newTechs))
        if "turnsInPassingOrder" in self.gamestate and "pass_order" in self.gamestate:
            if self.gamestate["turnsInPassingOrder"]:
                self.setTurnOrder(self.gamestate["pass_order"])
            self.gamestate["pass_order"] = []

        rnd = 1
        if "roundNum" in self.gamestate:
            rnd = self.gamestate["roundNum"]
        if "upkeepSupernovaCheck" + str(rnd) not in self.gamestate:
            self.initilizeKey(f"upkeepSupernovaCheck{rnd}")
            tiles = self.gamestate["board"].copy()
            for position in tiles:
                if self.gamestate["board"][position].get("type") == "supernova":
                    msg = f"Rolled the following dice for the supernova in position {position}: "
                    total = 0
                    for x in range(2):
                        random_number = random.randint(1, 6)
                        if random_number != 1 and random_number != 6:
                            total += random_number
                        num = str(random_number).replace("1", "Miss").replace("6", ":boom:")
                        msg += str(num) + " "
                    if self.gamestate["board"][position]["owner"] != 0:
                        playerObj = self.getPlayerObjectFromColor(self.gamestate["board"][position]["owner"])
                        maxTech = max(len(playerObj["grid_tech"]), len(playerObj["military_tech"]))
                        maxTech = max(maxTech, len(playerObj["nano_tech"]))
                        total += maxTech
                    msg += (f"\nThe sum of that and the owners highest tech track ({str(total)})"
                            f" was compared against the round ({rnd}) and found to be ")
                    if total < rnd:
                        msg += "lesser, so the supernova exploded."
                        if self.gamestate["board"][position]["owner"] != 0:
                            await InfluenceButtons.removeInfluenceFinish(self, interaction,
                                                                         f"removeInfluenceFinish_{position}_normal",
                                                                         False)
                        units = self.gamestate["board"][position]["player_ships"][:]
                        for unit in units:
                            self.remove_units([unit], position)
                        del self.gamestate["board"][position]
                        self.add_tile(position, 0, "supernovaExploded")
                    else:
                        msg += " equal to or greater, and so the supernova is safe, for now."
                    await interaction.channel.send(msg)
        if "roundNum" in self.gamestate:
            self.gamestate["roundNum"] += 1
        else:
            self.gamestate["roundNum"] = 2
        self.initilizeKey("tilesToResolve")
        self.initilizeKey("queuedQuestions")
        self.initilizeKey("queuedDraws")
        self.cleanAllTheTiles()
        self.update()

    def getPlayerEmoji(self, player):
        shortFaction = self.getShortFactionNameFromFull(player["name"])
        if "terran" in shortFaction:
            shortFaction += "_"
        emoji = Emoji.getEmojiByName(f"{shortFaction}token")
        return emoji

    def createRoundNum(self):
        if "roundNum" not in self.gamestate:
            self.gamestate["roundNum"] = 1
            self.update()

    def player_setup(self, player_id, faction, color, interaction: discord.Interaction):
        if self.gamestate["setup_finished"] == 1:
            return ("The game has already been setup!")

        with open("data/factions.json", "r") as f:
            faction_data = json.load(f)

        self.gamestate["players"][str(player_id)].update({"color": color})
        self.gamestate["players"][str(player_id)].update(faction_data[faction])
        self.gamestate["players"][str(player_id)].update({"passed": False})
        self.gamestate["players"][str(player_id)].update({"perma_passed": False})
        name = self.gamestate["players"][str(player_id)]["player_name"]
        shortFaction = self.getShortFactionNameFromFull(self.gamestate["players"][str(player_id)]["name"])
        if "terran" in shortFaction:
            shortFaction += "_"
        emoji = Emoji.getEmojiByName(f"{shortFaction}token")
        self.gamestate["players"][str(player_id)]["player_name"] = f"{name} {emoji}"
        if self.gamestate.get("communityMode",False):
             role = discord.utils.get(interaction.guild.roles, name=self.gamestate["players"][str(player_id)]["color"])
             if role != None:
                self.gamestate["players"][str(player_id)]["player_name"] = f"{role.mention} {emoji}"
        self.update()
        # return(f"{name} is now setup!")

    def setup_finished(self):

        for i in self.gamestate["players"]:
            if len(self.gamestate["players"][i]) < 3:
                return f"{self.gamestate['players'][i]['player_name']} still needs to be setup!"
            else:
                p1 = PlayerHelper(i, self.get_player(i))
                home = self.get_system_coord(p1.stats["home_planet"])
                if p1.stats["name"] == "Orion Hegemony":
                    self.gamestate["board"][home]["player_ships"].append(p1.stats["color"] + "-cru")
                elif p1.stats["name"] == "Rho Indi Syndicate":
                    self.gamestate["board"][home]["player_ships"] = 2 * [p1.stats["color"] + "-int"]
                elif p1.stats["name"] == "The Exiles":
                    self.gamestate["board"][home]["player_ships"] = [p1.stats["color"] + "-orb",
                                                                     p1.stats["color"] + "-int"]
                else:
                    self.gamestate["board"][home]["player_ships"].append(p1.stats["color"] + "-int")

                if p1.stats["name"] == "Eridani Empire":
                    random.shuffle(self.gamestate["reputation_tiles"])
                    p1.stats["reputation_track"][0] = self.gamestate["reputation_tiles"].pop(0)
                    p1.stats["reputation_track"][1] = self.gamestate["reputation_tiles"].pop(0)
                    self.update_player(p1)

        self.gamestate["setup_finished"] = 1
        self.update()

    def setup_techs_and_outer_rim(self, count: int, galactic_events ,hyperlane):
        self.gamestate["player_count"] = count
        draw_count = {2: [5, 12], 3: [8, 14], 4: [14, 16], 5: [16, 18], 6: [18, 20],7:[22,22],8:[24,24],9:[24,26]}

        third_sector_tiles = ["301", "302", "303", "304", "305", "306", "307", "308", "309", "310", "311", "312", "313",
                              "314", "315", "316", "317", "318", "381", "382", "398", "397", "399", "396", "394", "393"]
        if not galactic_events and count < 7:
            third_sector_tiles = ["301", "302", "303", "304", "305", "306", "307", "308", "309", "310",
                                  "311", "312", "313", "314", "315", "316", "317", "318", "381", "382"]
        else:
            ranNum = random.randint(1, 2)
            if ranNum == 1:
                third_sector_tiles.remove("396")
            else:
                third_sector_tiles.remove("399")
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
                picked_tech = "cld"
            self.gamestate["available_techs"].append(picked_tech)

            if tech_data[picked_tech]["track"] == "any":
                pass
            else:
                tech_draws -= 1
        minorDraws = 4
        minor_species = ["Cruiser Discount", "Dreadnought Discount", "Monolith Discount", "Orbital Discount",
                         "Tech Discount", "Population Cube",
                         "Three Points", "Point Per Ambassador", "Point Per Reputation Tile"]
        self.gamestate["minor_species"] = []
        if hyperlane:
            self.gamestate["5playerhyperlane"] = True
        else:
            self.gamestate["5playerhyperlane"] = False
        while minorDraws > 0:
            random.shuffle(minor_species)
            self.gamestate["minor_species"].append(minor_species.pop())
            minorDraws -= 1
        self.update()

    def setTurnsInPassingOrder(self, status: bool):
        self.gamestate["turnsInPassingOrder"] = status

    def playerResearchTech(self, playerid, tech, techType):
        self.gamestate["available_techs"].remove(tech)
        self.gamestate["players"][playerid][f"{techType}_tech"].append(tech)
        with open("data/techs.json", "r") as f:
            tech_data = json.load(f)
        tech_details = tech_data.get(tech)
        self.gamestate["players"][playerid]["influence_discs"] += tech_details["infdisc"]
        if tech_details["activ1"] != 0:
            self.gamestate["players"][playerid][f"{tech_details['activ1']}_apt"] += 1
            if tech_details["activ1"] == "upgrade":
                self.gamestate["players"][playerid][f"{tech_details['activ1']}_apt"] += 1
        self.update()

    def playerReturnTech(self, playerid, tech, techType):
        self.gamestate["available_techs"].append(tech)
        self.gamestate["players"][playerid][f"{techType}_tech"].remove(tech)
        with open("data/techs.json", "r") as f:
            tech_data = json.load(f)
        tech_details = tech_data.get(tech)
        self.gamestate["players"][playerid]["influence_discs"] -= tech_details["infdisc"]
        if tech_details["activ1"] != 0:
            self.gamestate["players"][playerid][f"{tech_details['activ1']}_apt"] -= 1
            if tech_details["activ1"] == "upgrade":
                self.gamestate["players"][playerid][f"{tech_details['activ1']}_apt"] -= 1
        self.update()


    def playerRemoveAncientMight(self, playerid):
        self.gamestate["players"][playerid]["discoveryTileBonusPointTiles"] = []
        self.update()

    def update(self):
        try:
            with open(f"{config.gamestate_path}/{self.game_id}.json", "w") as f:
                json.dump(self.gamestate, f)
        except (OSError, IOError, json.JSONDecodeError, PermissionError):
            self.release_lock()
            with open(f"{config.gamestate_path}/{self.game_id}.json", "w") as f:
                json.dump(self.gamestate, f)
            self.acquire_lock()

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
            saveFile["newestSaveNum"] -= 1
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
                saveFile["oldestSaveNum"] += 1

            saveFile[str(saveFile["newestSaveNum"] + 1)] = self.gamestate
            saveFile["newestSaveNum"] += 1
            json.dump(saveFile, f)

    def get_player(self, player_id, interaction=None):
        if str(player_id) not in self.gamestate["players"]:
            if interaction != None:
                member = interaction.guild.get_member(player_id) 
                roles = member.roles
                role_names = [role.name for role in roles if role.name != "@everyone"]
                colors = ["blue", "red", "green", "yellow", "purple", "white", "pink", "brown", "teal"]
                for role_name in role_names:
                    for color in colors:
                        if color in role_name.lower():
                            return self.getPlayerObjectFromColor(color)
            return None
        return self.gamestate["players"][str(player_id)]

    def get_player_from_color(self, color):
        for i in self.gamestate["players"]:
            if self.gamestate["players"][i]["color"] == color:
                return i
        return color

    def getPlayerObjectFromColor(self, color):
        for i in self.gamestate["players"]:
            if self.gamestate["players"][i]["color"] == color:
                return self.gamestate["players"][i]

    # def fillInDiscTiles(self):
    #     listOfDisc = []
    #     with open("data/discoverytiles.json") as f:
    #         discTile_data = json.load(f)
    #     for tile in discTile_data:
    #         for x in range(discTile_data[tile]["num"]):
    #             listOfDisc.append(tile)
    #     random.shuffle(listOfDisc)
    #     self.gamestate["discTiles"]= listOfDisc
    #     self.update()

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
        elif full_name == "Wardens of Magellan":
            return "magellan"
        elif full_name == "Enlightened of Lyra":
            return "lyra"
        elif full_name == "Rho Indi Syndicate":
            return "rho"
        elif full_name == "The Exiles":
            return "exile"
        elif "Terran" in full_name:
            return full_name.lower().replace(" ", "_")

    def formRelationsBetween(self, player1, player2):
        pID = self.get_player_from_color(player1['color'])
        pID2 = self.get_player_from_color(player2['color'])
        found = False
        for x, tile in enumerate(player1["reputation_track"]):
            if isinstance(tile, str) and (tile == "amb" or tile == "mixed"):
                track = f"{tile}-{self.get_short_faction_name(player2['name'])}-{player2['color']}"
                self.gamestate["players"][pID]["reputation_track"][x] = track
                found = True
                break
        if not found:
            lowest = 10
            loc = 0
            for x, tile in enumerate(player1["reputation_track"]):
                if isinstance(tile, int) and tile < lowest:
                    loc = x
                    lowest = tile
            track = f"mixed-{self.get_short_faction_name(player2['name'])}-{player2['color']}"
            self.gamestate["players"][pID]["reputation_track"][loc] = track
            self.gamestate["reputation_tiles"].append(lowest)

        found = False
        for x, tile in enumerate(player2["reputation_track"]):
            if isinstance(tile, str) and (tile == "amb" or tile == "mixed"):
                track = f"{tile}-{self.get_short_faction_name(player1['name'])}-{player1['color']}"
                self.gamestate["players"][pID2]["reputation_track"][x] = track
                found = True
                break
        if not found:
            lowest = 10
            loc = 0
            for x, tile in enumerate(player2["reputation_track"]):
                if isinstance(tile, int) and tile < lowest:
                    loc = x
                    lowest = tile
            track = f"mixed-{self.get_short_faction_name(player1['name'])}-{player1['color']}"
            self.gamestate["players"][pID2]["reputation_track"][loc] = track
            self.gamestate["reputation_tiles"].append(lowest)

        self.update()

    def formMinorSpeciesRelations(self, player, minor_species_name: str):
        pID = self.get_player_from_color(player['color'])
        found = False
        for x, tile in enumerate(player["reputation_track"]):
            if isinstance(tile, str) and (tile == "amb" or tile == "mixed"):
                self.gamestate["players"][pID]["reputation_track"][x] = tile + "-minor-" + minor_species_name
                found = True
                break
        if not found:
            lowest = 10
            loc = 0
            for x, tile in enumerate(player["reputation_track"]):
                if isinstance(tile, int) and tile < lowest:
                    loc = x
                    lowest = tile
            self.gamestate["players"][pID]["reputation_track"][loc] = f"{tile}-minor-{minor_species_name}"
            self.gamestate["reputation_tiles"].append(lowest)
        if "Discount" in minor_species_name and "Tech" not in minor_species_name:
            discountedUnit = minor_species_name.replace(" Discount", "").replace("Dreadnought", "dread").lower()
            discount = 1
            if "dread" in discountedUnit or "monolith" in discountedUnit:
                discount = 2
            self.gamestate["players"][pID][f"cost_{discountedUnit}"] -= discount
        self.gamestate["minor_species"].remove(minor_species_name)

        self.update()

    def returnReputation(self, val: int, player):
        loc = 0
        pID = self.get_player_from_color(player["color"])
        for x, tile in enumerate(player["reputation_track"]):
            if isinstance(tile, int) and tile == val:
                loc = x
                lowest = tile
                self.gamestate["players"][pID]["reputation_track"][loc] = "mixed"
                self.gamestate["reputation_tiles"].append(lowest)
                self.update()
                return

    def breakRelationsBetween(self, player1, player2):
        pID = self.get_player_from_color(player1['color'])
        pID2 = self.get_player_from_color(player2['color'])
        for x, tile in enumerate(player1["reputation_track"]):
            if isinstance(tile, str) and player2["color"] in tile:
                self.gamestate["players"][pID]["reputation_track"][x] = tile.split("-")[0]
                if tile.split("-")[0] == "amb":
                    for x2, tile2 in enumerate(self.gamestate["players"][pID]["reputation_track"]):
                        if isinstance(tile2, str) and "mixed-" in tile2:
                            self.gamestate["players"][pID]["reputation_track"][x] = self.gamestate["players"][pID]["reputation_track"][x2].replace("mixed-","amb-")
                            self.gamestate["players"][pID]["reputation_track"][x2] = "mixed"
                            break
                break
        for x, tile in enumerate(player2["reputation_track"]):
            if isinstance(tile, str) and player1["color"] in tile:
                self.gamestate["players"][pID2]["reputation_track"][x] = tile.split("-")[0]
                if tile.split("-")[0] == "amb":
                    for x2, tile2 in enumerate(self.gamestate["players"][pID2]["reputation_track"]):
                        if isinstance(tile2, str) and "mixed-" in tile2:
                            self.gamestate["players"][pID2]["reputation_track"][x] = self.gamestate["players"][pID2]["reputation_track"][x2].replace("mixed-","amb-")
                            self.gamestate["players"][pID2]["reputation_track"][x2] = "mixed"
                            break
                break
        self.update()

    def breakMinorSpecies(self, player1):
        pID = self.get_player_from_color(player1['color'])
        for x, tile in enumerate(player1["reputation_track"]):
            if isinstance(tile, str) and "minor" in tile:
                minorName = tile.split("-")[2]
                self.gamestate["minor_species"].append(minorName)
                if "Discount" in minorName and "Tech" not in minorName:
                    discountedUnit = minorName.replace(" Discount", "").replace("Dreadnought", "dread").lower()
                    discount = 1
                    if "dread" in discountedUnit or "monolith" in discountedUnit:
                        discount = 2
                    self.gamestate["players"][pID][f"cost_{discountedUnit}"] += discount
                self.gamestate["players"][pID]["reputation_track"][x] = tile.split("-")[0]
                break
        self.update()

    def addDiscTile(self, tile: str):
        self.gamestate["board"][tile]["disctile"] = 1
        self.update()

    def getNextDiscTile(self, tile: str):
        nextTile = self.gamestate["discTiles"].pop()
        self.gamestate["board"][tile]["disctile"] = 0
        self.update()
        return nextTile

    def setTurnOrder(self, order):
        self.gamestate["turn_order"] = order
        self.update()

    def addToPassOrder(self, player_name):
        if "pass_order" not in self.gamestate:
            self.gamestate["pass_order"] = []
        if player_name not in self.gamestate["pass_order"]:
            self.gamestate["pass_order"].append(player_name)
        self.update()

    def useMagDisc(self, playerID):
        self.gamestate["players"][playerID]["magDiscTileUsed"] = True
        self.update()

    def update_player(self, *args):
        for ar in args:
            if ar.player_id in self.gamestate["players"]:
                self.gamestate["players"][ar.player_id] = ar.stats
            else:
                playerID = self.get_player_from_color(ar.stats["color"])
                self.gamestate["players"][playerID] = ar.stats
        self.update()

    def change_player(self, player_id, new_player_id, new_username, new_player_name):
        stats = self.gamestate["players"][player_id]
        del self.gamestate["players"][player_id]
        self.gamestate["players"][new_player_id] = stats
        self.gamestate["players"][new_player_id]["player_name"] = new_player_name
        self.gamestate["players"][new_player_id]["username"] = new_username
        self.update()

    def update_pulsar_action(self, tile, action):
        self.gamestate["board"][tile]["currentAction"] = action
        self.update()

    def get_system_coord(self, sector):
        for i in (self.gamestate["board"]):
            if self.gamestate["board"][i]["sector"] == sector:
                return i
        return False

    def get_owned_tiles(self, player):
        tile_map = self.gamestate["board"]
        color = player["color"]
        tiles = []
        for tile in tile_map:
            if tile_map[tile].get("owner") == color:
                tiles.append(tile)
        return tiles

    async def showGame(self,  thread, message):
        drawing = DrawHelper(self.gamestate)
        map_result = await asyncio.to_thread(drawing.show_game)
        view = View()
        view.add_item(Button(label="Show Game", style=discord.ButtonStyle.blurple, custom_id="showGame"))
        view.add_item(Button(label="Show Reputation", style=discord.ButtonStyle.gray, custom_id="showReputation"))
        message = await thread.send(message, file=map_result, view=view)

        image_url = message.attachments[0].url
        button = discord.ui.Button(label="View Full Image", url=image_url)
        view = discord.ui.View()
        view.add_item(button)
        await thread.send(view=view)

    async def showUpdate(self, message: str, interaction: discord.Interaction):
        if "-" in interaction.channel.name:
            thread_name = interaction.channel.name.split("-")[0] + "-bot-map-updates"
            thread = discord.utils.get(interaction.channel.threads, name=thread_name)
            if thread is not None:
                asyncio.create_task(self.showGame(thread, message))

    def getPlayerFromHSLocation(self, location):
        if "sector" not in self.gamestate["board"].get(location, []):
            return None
        tileID = self.gamestate["board"][location]["sector"]
        return next((player for player in self.gamestate["players"]
                     if str(self.gamestate["players"][player]["home_planet"]) == tileID), None)

    def getPlayerFromPlayerName(self, player_name):
        return next((player for player in self.gamestate["players"]
                     if str(self.gamestate["players"][player]["player_name"]) == player_name), None)

    def is_everyone_passed(self):
        listHS = [201, 203, 205, 207, 209, 211]
        if self.gamestate["player_count"] > 6:
                listHS = [302,304,306,308,310,312,314,316,318]
        for number in listHS:
            nextPlayer = self.getPlayerFromHSLocation(str(number))
            if nextPlayer is not None and not self.gamestate["players"].get(nextPlayer, {}).get("passed", False):
                return False
        return True

    def get_next_player(self, player):
        if player["player_name"] not in self.gamestate.get("turn_order", []):
            listHS = [201, 203, 205, 207, 209, 211]
            if self.gamestate["player_count"] > 6:
                listHS = [302,304,306,308,310,312,314,316,318]
            playerHSID = player["home_planet"]
            tileLocation = int(self.getLocationFromID(playerHSID))
            index = listHS.index(tileLocation)
            if index is None:
                return None
            newList = listHS[index + 1:] + listHS[:index] + [listHS[index]]
            for number in newList:
                nextPlayer = self.getPlayerFromHSLocation(str(number))
                if all([nextPlayer is not None,
                        not self.gamestate["players"].get(nextPlayer, {}).get("perma_passed", False),
                        not self.gamestate["players"].get(nextPlayer, {}).get("eliminated", False)]):
                    return self.gamestate["players"][nextPlayer]
            return None
        else:
            listPlayers = self.gamestate["turn_order"]
            index = listPlayers.index(player["player_name"])
            newList = listPlayers[index + 1:] + listPlayers[:index] + [listPlayers[index]]
            for player_name in newList:
                nextPlayer = self.getPlayerFromPlayerName(player_name)
                if all([nextPlayer is not None,
                        not self.gamestate["players"].get(nextPlayer, {}).get("perma_passed", False),
                        not self.gamestate["players"].get(nextPlayer, {}).get("eliminated", False)]):
                    return self.gamestate["players"][nextPlayer]
            return None
        # """

        # :param player: takes in a players stats in dict form. NOT a PlayerHelper object!
        # :return:
        # """
        # player_systems = []
        # player_home = player["home_planet"]
        # for i in ["201", "203", "205", "207", "209", "211"]:
        #     if self.gamestate["board"][i].get("owner", 0) != 0:
        #         player_systems.append(i)
        # tile = self.get_system_coord(player_home)
        # index = player_systems.index(tile) + 1
        # index %= len(player_systems)
        # new_player_color = self.gamestate["board"][player_systems[index]]["owner"]
        # return self.get_player_from_color(new_player_color)
