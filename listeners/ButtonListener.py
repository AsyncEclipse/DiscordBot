import asyncio
from datetime import datetime
import discord
from discord.ext import commands
from Buttons.BlackHole import BlackHoleButtons
from Buttons.Build import BuildButtons
from Buttons.DiplomaticRelations import DiplomaticRelationsButtons
from Buttons.DiscoveryTile import DiscoveryTileButtons
from Buttons.Draft import DraftButtons
from Buttons.Explore import ExploreButtons
from Buttons.Influence import InfluenceButtons
from Buttons.Move import MoveButtons
from Buttons.Population import PopulationButtons
from Buttons.Pulsar import PulsarButtons
from Buttons.Research import ResearchButtons
from Buttons.Shrine import ShrineButtons
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
    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.type == discord.InteractionType.component:
            start = datetime.now()
#            start_time = time.perf_counter()
            logging.basicConfig(level=logging.INFO)
            logger = logging.getLogger(__name__)
            log_channel = discord.utils.get(interaction.guild.channels, name="bot-log")
            button_log_channel = discord.utils.get(interaction.guild.channels, name="button-log")
            customID = interaction.data["custom_id"]
            if button_log_channel is not None and isinstance(button_log_channel, discord.TextChannel):
                await button_log_channel.send(f"{start.strftime('%H:%M:%S')} {customID} pressed:"
                                              f" {interaction.message.jump_url}")

            try:
                await interaction.response.defer(thinking=False)
                if customID == "showGame":
                    await interaction.followup.send("Show game request received,"
                                                    " please wait 5-10 seconds for the map to generate",
                                                    ephemeral=True)

                await asyncio.create_task(self.resolveButton(interaction))
