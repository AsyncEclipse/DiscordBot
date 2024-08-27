import discord
from Buttons.Population import PopulationButtons
from helpers.GamestateHelper import GamestateHelper
from helpers.PlayerHelper import PlayerHelper
from helpers.DrawHelper import DrawHelper
from discord.ui import View, Button

class TurnButtons:




    @staticmethod
    def noOneElsePassed(player, game: GamestateHelper):
        for p2 in game.get_gamestate()["players"]:
            if "passed" in game.get_gamestate()["players"][p2] and game.get_gamestate()["players"][p2]["passed"] == False:
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
    async def restartTurn(player, game, interaction: discord.Interaction):
        view = TurnButtons.getStartTurnButtons(game, player)
        await interaction.response.send_message(player["player_name"]+ " use buttons to do your turn",view=view)
        await interaction.message.delete()



    @staticmethod
    async def endTurn(player, game:GamestateHelper, interaction: discord.Interaction):
        nextPlayer = game.get_next_player(player)
        if nextPlayer != None and not game.is_everyone_passed():
            view = TurnButtons.getStartTurnButtons(game,nextPlayer)
            await interaction.response.send_message(nextPlayer["player_name"]+ " use buttons to do your turn",view=view)
        else:
            await interaction.response.send_message("All players have passed")
        await interaction.message.delete()
        await game.showUpdate(f"End of {interaction.user.name}'s turn",interaction)


    @staticmethod
    async def passForRound(player, game: GamestateHelper, interaction: discord.Interaction, player_helper : PlayerHelper):
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
        player_helper.passTurn()
        game.update_player(player_helper)
        nextPlayer = game.get_next_player(player)
        if nextPlayer != None and not game.is_everyone_passed():
            view = TurnButtons.getStartTurnButtons(game,nextPlayer)
            await interaction.response.send_message(nextPlayer["player_name"]+ " use buttons to do your turn",view=view)

            view2 = View()
            view2.add_item(Button(label=f"Permanently Pass", style=discord.ButtonStyle.green, custom_id="permanentlyPass"))
            await interaction.followup.send(interaction.user.mention+ " you can use this button to permanently pass on reactions if you want.",view=view2,ephemeral=True)
        else:
            view = View()
            view.add_item(Button(label="Run Cleanup",style=discord.ButtonStyle.primary, custom_id="runCleanup"))
            await interaction.response.send_message("All players have passed, you can use this button to start the next round after all battles are resolved", view=view)
        await interaction.message.delete()
        await game.showUpdate(f"{interaction.user.name} Passing",interaction)


    @staticmethod
    async def permanentlyPass(player, game: GamestateHelper, interaction: discord.Interaction, player_helper : PlayerHelper):
        player_helper.permanentlyPassTurn()
        game.update_player(player_helper)
        await interaction.response.edit_message(content="You permanently passed", view=None)

    @staticmethod
    async def runCleanup(game: GamestateHelper, interaction: discord.Interaction):
        game.cleanUp()
        nextPlayer = TurnButtons.getFirstPlayer(game)
        if nextPlayer != None:
            view = TurnButtons.getStartTurnButtons(game,nextPlayer)
            await interaction.response.send_message(nextPlayer["player_name"]+ " use buttons to do the first turn of the round",view=view)
        else:
            await interaction.response.send_message("Could not find first player, someone run /player start_turn")


    @staticmethod
    async def showReputation(game: GamestateHelper,interaction: discord.Interaction, player):
        msg = f"{interaction.user.mention} Your reputation tiles hold the following values: "
        for reputation in player["reputation_track"]:
            if reputation != "mixed" and reputation != "amb":
                msg = msg + str(reputation)+" "

        await interaction.response.send_message(msg,ephemeral=True)
    @staticmethod
    async def showGame(game: GamestateHelper, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True,ephemeral=True,)
        drawing = DrawHelper(game.gamestate)
        view = View()
        view.add_item(Button(label="Show Game",style=discord.ButtonStyle.primary, custom_id="showGame"))
        view.add_item(Button(label="Show Reputation",style=discord.ButtonStyle.gray, custom_id="showReputation"))
        await interaction.followup.send(file=drawing.show_game(),ephemeral=True, view=view)

    @staticmethod
    def getStartTurnButtons(game: GamestateHelper,p1):
        view = View()
        if "passed" in p1 and p1["passed"]== True:
            view.add_item(Button(label=f"Build (1)", style=discord.ButtonStyle.success, custom_id="startBuild"))
            view.add_item(Button(label=f"Upgrade (1)", style=discord.ButtonStyle.primary, custom_id="startUpgrade"))
            view.add_item(Button(label=f"Move (1)", style=discord.ButtonStyle.success, custom_id="startMove"))
        else:
            view.add_item(Button(label=f"Explore ({p1['explore_apt']})", style=discord.ButtonStyle.success, custom_id="startExplore"))
            view.add_item(Button(label=f"Research ({p1['research_apt']})", style=discord.ButtonStyle.primary, custom_id="startResearch"))
            view.add_item(Button(label=f"Build ({p1['build_apt']})", style=discord.ButtonStyle.success, custom_id="startBuild"))
            view.add_item(Button(label=f"Upgrade ({p1['upgrade_apt']})", style=discord.ButtonStyle.primary, custom_id="startUpgrade"))
            view.add_item(Button(label=f"Move ({p1['move_apt']})", style=discord.ButtonStyle.success, custom_id="startMove"))
            view.add_item(Button(label=f"Influence ({p1['influence_apt']})", style=discord.ButtonStyle.secondary, custom_id="startInfluence"))
            view.add_item(Button(label="Pass", style=discord.ButtonStyle.red, custom_id=f"FCID{p1['color']}_passForRound"))
        view.add_item(Button(label="Show Game",style=discord.ButtonStyle.gray, custom_id="showGame"))
        view.add_item(Button(label="Show Reputation",style=discord.ButtonStyle.gray, custom_id="showReputation"))
        if len(PopulationButtons.findEmptyPopulation(game,p1)) > 0 and p1["colony_ships"] > 0:
            view.add_item(Button(label="Put Down Population", style=discord.ButtonStyle.gray, custom_id=f"FCID{p1['color']}_startPopDrop"))
        return view