"""Alliances variant (Eclipse: Second Dawn - Expanded Galaxy).

Two players who already have Diplomatic Relations may found an Alliance, and in
6+ player games a third may join if every current member agrees. Allies never
pin each other and never fight each other. Leaving flips your tile to its
Betrayer side and bars you from rejoining that Alliance, though a different one
is still open to you.
"""
import discord
from discord.ui import View, Button

from helpers.GamestateHelper import GamestateHelper


class AllianceButtons:

    @staticmethod
    def areRelated(game: GamestateHelper, colorA, colorB):
        """Diplomatic Relations are stored on the reputation track as
        '<amb|mixed>-<faction>-<color>'; minor species entries are not relations."""
        for color, other in ((colorA, colorB), (colorB, colorA)):
            player = game.getPlayerObjectFromColor(color)
            if player is None:
                continue
            for tile in player["reputation_track"]:
                if isinstance(tile, str) and "-" in tile and "minor" not in tile:
                    if tile.split("-")[2] == other:
                        return True
        return False

    @staticmethod
    def getPlayersToFoundWith(game: GamestateHelper, player):
        """Players who could found a brand new Alliance with this one."""
        return [other for other in game.gamestate["players"].values()
                if AllianceButtons.canFoundAlliance(game, player["color"], other["color"])]

    @staticmethod
    def getJoinableAlliances(game: GamestateHelper, player):
        """Tile types of existing Alliances this player could become a member of."""
        return [tile for tile in game.getJoinableAllianceTiles(player)
                if AllianceButtons.canJoinAlliance(game, player["color"], tile)]

    @staticmethod
    def getBetrayableAlliances(player):
        """Faceup tiles this player could flip to their Betrayer side."""
        return [tile for tile, betrayed in player.get("alliances", {}).items() if not betrayed]

    @staticmethod
    def canUseAlliances(game: GamestateHelper, player=None):
        return bool(game.gamestate.get("alliances") and game.gamestate.get("player_count", 0) >= 4
                    and not game.gamestate.get("gameEnded"))

    @staticmethod
    def canFoundAlliance(game: GamestateHelper, colorA, colorB):
        if not AllianceButtons.canUseAlliances(game) or colorA == colorB:
            return False
        playerA = game.getPlayerObjectFromColor(colorA)
        playerB = game.getPlayerObjectFromColor(colorB)
        return bool(playerA and playerB and not game.isInAlliance(playerA) and not game.isInAlliance(playerB)
                    and AllianceButtons.areRelated(game, colorA, colorB)
                    and any(all(tile not in player.get("alliances", {}) for player in (playerA, playerB))
                            for tile in game.getUnfoundedAllianceTiles()))

    @staticmethod
    def isPlayersTurn(game: GamestateHelper, colors):
        active_colors = game.gamestate.get("activePlayerColor", [])
        # shortcut: after everyone passes the last player stays active, so an old Form Alliance
        # button still works until the next round starts; add an end-of-round flag if that matters.
        return bool(active_colors and active_colors[0] in colors)

    @staticmethod
    def canLeaveAlliance(game: GamestateHelper, player, tile):
        return bool(AllianceButtons.canUseAlliances(game, player)
                    and not game.isLastRound()
                    and not player.get("allianceLeaveClosed", True)
                    and player.get("alliances", {}).get(tile) is False
                    and AllianceButtons.isPlayersTurn(game, [player["color"]]))

    @staticmethod
    def addAllianceButtons(view, game: GamestateHelper, player):
        """Add whichever alliance buttons this player can use right now. A player
        can hold at most one faceup tile, so this adds at most two buttons."""
        if not AllianceButtons.canUseAlliances(game, player):
            return
        if (AllianceButtons.isPlayersTurn(game, [player["color"]])
                and (AllianceButtons.getPlayersToFoundWith(game, player)
                     or AllianceButtons.getJoinableAlliances(game, player))):
            view.add_item(Button(label="Form Alliance", style=discord.ButtonStyle.blurple,
                                 custom_id=f"FCID{player['color']}_startAlliance"))
        for tile in AllianceButtons.getBetrayableAlliances(player):
            if AllianceButtons.canLeaveAlliance(game, player, tile):
                view.add_item(Button(label=f"Leave {tile.capitalize()} Alliance", style=discord.ButtonStyle.red,
                                     custom_id=f"FCID{player['color']}_leaveAlliance_{tile}"))

    @staticmethod
    async def startAlliance(game: GamestateHelper, player, interaction: discord.Interaction):
        if (not AllianceButtons.canUseAlliances(game, player)
                or not AllianceButtons.isPlayersTurn(game, [player["color"]])):
            await interaction.channel.send("You cannot form an alliance right now.")
            await interaction.message.delete()
            return
        view = View()
        for other in AllianceButtons.getPlayersToFoundWith(game, player):
            view.add_item(Button(label=other["name"], style=discord.ButtonStyle.blurple,
                                 custom_id=f"FCID{player['color']}_offerAllianceTo_{other['color']}"))
        for tile in AllianceButtons.getJoinableAlliances(game, player):
            view.add_item(Button(label=f"Join the {tile.capitalize()} Alliance",
                                 style=discord.ButtonStyle.green,
                                 custom_id=f"FCID{player['color']}_offerJoinAlliance_{tile}"))
        if len(view.children) == 0:
            await interaction.channel.send(f"{player['player_name']}, there is nobody you can "
                                           "form an alliance with right now.")
            return
        await interaction.channel.send(f"{player['player_name']}, choose who to found an alliance with,"
                                       " or which existing alliance to join", view=view)

    @staticmethod
    async def offerAllianceTo(game: GamestateHelper, player, interaction: discord.Interaction, buttonID: str):
        otherColor = buttonID.split("_")[1]
        if (not AllianceButtons.isPlayersTurn(game, [player["color"], otherColor])
                or not AllianceButtons.canFoundAlliance(game, player["color"], otherColor)):
            await interaction.channel.send("Those players can no longer found an alliance.")
            await interaction.message.delete()
            return
        other = game.getPlayerObjectFromColor(otherColor)
        view = View()
        view.add_item(Button(label="Accept", style=discord.ButtonStyle.green,
                             custom_id=f"FCID{otherColor}_acceptAllianceWith_{player['color']}"))
        view.add_item(Button(label="Decline", style=discord.ButtonStyle.red,
                             custom_id=f"FCID{otherColor}_declineAllianceWith_{player['color']}"))
        await interaction.channel.send(f"{other['player_name']}, {player['player_name']} offers you an alliance."
                                       " Do you accept?", view=view)
        await interaction.message.delete()

    @staticmethod
    async def declineAllianceWith(game: GamestateHelper, player, interaction: discord.Interaction, buttonID: str):
        otherColor = buttonID.split("_")[1]
        other = game.getPlayerObjectFromColor(otherColor)
        await interaction.channel.send(f"{player['player_name']} declined the alliance offered by"
                                       f" {other['player_name']}.")
        await interaction.message.delete()

    @staticmethod
    async def acceptAllianceWith(game: GamestateHelper, player, interaction: discord.Interaction, buttonID: str):
        otherColor = buttonID.split("_")[1]
        other = game.getPlayerObjectFromColor(otherColor)
        tile = None
        if AllianceButtons.canFoundAlliance(game, player["color"], otherColor):
            tile = game.drawAllianceTile([player["color"], otherColor])
        if tile is None:
            await interaction.channel.send("Those players can no longer found an alliance.")
        else:
            await interaction.channel.send(f"{player['player_name']} and {other['player_name']} have founded"
                                           f" the {tile.capitalize()} Alliance.")
        await interaction.message.delete()

    @staticmethod
    async def offerJoinAlliance(game: GamestateHelper, player, interaction: discord.Interaction, buttonID: str):
        tile = buttonID.split("_")[1]
        if (not AllianceButtons.isPlayersTurn(game, [player["color"]])
                or not AllianceButtons.canJoinAlliance(game, player["color"], tile)):
            await interaction.channel.send("That player is no longer able to join this alliance.")
            await interaction.message.delete()
            return
        view = View()
        for member in game.getAllianceMembers(tile):
            memberName = game.getPlayerObjectFromColor(member)["name"]
            view.add_item(Button(label=f"Agree ({memberName})", style=discord.ButtonStyle.green,
                                 custom_id=f"FCID{member}_agreeJoinAlliance_{tile}_{player['color']}_none"))
        await interaction.channel.send(f"{player['player_name']} asks to join the {tile.capitalize()} Alliance."
                                       " Every current member has to agree.", view=view)
        await interaction.message.delete()

    @staticmethod
    def canJoinAlliance(game: GamestateHelper, color, tile):
        player = game.getPlayerObjectFromColor(color)
        if (player is None or not AllianceButtons.canUseAlliances(game, player)
                or game.isInAlliance(player) or tile not in game.getJoinableAllianceTiles(player)):
            return False
        members = game.getAllianceMembers(tile)
        # An unfounded tile is a founding, not a joining.
        return bool(members and any(AllianceButtons.areRelated(game, color, member) for member in members))

    @staticmethod
    async def agreeJoinAlliance(game: GamestateHelper, player, interaction: discord.Interaction, buttonID: str):
        _prefix, tile, joiner, approved = buttonID.split("_")[:4]
        agreed = [] if approved == "none" else approved.split("+")
        agreed.append(player["color"])
        members = game.getAllianceMembers(tile)
        if (not AllianceButtons.canJoinAlliance(game, joiner, tile)
                or player["color"] not in members):
            await interaction.channel.send("That player is no longer able to join this alliance.")
            await interaction.message.delete()
            return
        remaining = [color for color in game.getAllianceMembers(tile) if color not in agreed]
        if remaining:
            view = View()
            for member in remaining:
                memberName = game.getPlayerObjectFromColor(member)["name"]
                view.add_item(Button(label=f"Agree ({memberName})", style=discord.ButtonStyle.green,
                                     custom_id=(f"FCID{member}_agreeJoinAlliance_{tile}_{joiner}_"
                                                + "+".join(agreed))))
            joinerName = game.getPlayerObjectFromColor(joiner)["player_name"]
            await interaction.channel.send(f"{joinerName} still needs the agreement of the other"
                                           " Alliance members.", view=view)
        else:
            if set(agreed) != set(members):
                await interaction.channel.send("That player is no longer able to join this alliance.")
                await interaction.message.delete()
                return
            try:
                game.formAlliance(tile, [joiner])
            except ValueError as error:
                await interaction.channel.send(f"That player is no longer able to join this alliance: {error}")
                await interaction.message.delete()
                return
            playerName = game.getPlayerObjectFromColor(joiner)["player_name"]
            await interaction.channel.send(f"{playerName} has joined the {tile.capitalize()} Alliance.")
        await interaction.message.delete()

    @staticmethod
    async def leaveAlliance(game: GamestateHelper, player, interaction: discord.Interaction, buttonID: str):
        tile = buttonID.split("_")[1]
        if not AllianceButtons.canLeaveAlliance(game, player, tile):
            await interaction.channel.send("You can no longer leave this alliance.")
            await interaction.message.delete()
            return
        game.betrayAlliance(tile, player["color"])
        await interaction.channel.send(f"{player['player_name']} has left the {tile.capitalize()} Alliance and"
                                       " flipped their tile to its Betrayer side. They may never rejoin it.")
        await interaction.message.delete()
