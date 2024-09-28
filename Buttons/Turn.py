import discord
from Buttons.Population import PopulationButtons
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
        game.backUpToLastSaveFile()
        game = GamestateHelper(interaction.channel)
        view = TurnButtons.getStartTurnButtons(game, player)
        await interaction.channel.send(interaction.user.mention+" has chosen to back up to last start of turn.")
        await interaction.channel.send(player["player_name"]+ " use buttons to do your turn"+ game.displayPlayerStats(player),view=view)
        await interaction.message.delete()
        



    @staticmethod
    async def endTurn(player, game:GamestateHelper, interaction: discord.Interaction, bot):
        nextPlayer = game.get_next_player(player)
        if nextPlayer != None and not game.is_everyone_passed():
            view = TurnButtons.getStartTurnButtons(game,nextPlayer)
            await interaction.channel.send(nextPlayer["player_name"]+ " use buttons to do your turn"+ game.displayPlayerStats(nextPlayer),view=view)
        else:
            await interaction.channel.send("All players have passed")
        await interaction.message.delete()
        await game.showUpdate(f"End of {interaction.user.name}'s turn",interaction, bot)


    

    @staticmethod
    async def passForRound(player, game: GamestateHelper, interaction: discord.Interaction, player_helper : PlayerHelper, bot):
        if "passed" in player and player["passed"]== True:
            await interaction.channel.send(f"{interaction.user.mention} passed on their reaction window.")
        else:
            if TurnButtons.noOneElsePassed(player,game):
                player_helper.adjust_money(2)
                await interaction.channel.send(f"{interaction.user.mention} you gained 2 money and the first player marker for next round for passing first")
                player_helper.setFirstPlayer(True)
                for p2 in game.get_gamestate()["players"]:
                    if game.get_gamestate()["players"][p2]["color"] == player["color"]:
                        continue
                    player_helper2 = PlayerHelper(p2, game.get_gamestate()["players"][p2])
                    player_helper2.setFirstPlayer(False)
                    game.update_player(player_helper2)
            else:
                await interaction.channel.send(f"{interaction.user.mention} passed.")
        player_helper.passTurn(True)
        game.update_player(player_helper)
        nextPlayer = game.get_next_player(player)
        if nextPlayer != None and not game.is_everyone_passed():
            view = TurnButtons.getStartTurnButtons(game,nextPlayer)
            await interaction.channel.send(nextPlayer["player_name"]+ " use buttons to do your turn"+ game.displayPlayerStats(nextPlayer),view=view)

            view2 = View()
            view2.add_item(Button(label=f"Permanently Pass", style=discord.ButtonStyle.green, custom_id="permanentlyPass"))
            await interaction.followup.send(interaction.user.mention+ " you can use this button to permanently pass on reactions if you want.",view=view2,ephemeral=True)
        else:
            view = View()
            view.add_item(Button(label="Run Upkeep",style=discord.ButtonStyle.blurple, custom_id="runUpkeep"))
            await interaction.channel.send("All players have passed, you can use this button to start the next round after all battles are resolved", view=view)
        await interaction.message.delete()
        await game.showUpdate(f"{interaction.user.name} Passing",interaction, bot)


    @staticmethod
    async def permanentlyPass(player, game: GamestateHelper, interaction: discord.Interaction, player_helper : PlayerHelper):
        player_helper.permanentlyPassTurn(True)
        game.update_player(player_helper)
        await interaction.followup.send("You permanently passed", ephemeral=True)

    @staticmethod
    async def runUpkeep(game: GamestateHelper, interaction: discord.Interaction,bot):
        for player in game.gamestate["players"]:
            p1 = PlayerHelper(player, game.get_player(player))
            if p1.checkBankrupt():
                await interaction.channel.send("It appears that "+p1.name + " would be bankrupt (negative money). Please adjust the money or systems controlled so that upkeep can be run without the player entering negative money")
                return

        game.upkeep()
        drawing = DrawHelper(game.gamestate)
        if game.gamestate["roundNum"] < 9:
            await interaction.channel.send("Tech At Start Of New Round",file=drawing.show_available_techs())
            nextPlayer = TurnButtons.getFirstPlayer(game)
            if nextPlayer != None:
                view = TurnButtons.getStartTurnButtons(game,nextPlayer)
                await interaction.channel.send(nextPlayer["player_name"]+ " use buttons to do the first turn of the round"+game.displayPlayerStats(nextPlayer),view=view)
            else:
                await interaction.channel.send("Could not find first player, someone run /player start_turn")
        else:
            view = View()
            view.add_item(Button(label="End Game",style=discord.ButtonStyle.blurple, custom_id="endGame"))
            await interaction.channel.send("It seems like the game should be ended, hit this button to cleanup the channels.", view=view)
        await game.showUpdate(f"Start of new round",interaction, bot)


    @staticmethod
    async def showReputation(game: GamestateHelper,interaction: discord.Interaction, player):
        msg = f"{interaction.user.mention} Your reputation tiles hold the following values: "
        for reputation in player["reputation_track"]:
            if reputation != "mixed" and reputation != "amb" and isinstance(reputation, int):
                msg = msg + str(reputation)+" "

        await interaction.followup.send(msg,ephemeral=True)
    @staticmethod
    async def send_files(interaction, files):
        for file in files:
            await interaction.followup.send(file=file,ephemeral=True)

    @staticmethod
    async def send_file(interaction, file):
        await interaction.followup.send(file=file,ephemeral=True)

    @staticmethod
    async def showGame(game: GamestateHelper, interaction: discord.Interaction, bot):
        game.updateNamesAndOutRimTiles(interaction)
        drawing = DrawHelper(game.gamestate)
        view = View()
        view.add_item(Button(label="Show Game",style=discord.ButtonStyle.blurple, custom_id="showGame"))
        view.add_item(Button(label="Show Reputation",style=discord.ButtonStyle.gray, custom_id="showReputation"))
        map = drawing.show_map()
        stats = drawing.show_stats()
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(asyncio.run_coroutine_threadsafe, TurnButtons.send_files(interaction, [map,stats]),bot.loop)

    @staticmethod
    def getStartTurnButtons(game: GamestateHelper,p1):
        view = View()
        player = p1
        player_helper = PlayerHelper(game.getPlayersID(player), player)
        if "passed" in p1 and p1["passed"]== True:
            view.add_item(Button(label=f"Build (1)", style=discord.ButtonStyle.green, custom_id=f"FCID{player['color']}_startBuild"))
            view.add_item(Button(label=f"Upgrade (1)", style=discord.ButtonStyle.blurple, custom_id=f"FCID{player['color']}_startUpgrade"))
            view.add_item(Button(label=f"Move (1)", style=discord.ButtonStyle.green, custom_id=f"FCID{player['color']}_startMove"))
            view.add_item(Button(label="Pass On Reaction", style=discord.ButtonStyle.red, custom_id=f"FCID{p1['color']}_passForRound"))
        else:
            view.add_item(Button(label=f"Explore ({p1['explore_apt']})", style=discord.ButtonStyle.green, custom_id=f"FCID{player['color']}_startExplore"))
            view.add_item(Button(label=f"Research ({p1['research_apt']})", style=discord.ButtonStyle.blurple, custom_id=f"FCID{player['color']}_startResearch"))
            view.add_item(Button(label=f"Build ({p1['build_apt']})", style=discord.ButtonStyle.green, custom_id=f"FCID{player['color']}_startBuild"))
            view.add_item(Button(label=f"Upgrade ({p1['upgrade_apt']})", style=discord.ButtonStyle.blurple, custom_id=f"FCID{player['color']}_startUpgrade"))
            view.add_item(Button(label=f"Move ({p1['move_apt']})", style=discord.ButtonStyle.green, custom_id=f"FCID{player['color']}_startMove"))
            view.add_item(Button(label=f"Influence ({p1['influence_apt']})", style=discord.ButtonStyle.gray, custom_id=f"FCID{player['color']}_startInfluence"))
            view.add_item(Button(label="Pass", style=discord.ButtonStyle.red, custom_id=f"FCID{p1['color']}_passForRound"))
        view.add_item(Button(label="Show Game",style=discord.ButtonStyle.gray, custom_id="showGame"))
        view.add_item(Button(label="Show Reputation",style=discord.ButtonStyle.gray, custom_id="showReputation"))
        if len(PopulationButtons.findEmptyPopulation(game,p1)) > 0 and p1["colony_ships"] > 0:
            view.add_item(Button(label="Put Down Population", style=discord.ButtonStyle.gray, custom_id=f"FCID{p1['color']}_startPopDrop"))
        if game.get_gamestate()["player_count"] > 3 and not player_helper.isTraitor():
            view.add_item(Button(label="Initiate Diplomatic Relations", style=discord.ButtonStyle.gray, custom_id=f"FCID{p1['color']}_startDiplomaticRelations"))
        if game.getNumberOfSaveFiles() > 0:
            view.add_item(Button(label="Undo Last Turn", style=discord.ButtonStyle.red, custom_id=f"undoLastTurn"))
        return view

    @staticmethod
    async def undoLastTurn(player, game:GamestateHelper, interaction: discord.Interaction):
        view = View()
        view.add_item(Button(label="Undo Last Turn", style=discord.ButtonStyle.red, custom_id=f"restartTurn"))
        view.add_item(Button(label="Delete This Message", style=discord.ButtonStyle.gray, custom_id=f"deleteMsg"))
        await interaction.channel.send("Please confirm you want to undo the last turn. The person who took the last turn should be the one pressing this button",view=view)

    @staticmethod
    async def finishAction(player, game:GamestateHelper, interaction: discord.Interaction):
        view = View()
        view.add_item(Button(label="End Turn", style=discord.ButtonStyle.red, custom_id=f"FCID{player['color']}_endTurn"))
        if len(PopulationButtons.findEmptyPopulation(game, player)) > 0 and player["colony_ships"] > 0:
            view.add_item(Button(label="Put Down Population", style=discord.ButtonStyle.gray, custom_id=f"FCID{player['color']}_startPopDrop"))
        await interaction.channel.send(f"Colony ships available: {player['colony_ships']}"
                                                f"\nPlace population or end your turn.", view=view)
        await interaction.message.delete()