#                if button_log_channel is not None and isinstance(button_log_channel, discord.TextChannel):
#                    end_time = time.perf_counter()
#                    elapsed_time = end_time - start_time
#                    print(f"Total elapsed time for {customID} button press in main thread:
#                          f" {elapsed_time:.2f} seconds")
            except Exception as error:
                if log_channel is not None and isinstance(log_channel, discord.TextChannel):
                    tb = traceback.format_exc()  # Get the traceback as a string

                # Enhanced error logging including traceback
                    log_message = (
                        f"## Error in button interaction:\n"
                        f"- User: {interaction.user} \n"
                        f"- Channel: {interaction.message.jump_url}\n"
                        f"- Component Custom ID: {interaction.data.get('custom_id', 'N/A')}\n"
                        f"- Traceback:"
                    )
                    try:
                        if isinstance(error, discord.HTTPException) and error.status == 404:
                            await log_channel.send(f"Unknown Interaction error on {customID}. "
                                                   "Interaction was receieved at {start.strftime('%H:%M:%S')}")
                            if button_log_channel is not None and isinstance(button_log_channel, discord.TextChannel):
                                await button_log_channel.send(f"{start.strftime('%H:%M:%S')}"
                                                              " interaction errror hit on {customID}")
                        else:
                            await log_channel.send(log_message)
                            while tb:
                                if len(tb) < 1980:
                                    await log_channel.send("```python\n" + tb + "\n```")
                                    tb = ""
                                else:
                                    newline = tb.rfind("\n", 0, 1980)
                                    await log_channel.send("```python\n" + tb[:newline] + "\n```")
                                    tb = tb[newline+1:]

                    except discord.Forbidden:
                        logger.warning("Cannot send messages to the log channel `#bot-log`. Check permissions.")
                    except discord.HTTPException as e:
                        logger.error(f'Failed to send message to log channel: {e}')
                if isinstance(error, discord.HTTPException) and error.status == 404:
                    await interaction.channel.send("The bot was busy handling another request. Try again")
                else:
                    await interaction.channel.send("This button press hit some sort of new error. "
                                                   "Devs will probably need to fix it later. "
                                                   "Please press this button no more than twice in the meantime.")

    async def resolveButton(self, interaction: discord.Interaction):
        customID = interaction.data["custom_id"]
        start_time = time.perf_counter()
        game = GamestateHelper(interaction.channel)
        player = game.get_player(interaction.user.id)
        if player is not None:
            player_helper = PlayerHelper(interaction.user.id, player)
        else:
            player_helper = None
        if game.gamestate.get("lastButton") == customID:
            if not any(substring in customID for substring in ["showGame", "AtRatio", "gain5", "showReputation",
                                                               "rollDice", "magColShip", "rerollDie"]):
                await interaction.followup.send(f"{interaction.user.mention}, this button ({customID}) was pressed"
                                                " most recently, and we are attempting to prevent an accidental"
                                                " double press. Try hitting show game first and then hitting this"
                                                " button, if for some reason you need to press this button.",
                                                ephemeral=True)
                return
        game.saveLastButtonPressed(customID)
        # If we want to prevent others from touching someone else's buttons,
        # we can attach FCID{color}_ to the start of the button ID as a check.
        # We then remove this check so it doesnt interfere with the rest of the resolution.
        if player is not None:
            if customID.startswith("FCID"):
                check = customID.split("_")[0]
                if player["color"] != check.replace("FCID", "") and "dummy" != check.replace("FCID", ""):
                    await interaction.followup.send(interaction.user.mention + ", these buttons are not for you.",
                                                    ephemeral=True)
                    return
                customID = customID.replace(check+"_", "")

        if "deleteMsg" in customID:
            await interaction.message.delete()
        if customID == "showGame":
            await TurnButtons.showGame(game, interaction)
        if player is None:
            return
        if customID.startswith("tradeAtRatio"):
            await TurnButtons.tradeAtRatio(game, player, player_helper, interaction, customID)
        if customID == "showReputation":
            await TurnButtons.showReputation(game, interaction, player)
        if customID == "passForRound":
            game.updateSaveFile()
            await TurnButtons.passForRound(player, game, interaction, player_helper)
        if customID == "permanentlyPass":
            await TurnButtons.permanentlyPass(player, game, interaction, player_helper)
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
        if customID.startswith("finishAction"):
            await TurnButtons.finishAction(player, game, interaction, player_helper)
        if customID.startswith("magColShipForResource"):
            await TurnButtons.magColShipForResource(game, interaction, player, customID, player_helper)
        if customID.startswith("magColShipForSpentResource"):
            await TurnButtons.magColShipForSpentResource(game, interaction, player, customID, player_helper)
        if customID.startswith("startExplore"):
            if "2" not in customID:
                game.updateSaveFile()
            await ExploreButtons.startExplore(game, player, player_helper, interaction, customID)
        if customID.startswith("exploreTile"):
            await ExploreButtons.exploreTile(game, player, interaction, customID)
        if customID.startswith("placeTile"):
            await ExploreButtons.placeTile(game, interaction, player, customID, player_helper)
        if customID.startswith("discardTile"):
            await ExploreButtons.discardTile(game, interaction, player, customID)
        if customID.startswith("keepDiscForPoints"):
            await DiscoveryTileButtons.keepDiscForPoints(game, player_helper, interaction)
        if customID.startswith("exploreDiscoveryTile"):
            await DiscoveryTileButtons.exploreDiscoveryTile(game, customID.split("_")[1], interaction, player)
        if customID.startswith("usedDiscForAbility"):
            await DiscoveryTileButtons.usedDiscForAbility(game, player_helper, interaction, customID, player)
        if customID.startswith("getFreeTech"):
            await DiscoveryTileButtons.getFreeTech(game, interaction, customID, player)
        if customID.startswith("startResearch"):
            game.updateSaveFile()
            await ResearchButtons.startResearch(game, player, player_helper, interaction, True)
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
            await BuildButtons.startBuild(game, player, interaction, customID, player_helper)
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
            await UpgradeButtons.startUpgrade(game, player, interaction, True, "dummy")
        if customID.startswith("upgradeShip"):
            await UpgradeButtons.upgradeShip(game, player, interaction, customID, player_helper)
        if customID.startswith("selectOldPart"):
            await UpgradeButtons.selectOldPart(game, player, interaction, customID, player_helper)
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
            await InfluenceButtons.addInfluenceFinish(game, player, interaction, customID)
        if customID.startswith("removeInfluenceStart"):
            await InfluenceButtons.removeInfluenceStart(game, player, interaction)
        if customID.startswith("removeInfluenceFinish"):
            await InfluenceButtons.removeInfluenceFinish(game, interaction, customID, True)
        if customID.startswith("addCubeToTrack"):
            await InfluenceButtons.addCubeToTrack(game, player, interaction, customID)
        if customID.startswith("refreshPopShips"):
            await InfluenceButtons.refreshPopShips(game, player, interaction, customID)
        if customID.startswith("finishInfluenceAction"):
            await InfluenceButtons.finishInfluenceAction(game, player, interaction, player_helper)
        if customID.startswith("startDiplomaticRelations"):
            game.updateSaveFile()
            await DiplomaticRelationsButtons.startDiplomaticRelations(game, player, interaction)
        if customID.startswith("startMinorRelations"):
            await DiplomaticRelationsButtons.startMinorRelations(game, player, interaction)
        if customID.startswith("offerRelationsTo"):
            await DiplomaticRelationsButtons.offerRelationsTo(game, player, interaction, customID)
        if customID.startswith("declineRelationsWith"):
            await DiplomaticRelationsButtons.declineRelationsWith(game, player, interaction, customID)
        if customID.startswith("acceptRelationsWith"):
            await DiplomaticRelationsButtons.acceptRelationsWith(game, player, interaction, customID)
        if customID.startswith("formMinorRelations"):
            await DiplomaticRelationsButtons.formMinorRelations(game, player, interaction, customID, player_helper)
        if customID.startswith("reducePopFor"):
            await DiplomaticRelationsButtons.reducePopFor(game, player_helper, interaction, customID)
        if customID.startswith("startMove"):
            if customID == "startMove":
                game.updateSaveFile()
            await MoveButtons.startMove(game, player, interaction, customID, True)
        if customID.startswith("moveFrom"):
            await MoveButtons.moveFrom(game, player, interaction, customID)
        if customID.startswith("moveThisShip"):
            await MoveButtons.moveThisShip(game, player, interaction, customID)
        if customID.startswith("moveTo"):
            await MoveButtons.moveTo(game, player, interaction, customID, player_helper)
        if customID.startswith("endGame"):
            await game.endGame(interaction)
        if customID.startswith("declareWinner"):
            await game.declareWinner(interaction)
        if customID.startswith("rollDice"):
            await Combat.rollDice(game, customID, interaction)
        if customID.startswith("rerollDie"):
            await Combat.rerollDie(game, customID, interaction, player, player_helper)
        if customID.startswith("refreshImage"):
            await Combat.refreshImage(game, customID, interaction)
        if customID.startswith("removeUnits"):
            await Combat.removeUnits(game, customID, player, interaction)
        if customID.startswith("assignHitTo"):
            await Combat.assignHitTo(game, customID, interaction, True)
        if customID.startswith("drawReputation"):
            await Combat.drawReputation(game, customID, interaction, player_helper)
        if customID.startswith("removeThisUnit"):
            await Combat.removeThisUnit(game, customID, player, interaction)
        if customID.startswith("startToRetreatUnits"):
            await Combat.startToRetreatUnits(game, customID, interaction)
        if customID.startswith("finishRetreatingUnits"):
            await Combat.finishRetreatingUnits(game, customID, interaction, player)
        if customID.startswith("killPop"):
            await Combat.killPop(game, customID, interaction, player)
        if customID.startswith("placeShrineInitial"):
            await ShrineButtons.placeShrineInitial(game, player, interaction, customID)
        if customID.startswith("placeShrineFinal"):
            await ShrineButtons.placeShrineFinal(game, player, interaction, customID, player_helper)
        if customID.startswith("draftFaction"):
            await DraftButtons.draftFaction(game, interaction, customID)
        if customID.startswith("pulsarAction"):
            game.updateSaveFile()
            await PulsarButtons.pulsarAction(game, player, interaction, player_helper, customID)
        if customID.startswith("blackHoleReturnStart"):
            await BlackHoleButtons.blackHoleReturnStart(game, player, customID, player_helper, interaction)
        if customID.startswith("blackHoleFinish"):
            await BlackHoleButtons.blackHoleFinish(game, player, customID, player_helper, interaction)
        end_time = time.perf_counter()
        elapsed_time = end_time - start_time
        if elapsed_time > 5:
            print(f"Total elapsed time for {customID} button press in side thread: {elapsed_time:.2f} seconds")
