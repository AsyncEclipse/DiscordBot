
import asyncio
import random
import discord
from helpers import FactionData
from helpers.GamestateHelper import GamestateHelper
from helpers.PlayerHelper import PlayerHelper


class ReputationButtons:
    @staticmethod
    async def resolveGainingReputation(game: GamestateHelper, amount_of_options: int,
                                       interaction: discord.Interaction, player_helper: PlayerHelper, queue: bool,
                                       battle_rep_adjustment: int = 0):
        randomList = game.gamestate["reputation_tiles"][:]
        random.shuffle(randomList)
        opts = ""
        highest = 0
        if ('community_rep_mod' in game.gamestate and game.gamestate["community_rep_mod"]):
            if amount_of_options == 1:
                opts = '1'
                highest = 1
            else:
                modList = [x for x in randomList if x <= amount_of_options]
                random.shuffle(modList)
                for x in range(amount_of_options):
                    opt = modList.pop()
                    opts += " " + str(opt)
                    highest = max(opt, highest)
        else:
            for x in range(amount_of_options):
                opt = randomList.pop()
                opts += " " + str(opt)
                highest = max(opt, highest)
        gained = FactionData.of(player_helper.stats).get("reputation_draw_money", 0) * (amount_of_options - 1)
        msg = f"{player_helper.stats['player_name']}, you drew the tiles{opts} and selected {str(highest)}."
        if gained:
            player_helper.stats["money"] += gained
            msg += f" You also gained {gained} money."

        # Kurita: the +1/-1 belongs to the slot of the tile it was drawn with, so compare tile + marker
        track = player_helper.stats["reputation_track"]
        bonuses = player_helper.stats.setdefault("reputationBonuses", {})
        marker = f" ({battle_rep_adjustment:+d})" if battle_rep_adjustment else ""
        newValue = highest + battle_rep_adjustment
        loc = next((x for x, tile in enumerate(track) if tile in ("rep", "mixed")), None)
        if loc is None:
            worth = {x: tile + bonuses.get(str(x), 0) for x, tile in enumerate(track) if isinstance(tile, int)}
            lowestLoc = min(worth, key=worth.get, default=None)
            if lowestLoc is not None and worth[lowestLoc] < newValue:
                loc = lowestLoc
                lowestMarker = f" ({bonuses[str(loc)]:+d})" if bonuses.get(str(loc)) else ""
                msg += f" You replaced a reputation tile with the value of {track[loc]}{lowestMarker}"
                game.gamestate["reputation_tiles"].append(track[loc])
            else:
                msg += (f" {highest}{marker} was lower or equal to your lowest reputation tile,"
                        " so you put it back in the bag.")
        if loc is not None:
            track[loc] = highest
            game.gamestate["reputation_tiles"].remove(highest)
            if battle_rep_adjustment:
                bonuses[str(loc)] = battle_rep_adjustment
            else:
                bonuses.pop(str(loc), None)
        if not bonuses:
            player_helper.stats.pop("reputationBonuses")
        game.update_player(player_helper)
        game.update()
        if not queue:
            asyncio.create_task(interaction.followup.send(msg, ephemeral=True))
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
                asyncio.create_task(thread.send(msg))
