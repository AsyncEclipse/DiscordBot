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
import concurrent.futures
import time
import asyncio
class TurnButtons:

    @staticmethod
    def noOneElsePassed(player, game: GamestateHelper):
        for p2 in game.get_gamestate()["players"]:
            if "passed" in game.get_gamestate()["players"][p2] and game.get_gamestate()["players"][p2]["passed"] == True:
                return False
        return True


    @staticmethod
    def getFirstPlayer(game: GamestateHelper):
        listHS = [201,203,205,207,209,211]
        for number in listHS:
            nextPlayer = game.getPlayerFromHSLocation(str(number))
            if nextPlayer is not None and game.get_gamestate()["players"].get(nextPlayer, {}).get("firstPlayer", False):
                return game.get_gamestate()["players"][nextPlayer]
        return None

    @staticmethod
    async def restartTurn(player, game:GamestateHelper, interaction: discord.Interaction):
        try:  
            await interaction.message.delete()  
            game.backUpToLastSaveFile()
            game = GamestateHelper(interaction.channel)
            player = game.get_player(interaction.user.id)  
            view = TurnButtons.getStartTurnButtons(game, player)
            game.saveLastButtonPressed("restart")
            await interaction.channel.send(player['player_name']+" has chosen to back up to last start of turn.")
            await interaction.channel.send(player["player_name"]+ " use buttons to do your turn"+ game.displayPlayerStats(player),view=view)
        except discord.NotFound: 
            await interaction.channel.send("Ignoring double press")
            # Avoid a double backup by deleting the message first and doing nothing if it was already deleted
        
        



    @staticmethod
    async def endTurn(player, game:GamestateHelper, interaction: discord.Interaction):
        from helpers.CombatHelper import Combat
        start_time = time.perf_counter()
        nextPlayer = game.get_next_player(player)
        if nextPlayer != None and not game.is_everyone_passed():
            view = TurnButtons.getStartTurnButtons(game,nextPlayer)
            game.initilizeKey("activePlayerColor")
            game.addToKey("activePlayerColor",nextPlayer["color"])
            await interaction.channel.send("## "+game.getPlayerEmoji(nextPlayer)+" started their turn")
            await interaction.channel.send(nextPlayer["player_name"]+ " use buttons to do your turn"+ game.displayPlayerStats(nextPlayer),view=view)
        else:
            view = View()
            role = discord.utils.get(interaction.guild.roles, name=game.game_id)  
            msg = role.mention+" All players have passed, you can use this button to start the next round"
            if len(Combat.findTilesInConflict(game))+ len(Combat.findUnownedTilesToTakeOver(game)) + len(Combat.findTilesInContention(game)) > 0:
                asyncio.create_task(Combat.startCombatThreads(game, interaction))
                msg = msg +  " after all battles are resolved"
            view.add_item(Button(label="Put Down Population", style=discord.ButtonStyle.gray, custom_id=f"startPopDrop"))
            view.add_item(Button(label="Run Upkeep",style=discord.ButtonStyle.blurple, custom_id="runUpkeep"))
            asyncio.create_task(interaction.channel.send(msg, view=view))
        msg = f"End of {interaction.user.name}'s turn."
        if "lastAction" in player and "detailsOflastAction" in player:
            msg = f"End of {interaction.user.name}'s turn. They used their action to "+player["lastAction"]+". "+player["detailsOflastAction"]
        await game.updateNamesAndOutRimTiles(interaction)
        await interaction.message.delete()
        if "-" in interaction.channel.name:
            thread_name = interaction.channel.name.split("-")[0]+"-bot-map-updates"
            thread = discord.utils.get(interaction.channel.threads, name=thread_name) 
            if thread != None:
                asyncio.create_task(game.showGame(thread, msg))
        end_time = time.perf_counter()  
        elapsed_time = end_time - start_time  
        #print(f"Total elapsed time for non-update part of endTurn: {elapsed_time:.2f} seconds")  
        


    

    @staticmethod
    async def passForRound(player, game: GamestateHelper, interaction: discord.Interaction, player_helper : PlayerHelper):
        from helpers.CombatHelper import Combat
        if "passed" in player and player["passed"]== True:
            await interaction.channel.send(f"{player['player_name']} passed on their reaction window.")
        else:

            if TurnButtons.noOneElsePassed(player,game):
                player_helper.adjust_money(2)
                await interaction.channel.send(f"{player['player_name']} you gained 2 money and the first player marker for next round for passing first")
                player_helper.setFirstPlayer(True)
                for p2 in game.get_gamestate()["players"]:
                    if game.get_gamestate()["players"][p2]["color"] == player["color"]:
                        continue
                    player_helper2 = PlayerHelper(p2, game.get_gamestate()["players"][p2])
                    player_helper2.setFirstPlayer(False)
                    game.update_player(player_helper2)
            else:
                await interaction.channel.send(f"{player['player_name']} passed.")
        player_helper.passTurn(True)
        game.update_player(player_helper)
        nextPlayer = game.get_next_player(player)
        game.addToPassOrder(player["player_name"])
        if nextPlayer != None and not game.is_everyone_passed():
            view = TurnButtons.getStartTurnButtons(game,nextPlayer)
            game.initilizeKey("activePlayerColor")
            game.addToKey("activePlayerColor",nextPlayer["color"])
            await interaction.channel.send("## "+game.getPlayerEmoji(nextPlayer)+" started their turn")
            await interaction.channel.send(nextPlayer["player_name"]+ " use buttons to do your turn"+ game.displayPlayerStats(nextPlayer),view=view)

            view2 = View()
            view2.add_item(Button(label=f"Pass Unless Someone Attacks You", style=discord.ButtonStyle.green, custom_id="permanentlyPass"))
            await interaction.followup.send(interaction.user.mention+ " you can use this button to pass on reactions unless someone invades your systems.",view=view2,ephemeral=True)
        else:
            view = View()
            role = discord.utils.get(interaction.guild.roles, name=game.game_id)  
            msg = role.mention+" All players have passed, you can use this button to start the next round"
            if len(Combat.findTilesInConflict(game)) + len(Combat.findUnownedTilesToTakeOver(game))+ len(Combat.findTilesInContention(game))> 0:
                await Combat.startCombatThreads(game, interaction)
                msg = msg +  " after all battles are resolved"
            view.add_item(Button(label="Put Down Population", style=discord.ButtonStyle.gray, custom_id=f"startPopDrop"))
            view.add_item(Button(label="Run Upkeep",style=discord.ButtonStyle.blurple, custom_id="runUpkeep"))
            await interaction.channel.send(msg, view=view)
        msg2 = f"{interaction.user.name} Passing"
        await game.updateNamesAndOutRimTiles(interaction)
        await interaction.message.delete()
        if "-" in interaction.channel.name:
            thread_name = interaction.channel.name.split("-")[0]+"-bot-map-updates"
            thread = discord.utils.get(interaction.channel.threads, name=thread_name) 
            if thread != None:
                asyncio.create_task(game.showGame(thread, msg2))


    @staticmethod
    async def permanentlyPass(player, game: GamestateHelper, interaction: discord.Interaction, player_helper : PlayerHelper):
        player_helper.permanentlyPassTurn(True)
        game.update_player(player_helper)
        await interaction.followup.send("You passed on reactions as long as noone attacks you", ephemeral=True)

    @staticmethod  
    async def tradeAtRatio(game: GamestateHelper, player, player_helper: PlayerHelper, interaction: discord.Interaction,  buttonID:str):
        game = GamestateHelper(interaction.channel)  
        resource_type = buttonID.split("_")[1]
        resource_type2 = buttonID.split("_")[2]
        trade_value = player["trade_value"]
        if trade_value > player[resource_type]:
            await interaction.channel.send(player['player_name'] + " does not have enough "+resource_type +" to trade") 
            return
        msg = player_helper.adjust_resource(resource_type,-trade_value)  
        msg2 = player_helper.adjust_resource(resource_type2, 1) 
        game.update_player(player_helper)  
        await interaction.channel.send(msg)  
        await interaction.channel.send(msg2)


    @staticmethod
    async def runUpkeep(game: GamestateHelper, interaction: discord.Interaction):
        from helpers.CombatHelper import Combat
        if len(Combat.findTilesInConflict(game)) > 0:
            await interaction.channel.send("It appears some tiles are still in conflict. Please resolve them before running upkeep")
            return
        for player in game.gamestate["players"]:
            p1 = PlayerHelper(player, game.get_player(player))
            if p1.checkBankrupt():
                view = View()
                trade_value = p1.stats['trade_value']
                view.add_item(Button(label="Remove Control of A Sector", style=discord.ButtonStyle.blurple, custom_id=f"FCID{game.get_player(player)['color']}_removeInfluenceStart"))
                for resource_type, button_style in [("materials", discord.ButtonStyle.gray),   
                                            ("science", discord.ButtonStyle.gray)]: 
                    if(p1.stats[resource_type] >= trade_value):
                        view.add_item(Button(label=f"Trade {trade_value} {resource_type.capitalize()}",   
                                        style=button_style,   
                                        custom_id=f"FCID{p1.stats['color']}_tradeAtRatio_{resource_type}_money")) 
                if p1.stats["colony_ships"] > 0 and game.get_short_faction_name(p1.stats["name"]) == "magellan":
                    emojiC = Emoji.getEmojiByName("colony_ship")
                    view.add_item(Button(label=f"Get 1 Money", style=discord.ButtonStyle.red, emoji=emojiC, custom_id=f"FCID{p1.stats['color']}_magColShipForResource_money"))
                view.add_item(Button(label="Done Resolving", style=discord.ButtonStyle.red, custom_id=f"FCID{game.get_player(player)['color']}_deleteMsg"))
                await interaction.channel.send("It appears that "+p1.name + " would be bankrupt (negative money). They currently have "+str(p1.stats["money"])+" money and will get "+str(p1.money_income())+" in income, but they owe "+str(p1.upkeepCosts())+" money. Please adjust the money or systems controlled so that upkeep can be run without the player entering negative money", view=view)
                return
        if "actions" in interaction.channel.name:
            for thread in interaction.channel.threads:  
                if "Round" in thread.name:
                    asyncio.create_task(thread.edit(archived=True))
        await game.upkeep(interaction)
        drawing = DrawHelper(game.gamestate)
        if game.gamestate["roundNum"] < 9:
            await interaction.channel.send("Tech At Start Of Round "+str(game.gamestate['roundNum']),file=await asyncio.to_thread(drawing.show_available_techs))
            nextPlayer = TurnButtons.getFirstPlayer(game)
            if nextPlayer != None:
                view = TurnButtons.getStartTurnButtons(game,nextPlayer)
                game.initilizeKey("activePlayerColor")
                game.addToKey("activePlayerColor",nextPlayer["color"])
                await interaction.channel.send("## "+game.getPlayerEmoji(nextPlayer)+" started their turn")
                await interaction.channel.send(nextPlayer["player_name"]+ " use buttons to do the first turn of the round"+game.displayPlayerStats(nextPlayer),view=view)
            else:
                await interaction.channel.send("Could not find first player, someone run /player start_turn")
        else:
            view = View()
            view.add_item(Button(label="Declare Winner",style=discord.ButtonStyle.blurple, custom_id="declareWinner"))
            await interaction.channel.send("It seems like the game should be ended, hit this button to reveal the winner.", view=view)
        asyncio.create_task(game.showUpdate(f"Start of round {str(game.gamestate['roundNum'])}",interaction))


    @staticmethod
    async def showReputation(game: GamestateHelper,interaction: discord.Interaction, player):
        msg = f"{interaction.user.mention} Your reputation tiles hold the following values: "
        for reputation in player["reputation_track"]:
            if reputation != "mixed" and reputation != "amb" and isinstance(reputation, int):
                msg = msg + str(reputation)+" "

        await interaction.followup.send(msg,ephemeral=True)
    @staticmethod
    async def send_files(interaction, files, view, ephemeralStatus):
        for file in files:
            await interaction.followup.send(file=file,ephemeral=ephemeralStatus, view=view)

    @staticmethod
    async def send_file(interaction, file):
        await interaction.followup.send(file=file,ephemeral=True)

    @staticmethod
    async def showGame(game: GamestateHelper, interaction: discord.Interaction):
        await game.updateNamesAndOutRimTiles(interaction)
        await TurnButtons.showGameAsync(game, interaction, True)

    @staticmethod
    async def showGameAsync(game: GamestateHelper, interaction: discord.Interaction, ephemeralStatus):
        drawing = DrawHelper(game.gamestate)
        map = await asyncio.to_thread(drawing.show_game)
        view = View()
        button = Button(label="Show Game",style=discord.ButtonStyle.blurple, custom_id="showGame")
        view.add_item(button)
        view.add_item(Button(label="Show Reputation",style=discord.ButtonStyle.gray, custom_id="showReputation"))
        await TurnButtons.send_files(interaction, [map], view, ephemeralStatus)

    @staticmethod
    def getStartTurnButtons(game: GamestateHelper,p1):
        view = View()
        player = p1
        player_helper = PlayerHelper(game.getPlayersID(player), player)
        number_passed = 0
        ordinal = lambda n: "tsnrhtdd"[(n//10%10!=1)*(n%10<4)*n%10::4]
        for p2 in game.get_gamestate()["players"]:
            if "passed" in game.get_gamestate()["players"][p2] and game.get_gamestate()["players"][p2]["passed"] == True:
                number_passed += 1
        if player["influence_discs"] != 0:
            if "passed" in p1 and p1["passed"]== True:
                view.add_item(Button(label=f"Build (1)", style=discord.ButtonStyle.green, custom_id=f"FCID{player['color']}_startBuild"))
                view.add_item(Button(label=f"Upgrade (1)", style=discord.ButtonStyle.blurple, custom_id=f"FCID{player['color']}_startUpgrade"))
                view.add_item(Button(label=f"Move (1)", style=discord.ButtonStyle.green, custom_id=f"FCID{player['color']}_startMove"))
                view.add_item(Button(label="Pass On Reaction", style=discord.ButtonStyle.red, custom_id=f"FCID{p1['color']}_passForRound"))
            else:
                if len(ExploreButtons.getTilesToExplore(game, player)) > 0:
                    view.add_item(Button(label=f"Explore ({p1['explore_apt']})", style=discord.ButtonStyle.green, custom_id=f"FCID{player['color']}_startExplore"))
                view.add_item(Button(label=f"Research ({p1['research_apt']})", style=discord.ButtonStyle.blurple, custom_id=f"FCID{player['color']}_startResearch"))
                view.add_item(Button(label=f"Build ({p1['build_apt']})", style=discord.ButtonStyle.green, custom_id=f"FCID{player['color']}_startBuild"))
                view.add_item(Button(label=f"Upgrade ({p1['upgrade_apt']})", style=discord.ButtonStyle.blurple, custom_id=f"FCID{player['color']}_startUpgrade"))
                view.add_item(Button(label=f"Move ({p1['move_apt']})", style=discord.ButtonStyle.green, custom_id=f"FCID{player['color']}_startMove"))
                view.add_item(Button(label=f"Influence ({p1['influence_apt']})", style=discord.ButtonStyle.gray, custom_id=f"FCID{player['color']}_startInfluence"))
                view.add_item(Button(label=f"Pass ({number_passed+1}{ordinal(number_passed+1)})", style=discord.ButtonStyle.red, custom_id=f"FCID{p1['color']}_passForRound"))
        else:
            if "passed" in p1 and p1["passed"]== True:
                view.add_item(Button(label="Pass On Reaction", style=discord.ButtonStyle.red, custom_id=f"FCID{p1['color']}_passForRound"))
            else:
                view.add_item(Button(label=f"Pass ({number_passed+1}{ordinal(number_passed+1)})", style=discord.ButtonStyle.red, custom_id=f"FCID{p1['color']}_passForRound"))
        if "passed" not in p1 or  p1["passed"] != True:
            pulsarView = PulsarButtons.findPulsarOptions(game, p1)
            for child in pulsarView.children:
                view.add_item(child)
        view.add_item(Button(label="Show Game",style=discord.ButtonStyle.gray, custom_id="showGame"))
        view.add_item(Button(label="Show Reputation",style=discord.ButtonStyle.gray, custom_id="showReputation"))
        if p1["colony_ships"] > 0 and game.get_short_faction_name(p1["name"]) == "magellan":
            emojiC = Emoji.getEmojiByName("colony_ship")
            view.add_item(Button(label=f"Get 1 Science", style=discord.ButtonStyle.red, emoji=emojiC, custom_id=f"FCID{player['color']}_magColShipForResource_science"))
            view.add_item(Button(label=f"Get 1 Money", style=discord.ButtonStyle.green,emoji=emojiC, custom_id=f"FCID{player['color']}_magColShipForResource_money"))
            view.add_item(Button(label=f"Get 1 Material", style=discord.ButtonStyle.blurple,emoji=emojiC, custom_id=f"FCID{p1['color']}_magColShipForResource_materials"))
        if len(PopulationButtons.findEmptyPopulation(game,p1)) > 0 and p1["colony_ships"] > 0:
            view.add_item(Button(label="Put Down Population", style=discord.ButtonStyle.gray, custom_id=f"FCID{p1['color']}_startPopDrop"))
        blackView = BlackHoleButtons.getBlackHoleShips(game, player)
        for child in blackView.children:
            view.add_item(child)
        if game.get_gamestate()["player_count"] > 3 and not player_helper.isTraitor() and len(DiplomaticRelationsButtons.getPlayersWithWhichDiplomatcRelationsCanBeFormed(game, player)) > 0:
            view.add_item(Button(label="Initiate Diplomatic Relations", style=discord.ButtonStyle.gray, custom_id=f"FCID{p1['color']}_startDiplomaticRelations"))
        if not player_helper.isTraitor() and "minor_species" in game.gamestate and len(game.get_gamestate()["minor_species"]) > 0:
            view.add_item(Button(label="Minor Species Relations", style=discord.ButtonStyle.green, custom_id=f"FCID{p1['color']}_startMinorRelations"))
        if game.getNumberOfSaveFiles() > 0:
            view.add_item(Button(label="Undo Last Turn", style=discord.ButtonStyle.red, custom_id=f"undoLastTurn"))
        return view
    

    @staticmethod
    async def magColShipForResource(game: GamestateHelper, interaction: discord.Interaction,player, buttonID, player_helper :PlayerHelper):
        resource = buttonID.split("_")[1]
        if player["colony_ships"] < 1:
            await interaction.followup.send("You do not have enough color ships for this")
            return
        player_helper.adjust_colony_ships(1)
        await interaction.channel.send(player["player_name"]+ " exhausted 1 colony ship to get 1 "+resource +". They have "+str(player_helper.stats["colony_ships"])+" colony ships left."+player_helper.adjust_resource(resource,1))
        game.update_player(player_helper)


    @staticmethod
    async def undoLastTurn(player, game:GamestateHelper, interaction: discord.Interaction):
        view = View()
        await interaction.message.delete()
        view.add_item(Button(label="Undo Last Turn", style=discord.ButtonStyle.red, custom_id=f"restartTurn"))
        view.add_item(Button(label="Delete This Message", style=discord.ButtonStyle.gray, custom_id=f"deleteMsg"))
        await interaction.channel.send("Please confirm you want to undo the last turn. The person who took the last turn should be the one pressing this button",view=view)

    @staticmethod
    async def finishAction(player, game:GamestateHelper, interaction: discord.Interaction):
        view = View()
        view.add_item(Button(label="End Turn", style=discord.ButtonStyle.red, custom_id=f"FCID{player['color']}_endTurn"))
        if len(PopulationButtons.findEmptyPopulation(game, player)) > 0 and player["colony_ships"] > 0:
            view.add_item(Button(label="Put Down Population", style=discord.ButtonStyle.gray, custom_id=f"FCID{player['color']}_startPopDrop"))
        if player["colony_ships"] > 0 and game.get_short_faction_name(player["name"]) == "magellan":
            emojiC = Emoji.getEmojiByName("colony_ship")
            view.add_item(Button(label=f"Get 1 Science", style=discord.ButtonStyle.red, emoji=emojiC, custom_id=f"FCID{player['color']}_magColShipForResource_science"))
            view.add_item(Button(label=f"Get 1 Money", style=discord.ButtonStyle.green,emoji=emojiC, custom_id=f"FCID{player['color']}_magColShipForResource_money"))
            view.add_item(Button(label=f"Get 1 Material", style=discord.ButtonStyle.blurple,emoji=emojiC, custom_id=f"FCID{player['color']}_magColShipForResource_materials"))
        await interaction.channel.send(f"Colony ships available: {player['colony_ships']}"
                                                f"\nPlace population or end your turn.", view=view)
        await interaction.message.delete()
