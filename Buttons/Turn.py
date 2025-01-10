import discord
from Buttons.BlackHole import BlackHoleButtons
from Buttons.DiplomaticRelations import DiplomaticRelationsButtons
from Buttons.Explore import ExploreButtons
from Buttons.Population import PopulationButtons
from Buttons.Pulsar import PulsarButtons
from helpers.EmojiHelper import Emoji
from helpers.GamestateHelper import GamestateHelper
from helpers.PlayerHelper import PlayerHelper
from helpers.DrawHelper import DrawHelper
from discord.ui import View, Button
import asyncio


class TurnButtons:

    @staticmethod
    def noOneElsePassed(player, game: GamestateHelper):
        for p2 in game.gamestate["players"]:
            if game.gamestate["players"][p2].get("eliminated"):
                continue
            if game.gamestate["players"][p2].get("passed"):
                return False
        return True

    @staticmethod
    def getFirstPlayer(game: GamestateHelper):
        listHS = [201, 203, 205, 207, 209, 211]
        if game.gamestate["player_count"] > 6:
                listHS = [302,304,306,308,310,312,314,316,318]
        for number in listHS:
            nextPlayer = game.getPlayerFromHSLocation(str(number))
            if nextPlayer is not None and game.gamestate["players"].get(nextPlayer, {}).get("firstPlayer", False):
                return game.gamestate["players"][nextPlayer]
        return None

    @staticmethod
    async def restartTurn(player, game: GamestateHelper, interaction: discord.Interaction):
        try:
            await interaction.message.delete()
            game.backUpToLastSaveFile()
            game.release_lock()
            game = GamestateHelper(interaction.channel)
            player = game.get_player(interaction.user.id,interaction)
            view = TurnButtons.getStartTurnButtons(game, player, "dummy")
            game.saveLastButtonPressed("restart")
            await interaction.channel.send(player['player_name'] + " has chosen to back up to last start of turn.")
            await interaction.channel.send(player["player_name"] + " use buttons to do your turn"
                                           + game.displayPlayerStats(player), view=view)
        except discord.NotFound:
            await interaction.channel.send("Ignoring double press")
            # Avoid a double backup by deleting the message first and doing nothing if it was already deleted

    @staticmethod
    async def endTurn(player, game: GamestateHelper, interaction: discord.Interaction):
        from helpers.CombatHelper import Combat
        nextPlayer = game.get_next_player(player)
        await game.updateNamesAndOutRimTiles(interaction)
        game.initilizeKey("20MinReminder")
        if nextPlayer is not None and not game.is_everyone_passed():
            view = TurnButtons.getStartTurnButtons(game, nextPlayer, player["color"])
            game.initilizeKey("activePlayerColor")
            game.addToKey("activePlayerColor", nextPlayer["color"])
            game.updatePingTime()
            await interaction.channel.send("## " + game.getPlayerEmoji(nextPlayer) + " started their turn")
            await interaction.channel.send(f"{nextPlayer['player_name']} use buttons to do your turn"
                                           + game.displayPlayerStats(nextPlayer), view=view)
        else:
            view = View()
            role = discord.utils.get(interaction.guild.roles, name=game.game_id)
            msg = f"{role.mention}, all players have passed, you may use this button to start the next round"
            if any([len(Combat.findTilesInConflict(game)) > 0,
                    len(Combat.findUnownedTilesToTakeOver(game)) > 0,
                    len(Combat.findTilesInContention(game)) > 0]):
                Combat.startCombatThreads(game, interaction)
                msg += " after all battles are resolved"
            view.add_item(Button(label="Put Down Population", style=discord.ButtonStyle.gray,
                                 custom_id="startPopDrop"))
            if game.gamestate["player_count"] > 3:
                view.add_item(Button(label="Initiate Diplomatic Relations", style=discord.ButtonStyle.gray,
                                    custom_id=f"startDiplomaticRelations"))
            if "minor_species" in game.gamestate and len(game.gamestate["minor_species"]) > 0:
                view.add_item(Button(label="Minor Species Relations", style=discord.ButtonStyle.green,
                                    custom_id=f"startMinorRelations"))
            view.add_item(Button(label="Run Upkeep", style=discord.ButtonStyle.blurple, custom_id="runUpkeep"))
            asyncio.create_task(interaction.channel.send(msg + ".", view=view))
        userN = interaction.user.display_name
        if "username" in player:
            userN =player['username']
        msg = f"End of {userN}'s turn."
        if "lastAction" in player and "detailsOflastAction" in player:
            msg = (f"End of {userN}'s turn. "
                   f"They used their action to {player['lastAction']}. {player['detailsOflastAction']}")
        asyncio.create_task(interaction.message.delete())
        if "-" in interaction.channel.name:
            thread_name = interaction.channel.name.split("-")[0] + "-bot-map-updates"
            thread = discord.utils.get(interaction.channel.threads, name=thread_name)
            if thread is not None:
                asyncio.create_task(game.showGame(thread, msg))
        # print(f"Total elapsed time for non-update part of endTurn: {elapsed_time:.2f} seconds")

    @staticmethod
    async def passForRound(player, game: GamestateHelper, interaction: discord.Interaction,
                           player_helper: PlayerHelper):
        from helpers.CombatHelper import Combat
        if player.get("passed"):
            await interaction.channel.send(f"{player['player_name']} passed on their reaction window.")
        else:

            if TurnButtons.noOneElsePassed(player, game):
                player_helper.adjust_money(2)
                await interaction.channel.send(f"{player['player_name']} you gained 2 money"
                                               " and the first player marker for next round for passing first.")
                player_helper.setFirstPlayer(True)
                for p2 in game.gamestate["players"]:
                    if game.gamestate["players"][p2]["color"] == player["color"]:
                        continue
                    if game.gamestate["players"][p2].get("eliminated"):
                        continue
                    player_helper2 = PlayerHelper(p2, game.gamestate["players"][p2])
                    player_helper2.setFirstPlayer(False)
                    game.update_player(player_helper2)
            else:
                await interaction.channel.send(f"{player['player_name']} passed.")
        player_helper.passTurn(True)
        game.update_player(player_helper)
        nextPlayer = game.get_next_player(player)
        game.addToPassOrder(player["player_name"])
        sendPermaPassButton = False
        if nextPlayer is not None and not game.is_everyone_passed():
            view = TurnButtons.getStartTurnButtons(game, nextPlayer, player["color"])
            game.initilizeKey("activePlayerColor")
            game.addToKey("activePlayerColor", nextPlayer["color"])
            game.updatePingTime()
            await interaction.channel.send("## " + game.getPlayerEmoji(nextPlayer) + " started their turn")
            await interaction.channel.send(nextPlayer["player_name"] + " use buttons to do your turn"
                                           + game.displayPlayerStats(nextPlayer), view=view)
            sendPermaPassButton = True
            
        else:
            view = View()
            role = discord.utils.get(interaction.guild.roles, name=game.game_id)
            msg = f"{role.mention}, all players have passed, you may use this button to start the next round"
            if any([len(Combat.findTilesInConflict(game)) > 0,
                    len(Combat.findUnownedTilesToTakeOver(game)) > 0,
                    len(Combat.findTilesInContention(game)) > 0]):
                await Combat.startCombatThreads(game, interaction)
                msg += " after all battles are resolved"
            view.add_item(Button(label="Put Down Population", style=discord.ButtonStyle.gray,
                                 custom_id="startPopDrop"))
            view.add_item(Button(label="Run Upkeep", style=discord.ButtonStyle.blurple, custom_id="runUpkeep"))
            if game.gamestate["player_count"] > 3:
                view.add_item(Button(label="Initiate Diplomatic Relations", style=discord.ButtonStyle.gray,
                                    custom_id=f"startDiplomaticRelations"))
            if "minor_species" in game.gamestate and len(game.gamestate["minor_species"]) > 0:
                view.add_item(Button(label="Minor Species Relations", style=discord.ButtonStyle.green,
                                    custom_id=f"startMinorRelations"))
            await interaction.channel.send(msg + ".", view=view)
        msg2 = f"{player['username']} Passed"
        await game.updateNamesAndOutRimTiles(interaction)
        await interaction.message.delete()
        if "-" in interaction.channel.name:
            thread_name = interaction.channel.name.split("-")[0] + "-bot-map-updates"
            thread = discord.utils.get(interaction.channel.threads, name=thread_name)
            if thread is not None:
                asyncio.create_task(thread.send(msg2))
        if sendPermaPassButton:
            view2 = View()
            view2.add_item(Button(label="Pass Unless Someone Attacks You",
                                  style=discord.ButtonStyle.green, custom_id="permanentlyPass"))
            await interaction.followup.send(interaction.user.mention + " you may use this button to pass on reactions"
                                            " unless someone invades your systems.", view=view2, ephemeral=True)

    @staticmethod
    async def permanentlyPass(player, game: GamestateHelper, interaction:
                              discord.Interaction, player_helper: PlayerHelper):
        player_helper.permanentlyPassTurn(True)
        game.update_player(player_helper)
        await interaction.followup.send("You passed on reactions as long as noone attacks you", ephemeral=True)

    @staticmethod
    async def tradeAtRatio(game: GamestateHelper, player, player_helper: PlayerHelper,
                           interaction: discord.Interaction,  buttonID: str):
        resource_type = buttonID.split("_")[1]
        resource_type2 = buttonID.split("_")[2]
        trade_value = player["trade_value"]
        if trade_value > player[resource_type]:
            await interaction.channel.send(f"{player['player_name']} does not have enough {resource_type} to trade.")
            return
        msg = player_helper.adjust_resource(resource_type, -trade_value)
        msg2 = player_helper.adjust_resource(resource_type2, 1)
        game.update_player(player_helper)
        await interaction.channel.send(msg)
        await interaction.channel.send(msg2)

    @staticmethod
    async def readyForUpkeep(game: GamestateHelper, player, interaction: discord.Interaction, p1: PlayerHelper):
        color = player["color"]
        game.removeFromKey("peopleToCheckWith", color)
        if p1.checkBankrupt():
            view = View()
            trade_value = p1.stats['trade_value']
            view.add_item(Button(label="Remove Control of A Sector", style=discord.ButtonStyle.blurple,
                                 custom_id=f"FCID{player['color']}_removeInfluenceStart"))
            for resource_type, button_style in [("materials", discord.ButtonStyle.gray),
                                                ("science", discord.ButtonStyle.gray)]:
                if p1.stats[resource_type] >= trade_value:
                    view.add_item(Button(label=f"Trade {trade_value} {resource_type.capitalize()}",
                                         style=button_style,
                                         custom_id=f"FCID{p1.stats['color']}_tradeAtRatio_{resource_type}_money"))
            if p1.stats["colony_ships"] > 0 and game.get_short_faction_name(p1.stats["name"]) == "magellan":
                emojiC = Emoji.getEmojiByName("colony_ship")
                view.add_item(Button(label="Get 1 Money", style=discord.ButtonStyle.red, emoji=emojiC,
                                     custom_id=f"FCID{p1.stats['color']}_magColShipForResource_money"))
            view.add_item(Button(label="Done Resolving", style=discord.ButtonStyle.red,
                                 custom_id=f"FCID{player['color']}_deleteMsg"))
            message = (f"It appears that {p1.name} would be bankrupt (negative money). "
                       f"They currently have {p1.stats['money']} money and will get {p1.money_income()} in income, "
                       f"but they owe {p1.upkeepCosts()} money. "
                       "Please adjust the money or systems controlled so that upkeep"
                       " can be run without the player entering negative money")
            await interaction.channel.send(message, view=view)
        msg = f"{player['player_name']} has marked themselves as ready for upkeep."
        if len(game.gamestate["peopleToCheckWith"]) > 0:
            msg += " Still waiting on the following factions to press the ready for upkeep button:\n"
            for color2 in game.gamestate["peopleToCheckWith"]:
                p2 = game.getPlayerObjectFromColor(color2)
                msg += p2["player_name"]+"\n"
            await interaction.channel.send(msg)
        else:
            view = View()
            view.add_item(Button(label="Run Upkeep", style=discord.ButtonStyle.blurple, custom_id="runUpkeep"))
            msg += " Everyone is now ready for upkeep, please press the button"
            await interaction.channel.send(msg, view=view)

    @staticmethod
    async def runUpkeep(game: GamestateHelper, interaction: discord.Interaction):
        from helpers.CombatHelper import Combat
        if len(Combat.findTilesInConflict(game)) > 0:
            await interaction.channel.send("It appears some tiles are still in conflict. "
                                           "Please resolve them before running upkeep")
            return
        if "peopleToCheckWith" in game.gamestate and len(game.gamestate["peopleToCheckWith"]) > 0:
            msg = " Still waiting on the following players to hit the ready for upkeep button:\n"
            for color2 in game.gamestate["peopleToCheckWith"]:
                p2 = game.getPlayerObjectFromColor(color2)
                msg += p2["player_name"]+"\n"
            await interaction.channel.send(msg)
            return
        for player in game.gamestate["players"]:
            if game.gamestate["players"][player].get("eliminated"):
                continue
            p1 = PlayerHelper(player, game.get_player(player))
            if p1.checkBankrupt():
                view = View()
                trade_value = p1.stats['trade_value']
                view.add_item(Button(label="Remove Control of A Sector", style=discord.ButtonStyle.blurple,
                                     custom_id=f"FCID{p1.stats['color']}_removeInfluenceStart"))
                for resource_type, button_style in [("materials", discord.ButtonStyle.gray),
                                                    ("science", discord.ButtonStyle.gray)]:
                    if p1.stats[resource_type] >= trade_value:
                        view.add_item(Button(label=f"Trade {trade_value} {resource_type.capitalize()}",
                                             style=button_style,
                                             custom_id=f"FCID{p1.stats['color']}_tradeAtRatio_{resource_type}_money"))
                if p1.stats["colony_ships"] > 0 and game.get_short_faction_name(p1.stats["name"]) == "magellan":
                    emojiC = Emoji.getEmojiByName("colony_ship")
                    view.add_item(Button(label="Get 1 Money", style=discord.ButtonStyle.red, emoji=emojiC,
                                         custom_id=f"FCID{p1.stats['color']}_magColShipForResource_money"))
                view.add_item(Button(label="Done Resolving", style=discord.ButtonStyle.red,
                                     custom_id=f"FCID{game.get_player(player)['color']}_deleteMsg"))
                message = (f"It appears that {p1.name} would be bankrupt (negative money). "
                           f"They currently have {p1.stats['money']} money and will get {p1.money_income()} in income, "
                           f"but they owe {p1.upkeepCosts()} money. "
                           "Please adjust the money or systems controlled so that upkeep"
                           " can be run without the player entering negative money")
                await interaction.channel.send(message, view=view)
                return
        if "actions" in interaction.channel.name:
            for thread in interaction.channel.threads:
                if "Round" in thread.name:
                    asyncio.create_task(thread.edit(archived=True))
        await game.upkeep(interaction)
        drawing = DrawHelper(game.gamestate)
        if game.gamestate["roundNum"] < 9:
            await interaction.channel.send(f"Tech Available At Start Of Round {game.gamestate['roundNum']}",
                                           file=await asyncio.to_thread(drawing.show_available_techs))
            nextPlayer = TurnButtons.getFirstPlayer(game)
            if nextPlayer is not None:
                view = TurnButtons.getStartTurnButtons(game, nextPlayer, "dummy")
                game.initilizeKey("activePlayerColor")
                game.addToKey("activePlayerColor", nextPlayer["color"])
                game.updatePingTime()
                await interaction.channel.send("## " + game.getPlayerEmoji(nextPlayer) + " started their turn")
                message = (f"{nextPlayer['player_name']} use buttons to do the first turn of the round" +
                           game.displayPlayerStats(nextPlayer))
                await interaction.channel.send(message, view=view)
            else:
                await interaction.channel.send("Could not find first player, someone run /player start_turn")
        else:
            view = View()
            view.add_item(Button(label="Declare Winner", style=discord.ButtonStyle.blurple, custom_id="declareWinner"))
            await interaction.channel.send("It seems like the game should be ended, "
                                           "hit this button to reveal the winner.", view=view)
        asyncio.create_task(game.showUpdate(f"Start of round {str(game.gamestate['roundNum'])}", interaction))

    @staticmethod
    async def showReputation(game: GamestateHelper, interaction: discord.Interaction, player):
        msg = f"{interaction.user.mention} Your reputation tiles hold the following values: "
        for reputation in player["reputation_track"]:
            if reputation != "mixed" and reputation != "amb" and isinstance(reputation, int):
                msg += str(reputation) + " "

        await interaction.followup.send(msg, ephemeral=True)

    @staticmethod
    async def send_files(interaction, files, view, ephemeralStatus):
        for file in files:
            message = await interaction.followup.send(file=file, ephemeral=ephemeralStatus, view=view)
            image_url = message.attachments[0].url
            button = discord.ui.Button(label="View Full Image", url=image_url)
            view = discord.ui.View()
            view.add_item(button)
            await interaction.followup.send(view=view, ephemeral=ephemeralStatus)

    @staticmethod
    async def send_file(interaction, file):
        await interaction.followup.send(file=file, ephemeral=True)

    @staticmethod
    async def showGame(game: GamestateHelper, interaction: discord.Interaction):
        await game.updateNamesAndOutRimTiles(interaction)
        await TurnButtons.showGameAsync(game, interaction, True)

    @staticmethod
    async def showGameAsync(game: GamestateHelper, interaction: discord.Interaction, ephemeralStatus):
        drawing = DrawHelper(game.gamestate)
        map = await asyncio.to_thread(drawing.show_game)
        view = View()
        button = Button(label="Show Game", style=discord.ButtonStyle.blurple, custom_id="showGame")
        view.add_item(button)
        view.add_item(Button(label="Show Reputation", style=discord.ButtonStyle.gray, custom_id="showReputation"))
        await TurnButtons.send_files(interaction, [map], view, ephemeralStatus)

    @staticmethod
    def getStartTurnButtons(game: GamestateHelper, p1, lastPlayerColor):
        view = View()
        player = p1
        player_helper = PlayerHelper(game.getPlayersID(player), player)
        number_passed = 0
        ordinal = lambda n: "tsnrhtdd"[(n//10%10!=1)*(n%10<4)*n%10::4]  # noqa
        for p2 in game.gamestate["players"]:
            if game.gamestate["players"][p2].get("passed"):
                number_passed += 1
        if player["influence_discs"] != 0:
            if p1.get("passed"):
                view.add_item(Button(label="Build (1)", style=discord.ButtonStyle.green,
                                     custom_id=f"FCID{player['color']}_startBuild"))
                view.add_item(Button(label="Upgrade (1)", style=discord.ButtonStyle.blurple,
                                     custom_id=f"FCID{player['color']}_startUpgrade"))
                view.add_item(Button(label="Move (1)", style=discord.ButtonStyle.green,
                                     custom_id=f"FCID{player['color']}_startMove"))
                view.add_item(Button(label="Pass On Reaction", style=discord.ButtonStyle.red,
                                     custom_id=f"FCID{p1['color']}_passForRound"))
            else:
                if len(ExploreButtons.getTilesToExplore(game, player)) > 0:
                    view.add_item(Button(label=f"Explore ({p1['explore_apt']})", style=discord.ButtonStyle.green,
                                         custom_id=f"FCID{player['color']}_startExplore"))
                view.add_item(Button(label=f"Research ({p1['research_apt']})", style=discord.ButtonStyle.blurple,
                                     custom_id=f"FCID{player['color']}_startResearch"))
                view.add_item(Button(label=f"Build ({p1['build_apt']})", style=discord.ButtonStyle.green,
                                     custom_id=f"FCID{player['color']}_startBuild"))
                view.add_item(Button(label=f"Upgrade ({p1['upgrade_apt']})", style=discord.ButtonStyle.blurple,
                                     custom_id=f"FCID{player['color']}_startUpgrade"))
                view.add_item(Button(label=f"Move ({p1['move_apt']})", style=discord.ButtonStyle.green,
                                     custom_id=f"FCID{player['color']}_startMove"))
                view.add_item(Button(label=f"Influence ({p1['influence_apt']})", style=discord.ButtonStyle.gray,
                                     custom_id=f"FCID{player['color']}_startInfluence"))
                view.add_item(Button(label=f"Pass ({number_passed + 1}{ordinal(number_passed + 1)})",
                                     style=discord.ButtonStyle.red, custom_id=f"FCID{p1['color']}_passForRound"))
        else:
            if p1.get("passed"):
                view.add_item(Button(label="Pass On Reaction", style=discord.ButtonStyle.red,
                                     custom_id=f"FCID{p1['color']}_passForRound"))
            else:
                view.add_item(Button(label=f"Pass ({number_passed + 1}{ordinal(number_passed + 1)})",
                                     style=discord.ButtonStyle.red, custom_id=f"FCID{p1['color']}_passForRound"))
        if not p1.get("passed"):
            pulsarView = PulsarButtons.findPulsarOptions(game, p1)
            for child in pulsarView.children:
                view.add_item(child)
        view.add_item(Button(label="Show Game", style=discord.ButtonStyle.gray, custom_id="showGame"))
        view.add_item(Button(label="Show Reputation", style=discord.ButtonStyle.gray, custom_id="showReputation"))
        if p1["colony_ships"] > 0 and game.get_short_faction_name(p1["name"]) == "magellan":
            emojiC = Emoji.getEmojiByName("colony_ship")
            view.add_item(Button(label="Get 1 Science", style=discord.ButtonStyle.red, emoji=emojiC,
                                 custom_id=f"FCID{player['color']}_magColShipForResource_science"))
            view.add_item(Button(label="Get 1 Money", style=discord.ButtonStyle.green, emoji=emojiC,
                                 custom_id=f"FCID{player['color']}_magColShipForResource_money"))
            view.add_item(Button(label="Get 1 Material", style=discord.ButtonStyle.blurple, emoji=emojiC,
                                 custom_id=f"FCID{p1['color']}_magColShipForResource_materials"))
        if len(PopulationButtons.findEmptyPopulation(game, p1)) > 0 and p1["colony_ships"] > 0:
            view.add_item(Button(label="Put Down Population", style=discord.ButtonStyle.gray,
                                 custom_id=f"FCID{p1['color']}_startPopDrop"))
        blackView = BlackHoleButtons.getBlackHoleShips(game, player)
        for child in blackView.children:
            view.add_item(child)
        if all([game.gamestate["player_count"] > 3, not player_helper.isTraitor(),
                len(DiplomaticRelationsButtons.getPlayersWithWhichDiplomatcRelationsCanBeFormed(game, player)) > 0]):
            view.add_item(Button(label="Initiate Diplomatic Relations", style=discord.ButtonStyle.gray,
                                 custom_id=f"FCID{p1['color']}_startDiplomaticRelations"))
        if not player_helper.isTraitor() and len(game.gamestate.get("minor_species", [])) > 0:
            view.add_item(Button(label="Minor Species Relations", style=discord.ButtonStyle.green,
                                 custom_id=f"FCID{p1['color']}_startMinorRelations"))
        if game.getNumberOfSaveFiles() > 0:
            view.add_item(Button(label="Undo Last Turn", style=discord.ButtonStyle.red,
                                 custom_id=f"FCID{lastPlayerColor}_undoLastTurn"))
        return view

    @staticmethod
    async def magColShipForResource(game: GamestateHelper, interaction: discord.Interaction,
                                    player, buttonID, player_helper: PlayerHelper):
        resource = buttonID.split("_")[1]
        if player["colony_ships"] < 1:
            await interaction.followup.send("You do not have enough color ships for this.")
            return
        ships = player_helper.adjust_colony_ships(1)
        message = (f"{player['player_name']} exhausted 1 colony ship to get 1 {resource}. "
                   f"They have {ships} colony ship{'s' if ships == 1 else ''} left."
                   + player_helper.adjust_resource(resource, 1))
        await interaction.channel.send(message)
        game.update_player(player_helper)

    @staticmethod
    async def magColShipForSpentResource(game: GamestateHelper, interaction: discord.Interaction,
                                         player, buttonID, player_helper: PlayerHelper):
        resource = buttonID.split("_")[1]
        if player["colony_ships"] < 1:
            await interaction.followup.send("You do not have enough color ships for this.")
            return
        ships = player_helper.adjust_colony_ships(1)
        message = (f"{player['player_name']} exhausted 1 colony ship to get and then immediately spend 1 {resource}. "
                   f"They have {ships} colony ship{'s' if ships == 1 else ''} left.")
        await interaction.channel.send(message)
        game.update_player(player_helper)

    @staticmethod
    async def undoLastTurn(player, game: GamestateHelper, interaction: discord.Interaction):
        view = View()
        await interaction.message.delete()
        view.add_item(Button(label="Undo Last Turn", style=discord.ButtonStyle.red, custom_id="restartTurn"))
        view.add_item(Button(label="Delete This Message", style=discord.ButtonStyle.gray, custom_id="deleteMsg"))
        await interaction.channel.send("Please confirm you want to undo the last turn. "
                                       "The person who took the last turn should be the one pressing this button",
                                       view=view)

    @staticmethod
    async def checkTraitor(game: GamestateHelper, player, interaction: discord.Interaction, player_helper: PlayerHelper):
        for destination in game.gamestate["board"]:
            playerPresent = False
            if "player_ships" not in game.gamestate["board"][destination]:
                continue
            for ship in game.gamestate["board"][destination]["player_ships"]:
                if "orb" in ship or "mon" in ship:
                    continue
                if player['color'] in ship:
                    playerPresent = True
            if playerPresent:
                repTrack = player["reputation_track"][:]
                for tile in repTrack:
                    if isinstance(tile, str) and "-" in tile and "minor" not in tile:
                        color = tile.split("-")[2]
                        p2 = game.getPlayerObjectFromColor(color)
                        broken = False
                        if destination in p2["owned_tiles"]:
                            broken = True
                        for ship in game.gamestate["board"][destination]["player_ships"]:
                            if "orb" in ship or "mon" in ship:
                                continue
                            if color in ship:
                                broken = True
                        if broken:
                            await DiplomaticRelationsButtons.breakRelationsWith(game, player, p2, interaction)
                            game.makeEveryoneNotTraitor()
                            player_helper.setTraitor(True)
                            game.update_player(player_helper)
                            await interaction.channel.send(f"{player['player_name']}, you broke relations with {color}"
                                                        " and now are the Traitor.")
                            




    @staticmethod
    async def finishAction(player, game: GamestateHelper, interaction: discord.Interaction,
                           player_helper: PlayerHelper):
        await TurnButtons.checkTraitor(game, player, interaction, player_helper)
        view = View()
        view.add_item(Button(label="End Turn", style=discord.ButtonStyle.red,
                             custom_id=f"FCID{player['color']}_endTurn"))
        if len(PopulationButtons.findEmptyPopulation(game, player)) > 0 and player["colony_ships"] > 0:
            view.add_item(Button(label="Put Down Population", style=discord.ButtonStyle.gray,
                                 custom_id=f"FCID{player['color']}_startPopDrop"))
        if player["colony_ships"] > 0 and game.get_short_faction_name(player["name"]) == "magellan":
            emojiC = Emoji.getEmojiByName("colony_ship")
            view.add_item(Button(label="Get 1 Science", style=discord.ButtonStyle.red, emoji=emojiC,
                                 custom_id=f"FCID{player['color']}_magColShipForResource_science"))
            view.add_item(Button(label="Get 1 Money", style=discord.ButtonStyle.green, emoji=emojiC,
                                 custom_id=f"FCID{player['color']}_magColShipForResource_money"))
            view.add_item(Button(label="Get 1 Material", style=discord.ButtonStyle.blurple, emoji=emojiC,
                                 custom_id=f"FCID{player['color']}_magColShipForResource_materials"))
        if all([game.gamestate["player_count"] > 3,
                not player_helper.isTraitor(),
                len(DiplomaticRelationsButtons.getPlayersWithWhichDiplomatcRelationsCanBeFormed(game, player)) > 0]):
            view.add_item(Button(label="Initiate Diplomatic Relations", style=discord.ButtonStyle.gray,
                                 custom_id=f"FCID{player['color']}_startDiplomaticRelations"))
        if "minor_species" in game.gamestate:
            if all([not player_helper.isTraitor(),
                    len(game.gamestate["minor_species"]) > 0]):
                view.add_item(Button(label="Minor Species Relations", style=discord.ButtonStyle.green,
                                     custom_id=f"FCID{player['color']}_startMinorRelations"))
        view.add_item(Button(label="Restart Turn", style=discord.ButtonStyle.gray,
                             custom_id=f"FCID{player['color']}_restartTurn"))
        await interaction.channel.send(f"Colony ships available: {player['colony_ships']}\n"
                                       "Do any end of turn abilities and then end your turn.", view=view)
        game.initilizeKey("20MinReminder")
        game.addToKey("20MinReminder",player["color"])
        await interaction.message.delete()
