
import random
import discord
from helpers.GamestateHelper import GamestateHelper
from helpers.PlayerHelper import PlayerHelper


class ReputationButtons:
    @staticmethod
    async def resolveGainingReputation(game: GamestateHelper, amount_of_options: int,
                                       interaction: discord.Interaction, player_helper: PlayerHelper, queue: bool):
        randomList = game.gamestate["reputation_tiles"][:]
        random.shuffle(randomList)
        opts = ""
        highest = 0
        for x in range(amount_of_options):
            opt = randomList.pop()
            opts += " " + str(opt)
            highest = max(opt, highest)
        if player_helper.stats["name"] == "Rho Indi Syndicate":
            player_helper.stats["money"] += (amount_of_options - 1)
            msg = (f"{player_helper.stats['player_name']}, you drew the tiles{opts} and selected {str(highest)}. You "
                   f"also gained {(amount_of_options - 1)} money.")
        else:
            msg = f"{player_helper.stats['player_name']}, you drew the tiles{opts} and selected {str(highest)}."

        found = False
        for x, tile in enumerate(player_helper.stats["reputation_track"]):
            if tile == "mixed":
                player_helper.stats["reputation_track"][x] = highest
                game.gamestate["reputation_tiles"].remove(highest)
                found = True
                break
        if not found:
            lowest = highest
            loc = 0
            for x, tile in enumerate(player_helper.stats["reputation_track"]):
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
        if not queue:
            await interaction.followup.send(msg, ephemeral=True)
        else:
            threadName = (f"{game.gamestate['game_id']}-Round {game.gamestate['roundNum']}, "
                          f"Queued Draw for {player_helper.stats['color']}")
            actions_channel = discord.utils.get(interaction.guild.channels, name=f"{game.game_id}-actions")
            if actions_channel is not None and isinstance(actions_channel, discord.TextChannel):
                channel = actions_channel
                thread = await channel.create_thread(name=threadName,
                                                     auto_archive_duration=1440,
                                                     type=discord.ChannelType.private_thread,
                                                     invitable=False)
                await thread.send(msg)
