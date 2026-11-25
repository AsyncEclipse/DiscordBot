"""Community faction sheets, offered from the Faction Reference thread.

Both controls carry plain custom ids, so ButtonListener answers them: an old
button message keeps working after a restart and the picker never expires.
"""
import discord

from helpers.DrawHelper import DrawHelper
from helpers.FactionReference import faction_references

BOARD_DIR = "images/resources/components/factions/"


class FactionSheet:
    @staticmethod
    def community_sheets():
        """Community boards: every reference board that is not a standard faction board."""
        standard = {board for _, board in faction_references(False)}
        return {board: message for message, board in faction_references(True) if board not in standard}

    @staticmethod
    def request_button():
        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="Request community sheet", style=discord.ButtonStyle.blurple,
                                        custom_id="community_sheet:request"))
        return view

    @staticmethod
    def faction_picker():
        view = discord.ui.View()
        view.add_item(discord.ui.Select(
            placeholder="Select a community faction",
            options=[discord.SelectOption(label=message.splitlines()[0].removeprefix("# ")[:100], value=board)
                     for board, message in FactionSheet.community_sheets().items()],
            custom_id="community_sheet:select"))
        return view

    @staticmethod
    async def present_picker(interaction: discord.Interaction):
        await interaction.response.send_message("Choose a community faction:",
                                                view=FactionSheet.faction_picker(), ephemeral=True)

    @staticmethod
    async def answer(interaction: discord.Interaction):
        """Answer a press on the request button or on the faction select."""
        if interaction.data.get("custom_id") == "community_sheet:request":
            await FactionSheet.present_picker(interaction)
            return
        board_file = interaction.data["values"][0]
        message = FactionSheet.community_sheets().get(board_file)
        if message is None:
            await interaction.response.send_message("That faction sheet is not available.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        # get_file only reads the static board, so the drawing helper needs no gamestate here.
        await interaction.channel.send(message, file=DrawHelper(None).get_file(BOARD_DIR + board_file))
        await interaction.followup.send("Added the faction sheet to the reference thread.", ephemeral=True)
