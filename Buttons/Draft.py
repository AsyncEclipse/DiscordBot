import asyncio
import random
import discord
from Buttons.Turn import TurnButtons
from helpers.EmojiHelper import Emoji
from helpers.GamestateHelper import GamestateHelper
from helpers.DrawHelper import DrawHelper
from helpers.PlayerHelper import PlayerHelper
from discord.ui import View, Button


class DraftButtons:
    @staticmethod
    async def startDraft(game: GamestateHelper, player_list, interaction: discord.Interaction, channel, tournament:bool):
        random.shuffle(player_list)
        message = []
        message.append("The drafting order is as follows:")
        factionsAvailable = [("Hydran Progress", "hyd"),
                             ("Eridani Empire", "eri"),
                             ("Orion Hegemony", "ori"),
                             ("Descendants of Draco", "dra"),
                             ("Mechanema", "mec"),
                             ("Planta", "pla"),
                             ("Wardens of Magellan", "mag"),
                             ("Enlightened of Lyra", "lyr"),
                             ("Rho Indi Syndicate", "rho"),
                             ("The Exiles", "exl")]
        game.initilizeKey("draftedFactions")
        game.initilizeKey("draftingPlayers")
        for x, player in enumerate(player_list):
            member = interaction.guild.get_member(player[0])
            message.append(f"{x + 1}. {member.mention}")
            game.addToKey("draftingPlayers", player[0])
        if not tournament:
            message.append("For your reference, the factions currently available in the bot are the following 10,"
                        " plus the 6 Terran equivalents. First-timers are encouraged to use the Terran factions,"
                        " which are all the same and don't have as many quirks"
                        " (the quirks are tame compared to TI4 asymmetry though).")
            message.extend(["1. Hydran Progress", "2. Eridani Empire", "3. Orion Hegemony",
                            "4. Mechanema", "5. Descendants of Draco", "6. Planta",
                            "7. Wardens of Magellan", "8. Enlightened of Lyra",
                            "9. Rho Indi Syndicate", "10. The Exiles"])
        await channel.send("\n".join(message))
        game.initilizeKey("bannedFactions")
        if tournament:
            msg2 = "The following factions have been banned:"
            for i in range(1, 10-len(player_list)):
                random_number = random.randint(0, len(factionsAvailable)-1)
                faction, key = factionsAvailable.pop(random_number)
                game.addToKey("bannedFactions",key)
                msg2 += "\n"+faction
            await channel.send(msg2)
        playerID = game.gamestate["draftingPlayers"][0]
        member = interaction.guild.get_member(playerID)
        await channel.send(f"{member.mention}, please draft a faction from those available.",
                           view=DraftButtons.getDraftButtons(game))

    @staticmethod
    def getDraftButtons(game: GamestateHelper):
        view = View()
        factionsAvailable = [("Hydran Progress", "hyd"),
                             ("Eridani Empire", "eri"),
                             ("Orion Hegemony", "ori"),
                             ("Descendants of Draco", "dra"),
                             ("Mechanema", "mec"),
                             ("Planta", "pla"),
                             ("Wardens of Magellan", "mag"),
                             ("Enlightened of Lyra", "lyr"),
                             ("Rho Indi Syndicate", "rho"),
                             ("The Exiles", "exl"),
                             ("Terran Alliance (Orion)", "ter1"),
                             ("Terran Conglomerate (Mech)", "ter2"),
                             ("Terran Directorate (Eridani)", "ter3"),
                             ("Terran Federation (Hydran)", "ter4"),
                             ("Terran Republic (Draco)", "ter5"),
                             ("Terran Union (Planta)", "ter6")]
        bannedFactions = game.gamestate["bannedFactions"]
        for faction, key in factionsAvailable:
            colorsAlreadyChosen = []
            for playerID, factionKey in game.gamestate["draftedFactions"]:
                colorsAlreadyChosen.append(DraftButtons.getColor(factionKey))
            if DraftButtons.getColor(key) in colorsAlreadyChosen:
                continue
            if key in bannedFactions:
                continue
            shorterName = faction
            if "(" in faction:
                shorterName = shorterName[:(faction.find("(")-1)]
            shortFaction = game.getShortFactionNameFromFull(shorterName)
            if "terran" in shortFaction:
                shortFaction += "_"
            emoji = Emoji.getEmojiByName(shortFaction + "token")
            view.add_item(Button(label=f"{faction}", emoji=emoji, style=discord.ButtonStyle.gray,
                                 custom_id=f"draftFaction_{key}_{faction}"))
        return view

    @staticmethod
    async def draftFaction(game: GamestateHelper, interaction: discord.Interaction, customID: str):
        playerID = game.gamestate["draftingPlayers"][0]
        if interaction.user.id != playerID:
            await interaction.followup.send("These buttons are not for you", ephemeral=True)
            return
        factionKey = customID.split("_")[1]
        factionName = customID.split("_")[2]
        await interaction.channel.send(f"{interaction.user.mention} drafted {factionName}.")
        if factionKey == "exl":
            await interaction.followup.send(f"REMINDER {interaction.user.mention}: You start with one extra colony "
                                            f"ship to be used on your first turn to populate your starting orbital.")
        await interaction.message.delete()
        game.removeFromKey("draftingPlayers", playerID)
        game.addToKey("draftedFactions", (playerID, factionKey))
        if len(game.gamestate["draftingPlayers"]) > 0:
            playerID = game.gamestate["draftingPlayers"][0]
            member = interaction.guild.get_member(playerID)
            await interaction.channel.send(f"{member.mention}, please draft a faction from those available.",
                                           view=DraftButtons.getDraftButtons(game))
        else:
            factionsList = []
            playerIDList = []
            for player, faction in game.gamestate["draftedFactions"]:
                playerIDList.insert(0, player)
                factionsList.insert(0, faction)
            await DraftButtons.generalSetup(interaction, game, playerIDList, factionsList)

    @staticmethod
    def getColor(faction: str):
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
            return "pink"
        if faction == "lyr":
            return "orange"
        if faction == "rho":
            return "brown"
        if faction == "exl":
            return "teal"
        return "green"

    @staticmethod
    async def startEridaniMinorSpeciesDraft(game: GamestateHelper, player, interaction: discord.Interaction, temp_player_list=None):
        """Start the minor species draft for Eridani in Community Empires mode."""
        if "eridani_minor_species_draft" not in game.gamestate:
            player_id = game.get_player_from_color(player["color"])
            game.gamestate["eridani_minor_species_draft"] = {
                "player_id": str(player_id),
                "selected": [],
                "remaining": 2,
                "temp_player_list": temp_player_list
            }
            game.update()
        
        draft_state = game.gamestate["eridani_minor_species_draft"]
        remaining = draft_state["remaining"]
        
        if remaining <= 0:
            # Draft complete, start the game
            await interaction.channel.send(f"{player['player_name']} has completed drafting their 2 minor species!")
            # Get first player from temp_player_list if available, otherwise use first player in game
            if draft_state.get("temp_player_list") and len(draft_state["temp_player_list"]) > 0:
                first_player_id = draft_state["temp_player_list"][0]
            else:
                first_player_id = int(list(game.gamestate["players"].keys())[0])
            first_player = game.get_player(first_player_id, interaction)
            asyncio.create_task(game.showUpdate("Start of Game", interaction))
            view = TurnButtons.getStartTurnButtons(game, first_player, "dummy")
            game.initilizeKey("activePlayerColor")
            game.addToKey("activePlayerColor", first_player["color"])
            game.updatePingTime()
            await interaction.channel.send(f"## {game.getPlayerEmoji(first_player)} started their turn.")
            await interaction.channel.send(f"{first_player['player_name']} use these buttons to do your turn"
                                           + game.displayPlayerStats(first_player), view=view)
            return
        
        view = View()
        drawing = DrawHelper(game.gamestate)
        for minor in game.gamestate["minor_species"]:
            if minor not in draft_state["selected"]:
                buttonID = f"FCID{player['color']}_draftMinorSpecies_" + minor
                view.add_item(Button(label=minor, style=discord.ButtonStyle.blurple, custom_id=buttonID))
        
        await interaction.channel.send(f"{player['player_name']}, choose a minor species to draft "
                                       f"({remaining} remaining).",
                                       view=view, file=await asyncio.to_thread(drawing.show_minor_species))

    @staticmethod
    async def draftMinorSpecies(game: GamestateHelper, player, interaction: discord.Interaction, buttonID: str):
        """Handle Eridani selecting a minor species during the draft."""
        print('drafting minor species', buttonID)
        # ButtonID format: FCID{color}_draftMinorSpecies_{minor_species_name}
        parts = buttonID.split("_")
        minor_species_name = "_".join(parts[2:])  # Join all parts after the second underscore in case name has underscores
        
        if "eridani_minor_species_draft" not in game.gamestate:
            await interaction.followup.send("Draft state not found. Please restart the draft.", ephemeral=True)
            return
        
        draft_state = game.gamestate["eridani_minor_species_draft"]
        
        if minor_species_name in draft_state["selected"]:
            await interaction.followup.send("You have already selected this minor species.", ephemeral=True)
            return
        
        if minor_species_name not in game.gamestate["minor_species"]:
            await interaction.followup.send("This minor species is not available.", ephemeral=True)
            return
        
        # Add the minor species to the player's extra reputation track slots
        pID = game.get_player_from_color(player["color"])
        found = False
        # Find the first available extra slot (positions 4 and 5, which are the extra slots we added)
        for x in range(4, len(player["reputation_track"])):
            tile = player["reputation_track"][x]
            if isinstance(tile, str) and tile == "mixed":
                game.gamestate["players"][str(pID)]["reputation_track"][x] = f"mixed-minor-{minor_species_name}"
                found = True
                break
        
        if not found:
            await interaction.followup.send("No available slot found for minor species.", ephemeral=True)
            return
        
        # Apply discount if applicable
        if "Discount" in minor_species_name and "Tech" not in minor_species_name:
            discountedUnit = minor_species_name.replace(" Discount", "").replace("Dreadnought", "dread").lower()
            discount = 1
            if "dread" in discountedUnit or "monolith" in discountedUnit:
                discount = 2
            game.gamestate["players"][str(pID)][f"cost_{discountedUnit}"] -= discount
        
        # Remove from available minor species
        game.gamestate["minor_species"].remove(minor_species_name)
        
        # Update draft state
        draft_state["selected"].append(minor_species_name)
        draft_state["remaining"] -= 1
        game.update()
        
        await interaction.message.delete()
        await interaction.channel.send(f"{player['player_name']} drafted {minor_species_name}.")
        
        # Refresh player data after update
        player = game.get_player(int(pID), interaction)
        
        # Continue draft if more selections needed
        if draft_state["remaining"] > 0:
            await DraftButtons.startEridaniMinorSpeciesDraft(game, player, interaction, draft_state.get("temp_player_list"))
        else:
            # Draft complete - use the stored temp_player_list to get first player
            temp_player_list = draft_state.get("temp_player_list")
            if temp_player_list and len(temp_player_list) > 0:
                first_player_id = temp_player_list[0]
            else:
                first_player_id = int(list(game.gamestate["players"].keys())[0])
            first_player = game.get_player(first_player_id, interaction)
            await interaction.channel.send(f"{player['player_name']} has completed drafting their 2 minor species!")
            asyncio.create_task(game.showUpdate("Start of Game", interaction))
            view = TurnButtons.getStartTurnButtons(game, first_player, "dummy")
            game.initilizeKey("activePlayerColor")
            game.addToKey("activePlayerColor", first_player["color"])
            game.updatePingTime()
            await interaction.channel.send(f"## {game.getPlayerEmoji(first_player)} started their turn.")
            await interaction.channel.send(f"{first_player['player_name']} use these buttons to do your turn"
                                           + game.displayPlayerStats(first_player), view=view)

    @staticmethod
    async def generalSetup(interaction: discord.Interaction, game: GamestateHelper,
                           temp_player_list, temp_faction_list):
        colors = ["blue", "red", "green", "yellow", "purple", "white", "pink", "brown", "teal"]
        count = 0
        listPlayerHomes = []
        x = -1
        for i in temp_player_list:
            x += 1
            if i is not None and temp_faction_list[x] is not None:
                player = i
                faction = temp_faction_list[x]
                player_color = DraftButtons.getColor(faction)
                if player_color in colors:
                    colors.remove(player_color)
                else:
                    player_color = colors.pop(0)
                game.player_setup(player, faction, player_color, interaction)
                home = game.get_player(player)["home_planet"]
                listPlayerHomes.append([home, player_color])
                count += 1

        listOfTilesPos = ["201", "207", "205", "211", "203", "209"]
        tile_mapping = {
            3: ["201", "205", "209", "211", "203", "207"],
            4: ["201", "205", "207", "211", "203", "209"],
            5: ["201", "203", "205", "209", "211", "207"],
            6: ["201", "203", "205", "207", "209", "211"],
            7: ["302","304","308","310","312","314","318","316","306"],
            8: ["302","304","308","310","312","314","316","318","306"],
            9: ["302","304","306","308","310","312","314","316","318"]
        }
        if count in tile_mapping:
            listOfTilesPos = tile_mapping[count]
        hyperlane5 = False
        if game.gamestate.get("5playerhyperlane"):
            hyperlane5 = True
        if count == 4 and hyperlane5:
            listOfTilesPos =["203", "205", "209", "211", "207", "201"]
        listDefended = ["271", "272", "273", "274", "271"]
        random.shuffle(listDefended)
        game.add_tile("000", 0, "001")
        for i in range(count):
            rotDet = (180 - 30 * (int(listOfTilesPos[i]) - 201)) % 360
            if count > 6: 
                rotDet = 0
            game.add_tile(listOfTilesPos[i], rotDet, listPlayerHomes[i][0], listPlayerHomes[i][1])
        if not hyperlane5:
            for i in range(len(listOfTilesPos) - count):
                rotDet = (180 - 30 * (int(listOfTilesPos[5 - i]) - 201)) % 360
                if count > 6: 
                    rotDet = 0
                game.add_tile(listOfTilesPos[len(listOfTilesPos)-1 - i], rotDet, listDefended[i])
        for i in range(101, 107):
            if hyperlane5 and i == 104:
                continue
            if hyperlane5 and count == 4 and i == 101:
                continue
            game.add_tile(str(i), 0, "sector1back")
        for i in range(201, 213):
            if hyperlane5 and (i == 206 or i == 207):
                continue
            if hyperlane5 and count == 4 and (i == 211 or i == 212):
                continue
            if str(i) not in listOfTilesPos:
                game.add_tile(str(i), 0, "sector2back")
        for i in range(301, 319):
            if hyperlane5 and (i == 309 or i == 310 or i == 311):
                continue
            if hyperlane5 and count == 4 and (i == 301 or i == 302 or i ==318):
                continue
            if str(i) not in listOfTilesPos:
                game.add_tile(str(i), 0, "sector3back")
        if count > 6:
            for i in range(401,425):
                game.add_tile(str(i), 0, "sector3back")
        if game.gamestate["setup_finished"] != 1:
            game.setup_finished()
        # game.fillInDiscTiles()
        await interaction.channel.send("Done With Setup!")

        # Community Empires: Eridani drafts 2 minor species at game start
        if game.gamestate.get("community_empires", False):
            eridani_player_id = None
            for player_id in game.gamestate["players"]:
                player = game.get_player(int(player_id), interaction)
                if player and player.get("name") == "Eridani Empire":
                    eridani_player_id = int(player_id)
                    break
            
            if eridani_player_id is not None:
                eridani_player = game.get_player(eridani_player_id, interaction)
                await DraftButtons.startEridaniMinorSpeciesDraft(game, eridani_player, interaction, temp_player_list)
                # Wait for draft to complete before starting the game
                return

        asyncio.create_task(game.showUpdate("Start of Game", interaction))
        view = TurnButtons.getStartTurnButtons(game, game.get_player(temp_player_list[0],interaction), "dummy")
        game.initilizeKey("activePlayerColor")
        game.addToKey("activePlayerColor", game.get_player(temp_player_list[0],interaction)["color"])
        game.updatePingTime()
        player = game.get_player(temp_player_list[0],interaction)
        await interaction.channel.send(f"## {game.getPlayerEmoji(player)} started their turn.")
        await interaction.channel.send(f"{player['player_name']} use these buttons to do your turn"
                                       + game.displayPlayerStats(player), view=view)
