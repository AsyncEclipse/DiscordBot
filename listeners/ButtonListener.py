import discord
from discord.ext import commands
from Buttons.Build import BuildButtons
from Buttons.DiplomaticRelations import DiplomaticRelationsButtons
from Buttons.DiscoveryTile import DiscoveryTileButtons
from Buttons.Explore import ExploreButtons
from Buttons.Influence import InfluenceButtons
from Buttons.Move import MoveButtons
from Buttons.Population import PopulationButtons
from Buttons.Research import ResearchButtons
from Buttons.Turn import TurnButtons
from Buttons.Upgrade import UpgradeButtons
from helpers.CombatHelper import Combat
from helpers.GamestateHelper import GamestateHelper
import time 
import logging
import traceback

from helpers.PlayerHelper import PlayerHelper

class ButtonListener(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_interaction(self, interaction : discord.Interaction):
        if interaction.type == discord.InteractionType.component:
            logging.basicConfig(level=logging.INFO)  
            logger = logging.getLogger(__name__)  
            log_channel = discord.utils.get(interaction.guild.channels, name="bot-log") 
            button_log_channel = discord.utils.get(interaction.guild.channels, name="button-log") 
            try:
                customID = interaction.data["custom_id"]
                if button_log_channel is not None and isinstance(button_log_channel, discord.TextChannel):  
                    await button_log_channel.send(f'{customID} pressed: '+interaction.message.jump_url) 
                await interaction.response.defer(thinking=False)
                start_time = time.perf_counter()  
                game = GamestateHelper(interaction.channel)
                player = game.get_player(interaction.user.id)  
                if player != None:
                    player_helper = PlayerHelper(interaction.user.id, player)
                else:
                    player_helper = None
                if "lastButton" in game.gamestate and game.gamestate["lastButton"] == customID:
                    if not any(substring in customID for substring in ["showGame", "AtRatio", "gain5", "showReputation", "rollDice"]):  
                        await interaction.followup.send(interaction.user.mention+" This button ("+customID+") was pressed most recently, and we are attempting to prevent an accidental double press. Try hitting show game first and then hitting this button, if for some reason you need to press this button", ephemeral=True)
                        return
                game.saveLastButtonPressed(customID)
                # If we want to prevent others from touching someone else's buttons, we can attach FCID{color}_ to the start of the button ID as a check.
                # We then remove this check so it doesnt interfere with the rest of the resolution
                if player != None:
                    if customID.startswith("FCID"):
                        check = customID.split("_")[0]
                        if player["color"] != check.replace("FCID",""):
                            await interaction.followup.send(interaction.user.mention+" These buttons are not for you.", ephemeral=True)
                            return
                        customID = customID.replace(check+"_","")
                
                 
                if "deleteMsg" in customID:
                    await interaction.message.delete()
                if customID == "showGame":  
                    await TurnButtons.showGame(game, interaction)
                if player == None:
                    return
                if customID.startswith("tradeAtRatio"):
                    await TurnButtons.tradeAtRatio(game, player, player_helper, interaction, customID)
                if customID == "showReputation":  
                    await TurnButtons.showReputation(game, interaction,player)
                if customID == "passForRound":
                    game.updateSaveFile()
                    await TurnButtons.passForRound(player, game, interaction,player_helper)
                if customID == "permanentlyPass":
                    await TurnButtons.permanentlyPass(player, game, interaction,player_helper)
                if customID == "endTurn":
                    await TurnButtons.endTurn(player, game, interaction)
                if customID == "restartTurn":
                    await TurnButtons.restartTurn(player, game, interaction)
                if customID == "undoLastTurn":
                    await TurnButtons.undoLastTurn(player, game, interaction)
                if customID == "runUpkeep":
                    game.createRoundNum()
                    round = game.get_gamestate()["roundNum"]
                    await TurnButtons.runUpkeep(game, interaction)
                    game.updateSaveFile()
                    round2 = game.get_gamestate()["roundNum"]
                    if round != round2:
                        await interaction.message.delete()
                if customID.startswith("startExplore"):
                    if "2" not in customID:
                        game.updateSaveFile()
                    await ExploreButtons.startExplore(game, player, player_helper, interaction,customID)
                if customID.startswith("exploreTile"):
                    await ExploreButtons.exploreTile(game, player, interaction, customID)
                if customID.startswith("placeTile"):
                    await ExploreButtons.placeTile(game,  interaction, player, customID,player_helper)
                if customID.startswith("discardTile"):
                    await ExploreButtons.discardTile(game, interaction, player, customID)
                if customID.startswith("keepDiscForPoints"):
                    await DiscoveryTileButtons.keepDiscForPoints(game, player_helper, interaction)
                if customID.startswith("exploreDiscoveryTile"):
                    await DiscoveryTileButtons.exploreDiscoveryTile(game, customID.split("_")[1], interaction, player)
                if customID.startswith("usedDiscForAbility"):
                    await DiscoveryTileButtons.usedDiscForAbility(game, player_helper, interaction, customID,player)
                if customID.startswith("getFreeTech"):
                    await DiscoveryTileButtons.getFreeTech(game, interaction, customID)
                if customID.startswith("startResearch"):
                    game.updateSaveFile()
                    await ResearchButtons.startResearch(game, player, player_helper, interaction,True)
                if customID.startswith("getTech"):
                    await ResearchButtons.getTech(game, player, player_helper, interaction, customID)
                if customID.startswith("placeWarpPortal"):
                    await ResearchButtons.placeWarpPortal(interaction, game, player, customID)
                if customID.startswith("payAtRatio"):
                    await ResearchButtons.payAtRatio(game, player, player_helper, interaction, customID)
                if customID.startswith("gain5resource"):
                    await ResearchButtons.gain5resource(game, player, player_helper, interaction, customID)
                if customID.startswith("gain3resource"):
                    await ResearchButtons.gain3resource(game, player, player_helper, interaction, customID)
                if customID.startswith("startBuild"):
                    if "2" not in customID:
                        game.updateSaveFile()
                    await BuildButtons.startBuild(game, player, interaction,customID,player_helper)
                if customID.startswith("buildIn"):
                    await BuildButtons.buildIn(game, player, interaction, customID)
                if customID.startswith("buildShip"):
                    await BuildButtons.buildShip(game, player, interaction, customID)
                if customID.startswith("spendMaterial"):
                    await BuildButtons.spendMaterial(game, player, interaction, customID)
                if customID.startswith("convertResource"):
                    await BuildButtons.convertResource(game, player, interaction, customID)
                if customID.startswith("finishBuild"):
                    await BuildButtons.finishBuild(game, player, interaction, customID)
                if customID.startswith("finishSpendForBuild"):
                    await BuildButtons.finishSpendForBuild(game, player, interaction, customID, player_helper)
                if customID.startswith("startUpgrade"):
                    game.updateSaveFile()
                    await UpgradeButtons.startUpgrade(game, player, interaction, True,"dummy")
                if customID.startswith("upgradeShip"):
                    await UpgradeButtons.upgradeShip(game, player, interaction, customID, player_helper)
                if customID.startswith("selectOldPart"):
                    await UpgradeButtons.selectOldPart(game, player, interaction, customID,player_helper)
                if customID.startswith("chooseUpgrade"):
                    await UpgradeButtons.chooseUpgrade(game, player, interaction, customID, player_helper)
                if customID.startswith("startPopDrop"):
                    await PopulationButtons.startPopDrop(game, player, interaction)
                if customID.startswith("fillPopulation"):
                    await PopulationButtons.fillPopulation(game, player, interaction, customID)
                if customID.startswith("startInfluence"):
                    game.updateSaveFile()
                    await InfluenceButtons.startInfluence(game, player, interaction)
                if customID.startswith("addInfluenceStart"):
                    await InfluenceButtons.addInfluenceStart(game, player, interaction)
                if customID.startswith("addInfluenceFinish"):
                    await InfluenceButtons.addInfluenceFinish(game, player, interaction,customID)
                if customID.startswith("removeInfluenceStart"):
                    await InfluenceButtons.removeInfluenceStart(game, player, interaction)
                if customID.startswith("removeInfluenceFinish"):
                    await InfluenceButtons.removeInfluenceFinish(game, interaction,customID, True)
                if customID.startswith("addCubeToTrack"):
                    await InfluenceButtons.addCubeToTrack(game, player, interaction,customID)
                if customID.startswith("refreshPopShips"):
                    await InfluenceButtons.refreshPopShips(game, player, interaction, customID)
                if customID.startswith("finishInfluenceAction"):
                    await InfluenceButtons.finishInfluenceAction(game, player, interaction,player_helper)
                if customID.startswith("startDiplomaticRelations"):
                    await DiplomaticRelationsButtons.startDiplomaticRelations(game, player, interaction)
                if customID.startswith("offerRelationsTo"):
                    await DiplomaticRelationsButtons.offerRelationsTo(game, player, interaction,customID)
                if customID.startswith("declineRelationsWith"):
                    await DiplomaticRelationsButtons.declineRelationsWith(game, player, interaction,customID)
                if customID.startswith("acceptRelationsWith"):
                    await DiplomaticRelationsButtons.acceptRelationsWith(game, player, interaction,customID)
                if customID.startswith("reducePopFor"):
                    await DiplomaticRelationsButtons.reducePopFor(game, player_helper, interaction,customID)
                if customID.startswith("startMove"):
                    if customID == "startMove":
                        game.updateSaveFile()
                    await MoveButtons.startMove(game, player, interaction,customID, True)
                if customID.startswith("moveFrom"):
                    await MoveButtons.moveFrom(game, player, interaction,customID)
                if customID.startswith("moveThisShip"):
                    await MoveButtons.moveThisShip(game, player, interaction,customID)
                if customID.startswith("moveTo"):
                    await MoveButtons.moveTo(game, player, interaction,customID,player_helper)
                if customID.startswith("endGame"):
                    await game.endGame(interaction)
                if customID.startswith("declareWinner"):
                    await game.declareWinner(interaction)
                if customID.startswith("rollDice"):
                    await Combat.rollDice(game, customID,interaction)
                if customID.startswith("refreshImage"):
                    await Combat.refreshImage(game, customID,interaction)
                if customID.startswith("removeUnits"):
                    await Combat.removeUnits(game, customID,player, interaction)
                if customID.startswith("assignHitTo"):
                    await Combat.assignHitTo(game, customID, interaction, True)
                if customID.startswith("drawReputation"):
                    await Combat.drawReputation(game, customID, interaction,player_helper)
                if customID.startswith("removeThisUnit"):
                    await Combat.removeThisUnit(game, customID,player, interaction)
                if customID.startswith("startToRetreatUnits"):
                    await Combat.startToRetreatUnits(game, customID, interaction)
                if customID.startswith("finishRetreatingUnits"):
                    await Combat.finishRetreatingUnits(game, customID, interaction)
                if customID.startswith("killPop"):
                    await Combat.killPop(game, customID, interaction,player)
                end_time = time.perf_counter()  
                elapsed_time = end_time - start_time  
                if(elapsed_time > 2):
                    print(f"Total elapsed time for {customID} button press: {elapsed_time:.2f} seconds")  
                if customID.startswith("finishAction"):
                    await TurnButtons.finishAction(player, game, interaction)
            except Exception as error:
                if log_channel is not None and isinstance(log_channel, discord.TextChannel):  
                    tb = traceback.format_exc()  # Get the traceback as a string  

                # Enhanced error logging including traceback  
                    log_message = (  
                        f"## Error in button interaction:\n"  
                        f"- User: {interaction.user} \n"  
                        f"- Channel: {interaction.message.jump_url}\n"  
                        f"- Component Custom ID: {interaction.data['custom_id'] if 'custom_id' in interaction.data else 'N/A'}\n"  
                        f"- Traceback:\n{tb}" 
                    )  
                    try:  
                        if isinstance(error, discord.HTTPException) and error.status == 404:  
                            await log_channel.send("Hit the unknown interaction error")
                        else:
                            await log_channel.send(log_message)  
                    except discord.Forbidden:  
                        logger.warning(f'Cannot send messages to the log channel "bot-log". Check permissions.')  
                    except discord.HTTPException as e:  
                        logger.error(f'Failed to send message to log channel: {e}')  
                if isinstance(error, discord.HTTPException) and error.status == 404:  
                    logger.error(f'Unknown Interaction error: {error}')  
                    await interaction.channel.send("The bot was busy handling another request. Try again")
                else:
                    await interaction.channel.send("This button press hit some sort of new error. Devs will probably need to fix it later")