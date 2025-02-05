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
            start_time = time.perf_counter()
            logging.basicConfig(level=logging.INFO)
            logger = logging.getLogger(__name__)
            log_channel = discord.utils.get(interaction.guild.channels, name="bot-log")
            button_log_channel = discord.utils.get(interaction.guild.channels, name="button-log")
            customID = interaction.data["custom_id"]
            if button_log_channel is not None and isinstance(button_log_channel, discord.TextChannel):
                asyncio.create_task(button_log_channel.send(f"{start.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]} {customID} pressed:"
                                              f" {interaction.message.jump_url} by {interaction.user.display_name}"))

            try:
                await interaction.response.defer(thinking=False)
                if customID == "showGame":
                    await interaction.followup.send("Show game request received,"
                                                    " please wait 5-10 seconds for the map to generate",
                                                    ephemeral=True)

                await self.resolveButton(interaction)

                if button_log_channel is not None and isinstance(button_log_channel, discord.TextChannel):
                    end_time = time.perf_counter()
                    elapsed_time = end_time - start_time
                    print(f"Total elapsed time for {customID} button press in main thread:{elapsed_time:.2f} seconds")
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
                            asyncio.create_task(log_channel.send(f"Unknown Interaction error on {customID}. "
                                                   f"Interaction was received at {start.strftime('%H:%M:%S')}"))
                            if button_log_channel is not None and isinstance(button_log_channel, discord.TextChannel):
                                await button_log_channel.send(f"{start.strftime('%H:%M:%S')}"
                                                              f" interaction errror hit on {customID}")
                        else:
                            await log_channel.send(log_message)
                            while tb:
                                if len(tb) < 1980:
                                    await log_channel.send("```python\n" + tb + "\n```")
                                    tb = ""
                                else:
                                    newline = tb.rfind("\n", 0, 1980)
                                    await log_channel.send("```python\n" + tb[:newline] + "\n```")
                                    tb = tb[newline + 1:]
                        # game = GamestateHelper(interaction.channel, interaction.channel.name,True)
                        # game.setLockedStatus(False)
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
        userID = interaction.user.id
        player = game.get_player(interaction.user.id,interaction)
        if player == None and game.gamestate.get("communityMode",False):
            member = interaction.guild.get_member(userID) 
            roles = member.roles
            role_names = [role.name for role in roles if role.name != "@everyone"]
            colors = ["blue", "red", "green", "yellow", "purple", "white", "pink", "brown", "teal"]
            for role_name in role_names:
                for color in colors:
                    if color in role_name.lower():
                        player = game.getPlayerObjectFromColor(color)
                        userID = game.get_player_from_color(color)
                        break
                if player != None:
                    break
        if player is not None:
            player_helper = PlayerHelper(userID, player)
        else:
            player_helper = None
        if game.gamestate.get("lastButton") == customID:
            if not any(substring in customID for substring in ["showGame", "AtRatio", "gain5",
                                                               "showReputation", "rollDice", "magColShip",
                                                               "rerollDie", "readyForUpkeep","draftFaction"]):
                await interaction.followup.send(f"{interaction.user.mention}, this button ({customID}) was pressed"
                                                " most recently, and we are attempting to prevent an accidental"
                                                " double press. Try hitting show reputation first and then hitting this"
                                                " button, if for some reason you need to press this button.",
                                                ephemeral=True)
                return

        # if game.gamestate.get("gameLocked") == "yes":
        #     await asyncio.sleep(0.5)
        #     game = GamestateHelper(interaction.channel)
        #     if game.gamestate.get("gameLocked") == "yes":
        #         await interaction.followup.send((f"{interaction.user.mention}, the game was processing"
        #                                         " another request when you hit this button. Try again now"),
        #                                         ephemeral=True)
        #         return
        
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
                customID = customID.replace(check + "_", "")

        if "deleteMsg" in customID:
            await interaction.message.delete()
        if customID == "showGame":
            await TurnButtons.showGame(game, interaction)
            return
        if customID.startswith("refreshImage"):
            await Combat.refreshImage(game, customID, interaction)
            return
        if player is None:
            return
        game.file = game.setLockedStatus(True)
        if game.file == None: 
            await interaction.followup.send((f"{interaction.user.mention}, the game was processing"
                                                " another request when you hit this button. Try again now"),
                                                ephemeral=True)
            return
        game.saveLastButtonPressed(customID)
        if customID.startswith("tradeAtRatio"):
            await TurnButtons.tradeAtRatio(game, player, player_helper, interaction, customID)
        elif customID == "showReputation":
            await TurnButtons.showReputation(game, interaction, player)
        elif customID == "passForRound":
            game.updateSaveFile()
            await TurnButtons.passForRound(player, game, interaction, player_helper)
        elif customID == "permanentlyPass":
            await TurnButtons.permanentlyPass(player, game, interaction, player_helper)
        elif customID == "endTurn":
            await TurnButtons.endTurn(player, game, interaction)
        elif customID == "restartTurn":
            await TurnButtons.restartTurn(player, game, interaction)
        elif customID == "undoLastTurn":
            await TurnButtons.undoLastTurn(player, game, interaction)
        elif customID == "readyForUpkeep":
            await TurnButtons.readyForUpkeep(game, player, interaction, player_helper)
        elif customID == "runUpkeep":
            game.createRoundNum()
            rnd = game.gamestate["roundNum"]
            await TurnButtons.runUpkeep(game, interaction)
            game.updateSaveFile()
            round2 = game.gamestate["roundNum"]
            if rnd != round2:
                await interaction.message.delete()
        elif customID.startswith("finishAction"):
            await TurnButtons.finishAction(player, game, interaction, player_helper)
        elif customID.startswith("magColShipForResource"):
            await TurnButtons.magColShipForResource(game, interaction, player, customID, player_helper)
        elif customID.startswith("magColShipForSpentResource"):
            await TurnButtons.magColShipForSpentResource(game, interaction, player, customID, player_helper)
        elif customID.startswith("startExplore"):
            if "2" not in customID:
                game.updateSaveFile()
            await ExploreButtons.startExplore(game, player, player_helper, interaction, customID)
        elif customID.startswith("exploreTile"):
            await ExploreButtons.exploreTile(game, player, interaction, customID)
        elif customID.startswith("placeTile"):
            await ExploreButtons.placeTile(game, interaction, player, customID, player_helper)
        elif customID.startswith("discardTile"):
            await ExploreButtons.discardTile(game, interaction, player, customID)
        elif customID.startswith("keepDiscForPoints"):
            await DiscoveryTileButtons.keepDiscForPoints(game, player_helper, interaction)
        elif customID.startswith("exploreDiscoveryTile"):
            await DiscoveryTileButtons.exploreDiscoveryTile(game, customID.split("_")[1], interaction, player)
        elif customID.startswith("usedDiscForAbility"):
            await DiscoveryTileButtons.usedDiscForAbility(game, player_helper, interaction, customID, player)
        elif customID.startswith("getFreeTech"):
            await DiscoveryTileButtons.getFreeTech(game, interaction, customID, player)
        elif customID.startswith("startResearch"):
            game.updateSaveFile()
            await ResearchButtons.startResearch(game, player, player_helper, interaction, True)
        elif customID.startswith("getTech"):
            await ResearchButtons.getTech(game, player, player_helper, interaction, customID)
        elif customID.startswith("placeWarpPortal"):
            await ResearchButtons.placeWarpPortal(interaction, game, player, customID)
        elif customID.startswith("payAtRatio"):
            await ResearchButtons.payAtRatio(game, player, player_helper, interaction, customID)
        elif customID.startswith("gain5resource"):
            await ResearchButtons.gain5resource(game, player, player_helper, interaction, customID)
        elif customID.startswith("gain3resource"):
            await ResearchButtons.gain3resource(game, player, player_helper, interaction, customID)
        elif customID.startswith("startBuild"):
            if "2" not in customID:
                game.updateSaveFile()
            await BuildButtons.startBuild(game, player, interaction, customID, player_helper)
        elif customID.startswith("buildIn"):
            await BuildButtons.buildIn(game, player, interaction, customID)
        elif customID.startswith("buildShip"):
            await BuildButtons.buildShip(game, player, interaction, customID)
        elif customID.startswith("spendMaterial"):
            await BuildButtons.spendMaterial(game, player, interaction, customID)
        elif customID.startswith("convertResource"):
            await BuildButtons.convertResource(game, player, interaction, customID)
        elif customID.startswith("finishBuild"):
            await BuildButtons.finishBuild(game, player, interaction, customID)
        elif customID.startswith("finishSpendForBuild"):
            await BuildButtons.finishSpendForBuild(game, player, interaction, customID, player_helper)
        elif customID.startswith("startUpgrade"):
            game.updateSaveFile()
            await UpgradeButtons.startUpgrade(game, player, interaction, True, "dummy","dum")
        elif customID.startswith("chooseDifferentShip"):
            actions = customID.split("_")[1]
            discTile = customID.split("_")[2]
            await interaction.message.delete()
            await UpgradeButtons.startUpgrade(game, player, interaction, False, discTile,actions)
        elif customID.startswith("upgradeShip"):
            await UpgradeButtons.upgradeShip(game, player, interaction, customID, player_helper)
        elif customID.startswith("selectOldPart"):
            await UpgradeButtons.selectOldPart(game, player, interaction, customID, player_helper)
        elif customID.startswith("chooseUpgrade"):
            await UpgradeButtons.chooseUpgrade(game, player, interaction, customID, player_helper)
        elif customID.startswith("startPopDrop"):
            await PopulationButtons.startPopDrop(game, player, interaction)
        elif customID.startswith("fillPopulation"):
            await PopulationButtons.fillPopulation(game, player, interaction, customID)
        elif customID.startswith("startInfluence"):
            game.updateSaveFile()
            await InfluenceButtons.startInfluence(game, player, interaction)
        elif customID.startswith("addInfluenceStart"):
            await InfluenceButtons.addInfluenceStart(game, player, interaction)
        elif customID.startswith("eliminatePlayer"):
            await InfluenceButtons.eliminatePlayer(game, player, interaction,player_helper,True)
        elif customID.startswith("addInfluenceFinish"):
            await InfluenceButtons.addInfluenceFinish(game, player, interaction, customID)
        elif customID.startswith("removeInfluenceStart"):
            await InfluenceButtons.removeInfluenceStart(game, player, interaction)
        elif customID.startswith("removeInfluenceFinish"):
            await InfluenceButtons.removeInfluenceFinish(game, interaction, customID, True)
        elif customID.startswith("addCubeToTrack"):
            await InfluenceButtons.addCubeToTrack(game, player, interaction, customID)
        elif customID.startswith("refreshPopShips"):
            await InfluenceButtons.refreshPopShips(game, player, interaction, customID)
        elif customID.startswith("finishInfluenceAction"):
            await InfluenceButtons.finishInfluenceAction(game, player, interaction, player_helper)
        elif customID.startswith("startDiplomaticRelations"):
            game.updateSaveFile()
            await DiplomaticRelationsButtons.startDiplomaticRelations(game, player, interaction)
        elif customID.startswith("startMinorRelations"):
            await DiplomaticRelationsButtons.startMinorRelations(game, player, interaction)
        elif customID.startswith("offerRelationsTo"):
            await DiplomaticRelationsButtons.offerRelationsTo(game, player, interaction, customID)
        elif customID.startswith("declineRelationsWith"):
            await DiplomaticRelationsButtons.declineRelationsWith(game, player, interaction, customID)
        elif customID.startswith("acceptRelationsWith"):
            await DiplomaticRelationsButtons.acceptRelationsWith(game, player, interaction, customID)
        elif customID.startswith("formMinorRelations"):
            await DiplomaticRelationsButtons.formMinorRelations(game, player, interaction, customID, player_helper)
        elif customID.startswith("reducePopFor"):
            await DiplomaticRelationsButtons.reducePopFor(game, player_helper, interaction, customID)
        elif customID.startswith("startMove"):
            if customID == "startMove":
                game.updateSaveFile()
            await MoveButtons.startMove(game, player, interaction, customID, True)
        elif customID.startswith("moveFrom"):
            await MoveButtons.moveFrom(game, player, interaction, customID)
        elif customID.startswith("moveThisShip"):
            await MoveButtons.moveThisShip(game, player, interaction, customID)
        elif customID.startswith("moveTo"):
            await MoveButtons.moveTo(game, player, interaction, customID, player_helper)
        elif customID.startswith("endGame"):
            await game.endGame(interaction)
        elif customID.startswith("declareWinner"):
            await game.declareWinner(interaction)
        elif customID.startswith("rollDice"):
            await Combat.rollDice(game, customID, interaction)
        elif customID.startswith("rerollDie"):
            await Combat.rerollDie(game, customID, interaction, player, player_helper)
        elif customID.startswith("removeUnits"):
            await Combat.removeUnits(game, customID, player, interaction)
        elif customID.startswith("assignHitTo"):
            await Combat.assignHitTo(game, customID, interaction, True)
        elif customID.startswith("drawReputation"):
            await Combat.drawReputation(game, customID, interaction, player_helper)
        elif customID.startswith("dontDrawReputation"):
            await Combat.dontDrawReputation(game, customID, interaction, player_helper)
        elif customID.startswith("removeThisUnit"):
            await Combat.removeThisUnit(game, customID, player, interaction)
        elif customID.startswith("startToRetreatUnits"):
            await Combat.startToRetreatUnits(game, customID, interaction)
        elif customID.startswith("finishRetreatingUnits"):
            await Combat.finishRetreatingUnits(game, customID, interaction, player)
        elif customID.startswith("killPop"):
            await Combat.killPop(game, customID, interaction, player)
        elif customID.startswith("resolveLyraRiftRoll"):
            await Combat.resolveLyraRiftRoll(game, customID, interaction)
        elif customID.startswith("placeShrineInitial"):
            await ShrineButtons.placeShrineInitial(game, player, interaction, customID)
        elif customID.startswith("placeShrineFinal"):
            await ShrineButtons.placeShrineFinal(game, player, interaction, customID, player_helper)
        elif customID.startswith("draftFaction"):
            await DraftButtons.draftFaction(game, interaction, customID)
        elif customID.startswith("pulsarAction"):
            game.updateSaveFile()
            await PulsarButtons.pulsarAction(game, player, interaction, player_helper, customID)
        elif customID.startswith("blackHoleReturnStart"):
            await BlackHoleButtons.blackHoleReturnStart(game, player, customID, player_helper, interaction)
        elif customID.startswith("blackHoleFinish"):
            await BlackHoleButtons.blackHoleFinish(game, player, customID, player_helper, interaction)
        end_time = time.perf_counter()
        elapsed_time = end_time - start_time
        game.setLockedStatus(False)
        if elapsed_time > 5:
            print(f"Total elapsed time for {customID} button press in side thread: {elapsed_time:.2f} seconds")
