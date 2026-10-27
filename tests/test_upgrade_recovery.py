from types import SimpleNamespace
from unittest.mock import AsyncMock

import discord
import pytest

from Buttons.Upgrade import UpgradeButtons
from helpers.DrawHelper import DrawHelper
from helpers.PlayerHelper import PlayerHelper
from tests.fakes import FakeInteraction, buttons, reload


@pytest.fixture
def upgrade_game(start_game, monkeypatch):
    monkeypatch.setattr(DrawHelper, "player_area", lambda *args: None)
    monkeypatch.setattr(DrawHelper, "show_player_ship", lambda *args: None)
    return start_game(factions=["tm", "eri"])


def test_failed_menu_deletion_keeps_upgrade_controls_and_retry_is_refused(upgrade_game, run):
    game, channel = upgrade_game
    player = game.get_player(1)
    discs = player["influence_discs"]
    interaction = FakeInteraction(channel)
    interaction.message.delete = AsyncMock(side_effect=discord.DiscordServerError(
        SimpleNamespace(status=503, reason="Service Unavailable"), "Connection refused"))
    choice = "chooseUpgrade_2_interceptor_empty_hul_3_dummy"

    run(UpgradeButtons.chooseUpgrade(game, player, interaction, choice, PlayerHelper("1", player)))

    game = reload(game)
    player = game.get_player(1)
    assert player["interceptor_parts"] == ["ioc", "nus", "nud", "hul"]
    assert player["influence_discs"] == discs - 1
    assert "FCIDblue_finishAction" in buttons(channel)
    assert "FCIDblue_undoUpgrade_2_dummy" in buttons(channel)
    saved_player = dict(player)

    run(UpgradeButtons.chooseUpgrade(game, player, interaction, choice, PlayerHelper("1", player)))

    assert reload(game).get_player(1) == saved_player
    assert any("changed" in content for content, kwargs in interaction.followup.sent)


def test_stale_slot_is_refused_even_if_old_part_exists_elsewhere(upgrade_game, run):
    game, channel = upgrade_game
    player = game.get_player(1)
    interaction = FakeInteraction(channel)
    # The ion cannon exists in slot 0, but this button claims it is in slot 3.
    run(UpgradeButtons.chooseUpgrade(game, player, interaction,
                                     "chooseUpgrade_2_interceptor_ioc_hul_3_dummy",
                                     PlayerHelper("1", player)))

    assert reload(game).get_player(1) == player
    assert player["interceptor_parts"][-1] == "empty"
    assert any("changed" in content for content, kwargs in interaction.followup.sent)
