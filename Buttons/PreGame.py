import asyncio
import discord
from Buttons.DiscoveryTile import DiscoveryTileButtons
from Buttons.Population import PopulationButtons
from Buttons.Research import ResearchButtons
from Buttons.Turn import TurnButtons
from helpers.GamestateHelper import GamestateHelper
from helpers import FactionData
from discord.ui import View, Button


class PreGameButtons:
    """The phase between setting the game up and the first turn.

    Factions that have something to do before the game starts do it here: the Exiles
    populate the Orbital in their starting sector, the Atlantians resolve a discovery
    tile, Remnants of Ra put a cube on the disc of their artifact sector and the
    Techno-Mages may buy a technology. The first turn only starts once they are all done.
    """

    TASK_BUTTONS = {
        "orbital_pop": ("preGameOrbital",),
        "artifact_cube": ("ancientsCube",),
        "discovery_tile": ("selectDiscTile", "keepDiscForPoints", "usedDiscForAbility"),
        "discovery_upgrade": ("upgradeShip", "selectOldPart", "chooseUpgrade", "chooseDifferentShip",
                              "saveDiscoveryPart"),
        "discovery_tech": ("getFreeTech",),
        "discovery_resource": ("gain3resource",),
        "setup_tech": ("setupTech", "getTech", "declineSetupTech"),
        "setup_warp": ("placeWarpPortal",),
        "setup_resources": ("gain5resource", "finishSetupResources"),
    }

    @staticmethod
    def tasksForPlayer(player):
        tasks = []
        if FactionData.has(player, "orbital_pop_ships"):
            tasks.append("orbital_pop")
        if "anl" in player.get("nano_tech", []):
            tasks.append("discovery_tile")
        if FactionData.has(player, "artifact_disc_pop"):
            tasks.append("artifact_cube")
        if FactionData.has(player, "setup_tech"):
            tasks.append("setup_tech")
        return tasks

    @staticmethod
    async def canResolve(game, interaction, player, customID):
        phase = game.gamestate.get("pre_game")
        if phase is None:
            return True  # Games already running before the phase was introduced keep their buttons.
        player_id = game.get_player_from_color(player["color"])
        pending = [task for seat, task in game.preGameTasks() if seat == player_id]
        setup_button = (customID.startswith(("setupTech", "declineSetupTech", "preGameOrbital"))
                        or (customID.startswith("getTech_") and customID.endswith("_setup")))
        if not phase.get("started"):
            if customID.startswith(("showReputation", "showGame")):
                return True
            if any(customID.startswith(PreGameButtons.TASK_BUTTONS[task]) for task in pending):
                return True
            await interaction.followup.send("Finish the pending pre-game actions before taking a turn.",
                                            ephemeral=True)
            return False
        if setup_button:
            await interaction.followup.send("That pre-game action is already finished.", ephemeral=True)
            return False
        return True

    @staticmethod
    async def startPreGame(game: GamestateHelper, interaction: discord.Interaction, player_ids):
        """Ask every faction that has something to do before the game starts to do it now."""
        tasks = [[str(player_id), task] for player_id in player_ids
                 for task in PreGameButtons.tasksForPlayer(game.get_player(player_id, interaction))]
        # Register every task before sending prompts; a quick reply must not start the game early.
        game.gamestate["pre_game"] = {"first_player": str(player_ids[0]), "tasks": tasks,
                                      "offering": True, "started": False}
        game.update()
        for player_id, task in list(tasks):
            player = game.get_player(player_id, interaction)
            home = game.getLocationFromID(player["home_planet"])
            if task == "orbital_pop":
                offered = await PreGameButtons.offerExilesOrbital(game, player, interaction, home)
            elif task == "discovery_tile":
                game.addDiscTile(home)
                offered = await DiscoveryTileButtons.exploreDiscoveryTile(game, home, interaction, player)
            elif task == "artifact_cube":
                offered = await PopulationButtons.offerAncientsCube(game, player, interaction, home)
            else:
                offered = await ResearchButtons.offerSetupTech(game, player, interaction)
            if not offered:
                # this faction cannot do this action after all, so the game does not wait for it
                game.gamestate["pre_game"]["tasks"].remove([str(player_id), task])
                game.update()
        game.gamestate["pre_game"]["offering"] = False
        game.update()
        if not game.preGameTasks():
            await PreGameButtons.startGame(game, interaction, player_ids[0])
        else:
            await interaction.channel.send("The game starts once every faction has finished"
                                           " their pre-game action.")

    @staticmethod
    async def completeTask(game: GamestateHelper, interaction: discord.Interaction, player,
                           customID: str, result):
        """Advance only successful actions; a follow-up choice remains a pending task."""
        if not result:
            return
        player_id = game.get_player_from_color(player["color"])
        tasks = game.preGameTasks()
        for entry in tasks:
            seat, task = entry
            if seat == player_id and customID.startswith(PreGameButtons.TASK_BUTTONS[task]):
                if isinstance(result, str):
                    entry[1] = result
                else:
                    tasks.remove(entry)
                game.update()
                if not tasks:
                    await PreGameButtons.startGame(game, interaction,
                                                   game.gamestate["pre_game"]["first_player"])
                break

    @staticmethod
    async def startGame(game: GamestateHelper, interaction: discord.Interaction, first_player):
        """Start the first turn of the game."""
        phase = game.gamestate.get("pre_game", {})
        if phase.get("started") or phase.get("offering") or game.preGameTasks():
            return
        phase["started"] = True
        game.update()
        player = game.get_player(first_player, interaction)
        asyncio.create_task(game.showUpdate("Start of Game", interaction))
        TurnButtons.startNewTurn(player, game)
        view = TurnButtons.getStartTurnButtons(game, player, "dummy")
        game.updatePingTime()
        await interaction.channel.send(f"## {game.getPlayerEmoji(player)} started their turn.")
        await interaction.channel.send(f"{player['player_name']} use these buttons to do your turn"
                                       + game.displayPlayerStats(player), view=view)

    @staticmethod
    async def offerExilesOrbital(game: GamestateHelper, player, interaction: discord.Interaction, tile: str):
        """The Exiles put a population cube on the Orbital in their starting sector before the game starts."""
        if game.gamestate["board"][tile].get("orbital_pop", [0])[0]:
            return False
        options = [pop for pop in ["money", "science"]
                   if player["colony_ships"] > 0 and player[f"{pop}_pop_cubes"] > 0]
        if not options:
            return False
        view = View()
        for pop in options:
            view.add_item(Button(label=pop.capitalize(), style=discord.ButtonStyle.blurple,
                                 custom_id=f"FCID{player['color']}_preGameOrbital_{pop}"))
        await interaction.channel.send(f"{player['player_name']}, before the game starts you place a population"
                                       f" cube on the Orbital in your starting sector (tile {tile})."
                                       " Choose which type of cube to place.", view=view)
        return True

    @staticmethod
    async def placeExilesOrbital(game: GamestateHelper, player, interaction: discord.Interaction, customID: str):
        pop = customID.split("_")[1]
        if pop not in ("money", "science"):
            await interaction.followup.send("Choose a money or science cube.", ephemeral=True)
            return False
        tile = game.getLocationFromID(player["home_planet"])
        if game.gamestate["board"][tile].get("orbital_pop", [0])[0]:
            await interaction.followup.send("Your Orbital already has a population cube on it.", ephemeral=True)
            return
        if not game.add_pop_specific("orbital", pop, 0, tile, game.get_player_from_color(player["color"])):
            await interaction.followup.send("You need an unused colony ship and a cube"
                                            " to populate your Orbital.", ephemeral=True)
            return
        await interaction.message.edit(view=None)
        await interaction.channel.send(f"{player['player_name']} placed a {pop} population cube on the Orbital"
                                       f" in tile {tile}.")
        return True

    @staticmethod
    async def declineSetupTech(game: GamestateHelper, player, interaction: discord.Interaction):
        """The Techno-Mages may pass on the technology they may buy before the game starts."""
        await interaction.message.delete()
        await interaction.channel.send(f"{player['player_name']} is not buying a technology before the game starts.")
        return True
