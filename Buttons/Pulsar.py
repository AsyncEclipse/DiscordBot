import discord
from helpers.GamestateHelper import GamestateHelper
from helpers.PlayerHelper import PlayerHelper
from discord.ui import View, Button


class PulsarButtons:
    @staticmethod
    def findPulsarOptions(game: GamestateHelper, player):
        view = View()
        actions = ["build", "move", "upgrade"]
        for tile in game.gamestate["board"]:
            if all(["currentAction" in game.gamestate["board"][tile],
                   game.gamestate["board"][tile]["owner"] == player["color"],
                   "activatedPulsars" not in player or tile not in player["activatedPulsars"]]):
                for action in actions:
                    if action == game.gamestate["board"][tile]["currentAction"]:
                        continue
                    view.add_item(Button(label=f"Do Pulsar {action.capitalize()} ({tile})",
                                         style=discord.ButtonStyle.gray,
                                         custom_id=f"FCID{player['color']}_pulsarAction_{tile}_{action}"))
        return view

    @staticmethod
    async def pulsarAction(game: GamestateHelper, player, interaction: discord.Interaction,
                           player_helper: PlayerHelper, customID: str):
        from Buttons.Build import BuildButtons
        from Buttons.Move import MoveButtons
        from Buttons.Upgrade import UpgradeButtons
        tile = customID.split("_")[1]
        action = customID.split("_")[2]
        if "activatedPulsars" not in player_helper.stats:
            player_helper.stats["activatedPulsars"] = []
        player_helper.stats["activatedPulsars"].append(tile)
        game.update_player(player_helper)
        game.update_pulsar_action(tile, action)
        await interaction.message.delete()
        await interaction.channel.send(f"{player['player_name']} used a pulsar (tile {tile})"
                                       f" to perform the {action} action.")
        if action == "build":
            player_helper.stats["pulsarBuild"] = True
            game.update_player(player_helper)
            await BuildButtons.startBuild(game, player, interaction, "startBuild2", player_helper)
        if action == "upgrade":
            await UpgradeButtons.startUpgrade(game, player, interaction, False, "dummy")
        if action == "move":
            await MoveButtons.startMove(game, player, interaction, "startMove_8", False)
