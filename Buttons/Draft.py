import asyncio
import json
import random
import discord
from discord.ui import View
from Buttons.DiscoveryTile import DiscoveryTileButtons
from Buttons.Turn import TurnButtons
from helpers.DrawHelper import DrawHelper
from helpers.EmojiHelper import Emoji
from helpers.GamestateHelper import GamestateHelper
from helpers.PlayerHelper import PlayerHelper
from discord.ui import View, Button

class DraftButtons:

    @staticmethod  
    async def startDraft(game: GamestateHelper, player_list, interaction:discord.Interaction, channel):
        random.shuffle(player_list)
        list = ""
        game.initilizeKey("draftedFactions")
        game.initilizeKey("draftingPlayers")
        for x, player in enumerate(player_list):
            member = interaction.guild.get_member(player[0])
            list += str(x+1)+". "+member.mention +"\n"
            game.addToKey("draftingPlayers",player[0])
        list += """For your reference, the factions currently available in the bot are the following 8, plus the 6 terran equivalents. First timers are encouraged to use the terran factions, which are all the same and dont have as many quirks (the quirks are tame compared to TI4 asymmetry though):  
        1. Hydran Progress   
        2. Eridian Empire   
        3. Orion Hegemony   
        4. Mechanema   
        5. Descendants of Draco   
        6. Planta  
        7. Wardens of Magellan
        8. Enlightened of Lyra
        9. Rho Indi Syndicate\n
        """
        await channel.send(list)
        playerID = game.get_gamestate()["draftingPlayers"][0]
        member = interaction.guild.get_member(playerID)
        await channel.send(member.mention+" Please draft a faction from those available",view=DraftButtons.getDraftButtons(game))
        


    @staticmethod
    def getDraftButtons(game:GamestateHelper):
        view = View()
        factionsAvailable = [("Hydran Progress", "hyd"),
        ("Eridian Empire", "eri"),
        ("Orion Hegemony", "ori"),
        ("Descendants of Draco", "dra"),
        ("Mechanema", "mec"),
        ("Planta", "pla"),
        ("Wardens of Magellan", "mag"),
        ("Enlightened of Lyra", "lyr"),
        ("Rho Indi Syndicate", "rho"),
        ("Terran Alliance (Orion)", "ter1"),
        ("Terran Conglomerate (Mech)", "ter2"),
        ("Terran Directorate (Eridian)", "ter3"),
        ("Terran Federation (Hydran)", "ter4"),
        ("Terran Republic (Draco)", "ter5"),
        ("Terran Union (Planta)", "ter6")]
        for faction,key in factionsAvailable:
            colorsAlreadyChosen = []
            for playerID,factionKey in game.gamestate["draftedFactions"]:
                colorsAlreadyChosen.append(DraftButtons.getColor(factionKey))
            if DraftButtons.getColor(key) in colorsAlreadyChosen:
                continue
            shorterName = faction
            if "(" in faction:
                shorterName=shorterName[:(faction.find("(")-1)]
            shortFaction =game.getShortFactionNameFromFull(shorterName)
            if "terran" in shortFaction:
                shortFaction += "_"
            emoji = Emoji.getEmojiByName(shortFaction+"token")
            view.add_item(Button(label=f"{faction}", emoji=emoji, style=discord.ButtonStyle.gray, custom_id=f"draftFaction_{key}_{faction}"))
        return view
    
    @staticmethod  
    async def draftFaction(game: GamestateHelper, interaction:discord.Interaction, customID:str):
        playerID = game.get_gamestate()["draftingPlayers"][0]
        if interaction.user.id != playerID:
            await interaction.followup.send("These buttons are not for you",ephemeral=True)
            return
        factionKey = customID.split("_")[1]
        factionName = customID.split("_")[2]
        await interaction.channel.send(interaction.user.mention +" drafted "+factionName)
        await interaction.message.delete()
        game.removeFromKey("draftingPlayers",playerID)
        game.addToKey("draftedFactions",(playerID,factionKey))
        if len(game.get_gamestate()["draftingPlayers"]) > 0:
            playerID = game.get_gamestate()["draftingPlayers"][0]
            member = interaction.guild.get_member(playerID)
            await interaction.channel.send(member.mention+" Please draft a faction from those available",view=DraftButtons.getDraftButtons(game))
        else:
            factionsList = []
            playerIDList = []
            for player,faction in game.get_gamestate()["draftedFactions"]:
                playerIDList.insert(0,player)
                factionsList.insert(0,faction)
            await DraftButtons.generalSetup(interaction, game, playerIDList, factionsList)



    @staticmethod
    def getColor(faction:str):
        if faction == "ter6" or faction == "pla":
            return "green"
        if faction == "ter3" or faction == "eri":
            return "red"
        if faction == "ter1" or faction == "ori":
            return "purple"
        if faction == "ter2" or faction == "mec":
            return "white"
        if faction == "ter5" or faction == "dra":
            return "yellow"
        if faction == "ter4" or faction == "hyd":
            return "blue"
        if faction == "mag":
            return "orange"
        if faction == "lyr":
            return "black"
        if faction == "rho":
            return "teal"
        if faction == "exl":
            return "pink"
        return "green"
    
    @staticmethod
    async def generalSetup(interaction: discord.Interaction, game:GamestateHelper, temp_player_list, temp_faction_list):
        colors = ["blue", "red", "green", "yellow", "purple", "white"]
        count = 0
        listPlayerHomes=[]
        x = -1
        for i in temp_player_list:
            x = x+1
            if i != None and temp_faction_list[x] != None:
                player = i
                faction = temp_faction_list[x]
                player_color = DraftButtons.getColor(faction)
                if player_color in colors:
                    colors.remove(player_color)
                else:
                    player_color = colors.pop(0)
                game.player_setup(player, faction, player_color)
                home = game.get_player(player)["home_planet"]
                listPlayerHomes.append([home, player_color])
                count = count + 1
        
        listOfTilesPos = ["201", "207", "205", "211", "203", "209"]  
        tile_mapping = {  
            3: ["201", "205", "209", "211", "203", "207"],  
            4: ["201", "205", "207", "211", "203", "209"],  
            5: ["201", "203", "205", "209", "211", "207"],  
            6: ["201", "203", "205", "207", "209", "211"]  
        }  
        if count in tile_mapping:  
            listOfTilesPos = tile_mapping[count]  
        hyperlane5 = False
        if "5playerhyperlane" in game.gamestate and game.gamestate["5playerhyperlane"]:
            hyperlane5 = True
        listDefended = ["271","272","273","274","271"]
        random.shuffle(listDefended)
        game.add_tile("000", 0, "001")
        for i in range(count):
            rotDet = ((180 - (int(listOfTilesPos[i])-201)/2 * 60) + 360)%360
            game.add_tile(listOfTilesPos[i], rotDet, listPlayerHomes[i][0], listPlayerHomes[i][1])
        if not hyperlane5:
            for i in range(6-count):
                rotDet = ((180 - (int(listOfTilesPos[5-i])-201)/2 * 60) + 360)%360
                game.add_tile(listOfTilesPos[5-i], rotDet, listDefended[i])
        for i in range(101, 107):
            if hyperlane5 and i == 104:
                continue
            game.add_tile(str(i), 0, "sector1back")
        for i in range(201, 213):
            if hyperlane5 and (i == 206 or i == 207):
                continue
            if str(i) not in listOfTilesPos:
                game.add_tile(str(i), 0, "sector2back")
        for i in range(301, 319):
            if hyperlane5 and (i == 309 or i == 310 or i == 311):
                continue
            game.add_tile(str(i), 0, "sector3back")
        if game.gamestate["setup_finished"] != 1:
            game.setup_finished()
        #game.fillInDiscTiles()
        await interaction.channel.send("Done With Setup!")
        
        
        asyncio.create_task(game.showUpdate("Start of Game",interaction))
        view = TurnButtons.getStartTurnButtons(game, game.get_player(temp_player_list[0]), "dummy")
        game.initilizeKey("activePlayerColor")
        game.addToKey("activePlayerColor",game.get_player(temp_player_list[0])["color"])
        game.updatePingTime()
        await interaction.channel.send("## "+game.getPlayerEmoji(game.get_player(temp_player_list[0]))+" started their turn")
        await interaction.channel.send(f"{game.get_player(temp_player_list[0])['player_name']} use these buttons to do your turn. "+ game.displayPlayerStats(game.get_player(temp_player_list[0])),view=view)