import os
import discord
from Buttons.Turn import TurnButtons
import config
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button
from typing import Optional, List
from helpers.CombatHelper import Combat
from setup.GameInit import GameInit
from helpers.GamestateHelper import GamestateHelper
from helpers.DrawHelper import DrawHelper
import random
import time


class GameCommands(commands.GroupCog, name="game"):
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="end")
    async def end(self,interaction: discord.Interaction):
        game = GamestateHelper(interaction.channel)
        await game.endGame(interaction)

    @app_commands.command(name="declare_winner")
    async def declare_winner(self,interaction: discord.Interaction):
        game = GamestateHelper(interaction.channel)
        await game.declareWinner(interaction)

    @app_commands.command(name="set_advanced_ai")
    async def set_advanced_ai(self,interaction: discord.Interaction, status:bool):
        game = GamestateHelper(interaction.channel)
        game.setAdvancedAI(status)
        await interaction.response.send_message("Set AI Advanced status to "+str(status))
    @app_commands.command(name="set_turns_in_passing_order")
    async def set_turns_in_passing_order(self,interaction: discord.Interaction, status:bool):
        game = GamestateHelper(interaction.channel)
        game.setTurnsInPassingOrder(status)
        await interaction.response.send_message("Set Turn Order In Passing Order to "+str(status))

    @app_commands.command(name="add_specific_tile_to_deck")
    async def explore_specific_system_tile(self, interaction: discord.Interaction, system_num:str):
        game = GamestateHelper(interaction.channel)
        tile = game.add_specific_tile_to_deck(system_num,system_num)
        drawing = DrawHelper(game.gamestate)
        await interaction.response.defer(thinking=True)
        image = drawing.base_tile_image(tile)
        await interaction.followup.send("Added this tile to the deck", file=drawing.show_single_tile(image))

    @app_commands.command(name="start_combats")
    async def start_combats(self,interaction: discord.Interaction):
        game = GamestateHelper(interaction.channel)
        await interaction.response.defer(thinking=False)
        await Combat.startCombatThreads(game, interaction)

    @app_commands.command(name="upkeep")
    async def upkeep(self,interaction: discord.Interaction):
        await interaction.response.defer(thinking=False)
        game = GamestateHelper(interaction.channel)
        await TurnButtons.runUpkeep(game, interaction,self.bot)
    
    @app_commands.command(name="set_round")
    async def set_round(self,interaction: discord.Interaction, round:int):
        game = GamestateHelper(interaction.channel)
        game.setRound(round)
        await interaction.response.send_message("Set the round number to "+str(round))

    @app_commands.command(name="show_game")
    async def show_game(self, interaction: discord.Interaction):
        game = GamestateHelper(interaction.channel)
        await interaction.response.defer(thinking=True)
        start_time = time.perf_counter()
        drawing = DrawHelper(game.gamestate)
        map = await drawing.show_map()
        stats = await drawing.show_stats()
        await interaction.followup.send(file=map)
        await interaction.followup.send(file=stats)
        view = View()
        button = Button(label="Show Game",style=discord.ButtonStyle.blurple, custom_id="showGame")
        view.add_item(button)
        view.add_item(Button(label="Show Reputation",style=discord.ButtonStyle.gray, custom_id="showReputation"))
        await interaction.channel.send(view=view)
        end_time = time.perf_counter()  
        elapsed_time = end_time - start_time  
        print(f"Total elapsed time for show game command: {elapsed_time:.2f} seconds")  
    
    @app_commands.command(name="undo_to_last_turn_start")
    async def undo_to_last_turn_start(self, interaction: discord.Interaction):
        game = GamestateHelper(interaction.channel)
        if game.backUpToLastSaveFile():
            await interaction.response.send_message("Successfully backed up to the last save file. This generally means it backed up to the last start of someone's turn. They can run /player start_turn to get their buttons. "+str(game.getNumberOfSaveFiles())+" save files remain")
            game.saveLastButtonPressed("restart")
        else:
            await interaction.response.send_message("Ran out of save files, could not back up")
    