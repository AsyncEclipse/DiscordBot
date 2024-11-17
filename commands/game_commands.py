import asyncio
import discord
from Buttons.Turn import TurnButtons
from discord.ext import commands
from discord import app_commands
from helpers.CombatHelper import Combat
from helpers.GamestateHelper import GamestateHelper
from helpers.DrawHelper import DrawHelper


class GameCommands(commands.GroupCog, name="game"):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="end")
    async def end(self, interaction: discord.Interaction):
        game = GamestateHelper(interaction.channel)
        await game.endGame(interaction)

    @app_commands.command(name="declare_winner")
    async def declare_winner(self, interaction: discord.Interaction):
        game = GamestateHelper(interaction.channel)
        await game.declareWinner(interaction)

    @app_commands.command(name="set_advanced_ai")
    async def set_advanced_ai(self, interaction: discord.Interaction, status: bool):
        game = GamestateHelper(interaction.channel)
        game.setAdvancedAI(status)
        await interaction.response.send_message("Set AI Advanced status to " + str(status))

    @app_commands.command(name="set_fancy_ships")
    async def set_fancy_ships(self, interaction: discord.Interaction, status: bool):
        game = GamestateHelper(interaction.channel)
        game.setFancyShips(status)
        await interaction.response.send_message("Set fancy ships status to " + str(status))

    @app_commands.command(name="set_turns_in_passing_order")
    async def set_turns_in_passing_order(self, interaction: discord.Interaction, status: bool):
        game = GamestateHelper(interaction.channel)
        game.setTurnsInPassingOrder(status)
        await interaction.response.send_message("Set Turn Order In Passing Order to " + str(status))

    @app_commands.command(name="add_specific_tile_to_deck")
    async def explore_specific_system_tile(self, interaction: discord.Interaction, system_num: str):
        game = GamestateHelper(interaction.channel)
        tile = game.add_specific_tile_to_deck(system_num, system_num)
        drawing = DrawHelper(game.gamestate)
        await interaction.response.defer(thinking=True)
        image = drawing.base_tile_image(tile)
        await interaction.followup.send("Added this tile to the deck", file=drawing.show_single_tile(image))

    @app_commands.command(name="add_observer")
    async def add_observer(self, interaction: discord.Interaction, user: discord.User):
        game = GamestateHelper(interaction.channel)
        guild = interaction.guild
        for channel in guild.text_channels:
            if game.game_id in channel.name:
                try:
                    await channel.set_permissions(user, read_messages=True, send_messages=True)
                    await interaction.response.send_message(f"Added {user.mention} to {channel.name}")
                except discord.Forbidden:
                    await interaction.channel.send(f"Failed to add {user.mention} to {channel.name}:"
                                                   " Missing permissions.")
                except discord.HTTPException as e:
                    await interaction.channel.send("An error occurred when adding"
                                                   f" {user.mention} to {channel.name}: {str(e)}")

    @app_commands.command(name="start_combats")
    async def start_combats(self, interaction: discord.Interaction):
        game = GamestateHelper(interaction.channel)
        await interaction.response.defer(thinking=False)
        await Combat.startCombatThreads(game, interaction)

    @app_commands.command(name="upkeep")
    async def upkeep(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=False)
        game = GamestateHelper(interaction.channel)
        await TurnButtons.runUpkeep(game, interaction)

    @app_commands.command(name="disable_minor_species")
    async def disable_minor_species(self, interaction: discord.Interaction):
        await interaction.response.send_message("The Minor Species expansion has been disabled")
        game = GamestateHelper(interaction.channel)
        game.initilizeKey("minor_species")

    @app_commands.command(name="set_outlines_status")
    async def set_outlines_status(self, interaction: discord.Interaction, status: bool):
        game = GamestateHelper(interaction.channel)
        game.initilizeKey("turnOffLines")
        game.setAdvancedAI(status)
        await interaction.response.send_message("Set Outlines status to " + str(status))

    @app_commands.command(name="disable_five_player_hyperlanes")
    async def disable_five_player_hyperlanes(self, interaction: discord.Interaction):
        await interaction.response.send_message("The hyperlanes for 5 player mode have been disabled")
        game = GamestateHelper(interaction.channel)
        game.initilizeKey("5playerhyperlane")

    @app_commands.command(name="set_round")
    async def set_round(self, interaction: discord.Interaction, rnd: int):
        game = GamestateHelper(interaction.channel)
        game.setRound(rnd)
        await interaction.response.send_message(f"Set the round number to {rnd}.")

    @app_commands.command(name="show_game")
    async def show_game(self, interaction: discord.Interaction):
        game = GamestateHelper(interaction.channel)
        await interaction.response.defer(thinking=True)
        # start_time = time.perf_counter()
        asyncio.create_task(TurnButtons.showGameAsync(game, interaction, False))

        # end_time = time.perf_counter()
        # elapsed_time = end_time - start_time
        # print("Total elapsed time for show game command:"
        #       + f" {elapsed_time:.2f} seconds")

    @app_commands.command(name="undo_to_last_turn_start")
    async def undo_to_last_turn_start(self, interaction: discord.Interaction):
        game = GamestateHelper(interaction.channel)
        if game.backUpToLastSaveFile():
            await interaction.response.send_message("Successfully backed up to the last save file. "
                                                    "This generally means it backed up to the"
                                                    + " last start of someone's turn. "
                                                    "They may run /player start_turn to get their buttons. "
                                                    + str(game.getNumberOfSaveFiles()) + " save files remain.")
            game.saveLastButtonPressed("restart")
        else:
            await interaction.response.send_message("Ran out of save files, could not back up")

    @app_commands.command(name="eliminate_player")
    async def eliminate_player(self, interaction: discord.Interaction, player: discord.Member):
        game = GamestateHelper(interaction.channel)
        try:
            player_color = game.gamestate["players"][str(player.id)]["color"]
            player_name = game.gamestate["players"][str(player.id)]["player_name"]
        except KeyError:
            await interaction.response.send_message("That player is not in this game.")
            return
        for tile in game.gamestate["board"]:
            if "back" in game.gamestate["board"][tile]["sector"]:
                continue
            if game.gamestate["board"][tile]["owner"] == player_color:
                game.gamestate["board"][tile]["owner"] = 0
                if len(game.gamestate["board"][tile]["money_pop"]) > 0:
                    game.gamestate["board"][tile]["money_pop"][0] = 0
                if len(game.gamestate["board"][tile]["science_pop"]) > 0:
                    game.gamestate["board"][tile]["science_pop"][0] = 0
                if len(game.gamestate["board"][tile]["material_pop"]) > 0:
                    game.gamestate["board"][tile]["material_pop"][0] = 0
                if len(game.gamestate["board"][tile]["neutral_pop"]) > 0:
                    game.gamestate["board"][tile]["neutral_pop"][0] = 0
                if len(game.gamestate["board"][tile]["moneyadv_pop"]) > 0:
                    game.gamestate["board"][tile]["moneyadv_pop"][0] = 0
                if len(game.gamestate["board"][tile]["scienceadv_pop"]) > 0:
                    game.gamestate["board"][tile]["scienceadv_pop"][0] = 0
                if len(game.gamestate["board"][tile]["materialadv_pop"]) > 0:
                    game.gamestate["board"][tile]["materialadv_pop"][0] = 0
                if len(game.gamestate["board"][tile]["neutraladv_pop"]) > 0:
                    game.gamestate["board"][tile]["neutraladv_pop"][0] = 0
                game.gamestate["board"][tile]["player_ships"] = [e
                                                                 for e in game.gamestate["board"][tile]["player_ships"]
                                                                 if player_color not in e]
        try:
            if player_name in game.gamestate["pass_order"]:
                game.gamestate["pass_order"].remove(player_name)
        except KeyError:
            pass
        try:
            if player_name in game.gamestate["turn_order"]:
                game.gamestate["turn_order"].remove(player_name)
        except KeyError:
            pass
        del game.gamestate["players"][str(player.id)]
        await interaction.response.send_message(f"{player_name} has been removed from the game.")
        game.update()
