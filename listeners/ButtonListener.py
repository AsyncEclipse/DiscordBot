import discord
from discord.ext import commands
from Buttons.Build import BuildButtons
from Buttons.DiscoveryTile import DiscoveryTileButtons
from Buttons.Explore import ExploreButtons
from Buttons.Influence import InfluenceButtons
from Buttons.Move import MoveButtons
from Buttons.Population import PopulationButtons
from Buttons.Research import ResearchButtons
from Buttons.Turn import TurnButtons
from Buttons.Upgrade import UpgradeButtons
from helpers.GamestateHelper import GamestateHelper


from helpers.PlayerHelper import PlayerHelper

class ButtonListener(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_interaction(self, interaction : discord.Interaction):
        if interaction.type == discord.InteractionType.component:
            game = GamestateHelper(interaction.channel)
            player = game.get_player(interaction.user.id)  
            player_helper = PlayerHelper(interaction.user.id, player)
            customID = interaction.data["custom_id"]
            # If we want to prevent others from touching someone else's buttons, we can attach FCID{color}_ to the start of the button ID as a check.
            # We then remove this check so it doesnt interfere with the rest of the resolution
            if customID.startswith("FCID"):
                check = customID.split("_")[0]
                if player["color"] != check.replace("FCID",""):
                    await interaction.response.send_message(interaction.user.mention+" These buttons are not for you.")
                    return
                customID = customID.replace(check+"_","")
            if customID == "deleteMsg":
                await interaction.message.delete()
            if customID == "showGame":  
                await TurnButtons.showGame(game, interaction)
            if customID == "showReputation":  
                await TurnButtons.showReputation(game, interaction,player)
            if customID == "passForRound":
                await TurnButtons.passForRound(player, game, interaction,player_helper)
            if customID == "permanentlyPass":
                await TurnButtons.permanentlyPass(player, game, interaction,player_helper)
            if customID == "endTurn":
                await TurnButtons.endTurn(player, game, interaction)
            if customID == "restartTurn":
                await TurnButtons.restartTurn(player, game, interaction)
            if customID == "runCleanup":
                await TurnButtons.runCleanup(game, interaction)
            if customID.startswith("startExplore"):
                await ExploreButtons.startExplore(game, player, player_helper, interaction,customID)
            if customID.startswith("exploreTile_"):
                await ExploreButtons.exploreTile(game, player, interaction)
            if customID.startswith("placeTile"):
                await ExploreButtons.placeTile(game,  interaction, player)
            if customID.startswith("discardTile"):
                await ExploreButtons.discardTile(game, interaction)
            if customID.startswith("keepDiscForPoints"):
                await DiscoveryTileButtons.keepDiscForPoints(game, player_helper, interaction)
            if customID.startswith("usedDiscForAbility"):
                await DiscoveryTileButtons.usedDiscForAbility(game, player_helper, interaction, customID,player)
            if customID.startswith("startResearch"):
                await ResearchButtons.startResearch(game, player, player_helper, interaction,True)
            if customID.startswith("getTech_"):
                await ResearchButtons.getTech(game, player, player_helper, interaction)
            if customID.startswith("payAtRatio_"):
                await ResearchButtons.payAtRatio(game, player, player_helper, interaction, customID)
            if customID.startswith("gain5resource_"):
                await ResearchButtons.gain5resource(game, player, player_helper, interaction, customID)
            if customID.startswith("startBuild"):
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
                await UpgradeButtons.startUpgrade(game, player, interaction, True)
            if customID.startswith("upgradeShip"):
                await UpgradeButtons.upgradeShip(game, player, interaction, customID, player_helper)
            if customID.startswith("selectOldPart"):
                await UpgradeButtons.selectOldPart(game, player, interaction, customID)
            if customID.startswith("chooseUpgrade"):
                await UpgradeButtons.chooseUpgrade(game, player, interaction, customID, player_helper)
            if customID.startswith("startPopDrop"):
                await PopulationButtons.startPopDrop(game, player, interaction)
            if customID.startswith("fillPopulation"):
                await PopulationButtons.fillPopulation(game, player, interaction, customID)
            if customID.startswith("startInfluence"):
                await InfluenceButtons.startInfluence(game, player, interaction)
            if customID.startswith("addInfluenceStart"):
                await InfluenceButtons.addInfluenceStart(game, player, interaction)
            if customID.startswith("addInfluenceFinish"):
                await InfluenceButtons.addInfluenceFinish(game, player, interaction,customID)
            if customID.startswith("removeInfluenceStart"):
                await InfluenceButtons.removeInfluenceStart(game, player, interaction)
            if customID.startswith("removeInfluenceFinish"):
                await InfluenceButtons.removeInfluenceFinish(game, player, interaction,customID)
            if customID.startswith("addCubeToTrack"):
                await InfluenceButtons.addCubeToTrack(game, player, interaction,customID)
            if customID.startswith("refreshPopShips"):
                await InfluenceButtons.refreshPopShips(game, player, interaction, customID)
            if customID.startswith("finishInfluenceAction"):
                await InfluenceButtons.finishInfluenceAction(game, player, interaction,player_helper)
            if customID.startswith("startMove"):
                await MoveButtons.startMove(game, player, interaction,customID,player_helper, True)
            if customID.startswith("moveFrom"):
                await MoveButtons.moveFrom(game, player, interaction,customID)
            if customID.startswith("moveThisShip"):
                await MoveButtons.moveThisShip(game, player, interaction,customID)
            if customID.startswith("moveTo"):
                await MoveButtons.moveTo(game, player, interaction,customID,player_helper)

            
                