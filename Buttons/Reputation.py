
import random
import discord
from helpers.GamestateHelper import GamestateHelper
from helpers.PlayerHelper import PlayerHelper


class ReputationButtons:
    @staticmethod 
    async def resolveGainingReputation(game: GamestateHelper, amount_of_options:int, interaction: discord.Interaction, player_helper:PlayerHelper):
        randomList = game.gamestate["reputation_tiles"][:]
        random.shuffle(randomList)
        opts = ""
        highest = 0
        for x in range(amount_of_options):
            opt = randomList.pop()
            opts += " "+str(opt)
            highest = max(opt, highest)
        msg = f"{interaction.user.mention}, you drew the tiles{opts} and selected {str(highest)}."
        found = False
        for x,tile in enumerate(player_helper.stats["reputation_track"]):
            if tile == "mixed":
                player_helper.stats["reputation_track"][x] = highest
                game.gamestate["reputation_tiles"].remove(highest)
                found = True
                break
        if not found:
            lowest = highest
            loc = 0
            for x,tile in enumerate(player_helper.stats["reputation_track"]):
                if isinstance(tile, int) and tile < lowest:
                    loc = x
                    lowest = tile
            if lowest != highest:
                msg += f" You replaced a reputation tile with the value of {str(lowest)}"
                player_helper.stats["reputation_track"][loc] = highest
                game.gamestate["reputation_tiles"].append(lowest)
                game.gamestate["reputation_tiles"].remove(highest)
            else:
                msg += " It was lower or equal to your highest value reputation tile, so you put it back in the bag."
        game.update_player(player_helper)
        game.update()
        await interaction.response.send_message(msg, ephemeral=True)
        

