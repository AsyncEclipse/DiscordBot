from types import SimpleNamespace
from unittest.mock import AsyncMock

import discord
import pytest

from Buttons.Turn import TurnButtons
from helpers.CombatHelper import Combat
from tests.fakes import FakeInteraction


def missing_message():
    return discord.NotFound(SimpleNamespace(status=404, reason="Not Found"),
                            {"code": 10008, "message": "Unknown Message"})


def test_end_turn_handles_an_already_deleted_message(start_game, run, capsys):
    game, channel = start_game()
    interaction = FakeInteraction(channel)
    interaction.message.delete = AsyncMock(side_effect=missing_message())

    run(TurnButtons.endTurn(game.get_player(1), game, interaction))

    interaction.message.delete.assert_awaited_once()
    assert "was already deleted" in capsys.readouterr().out


@pytest.mark.parametrize("queued", [False, True])
@pytest.mark.parametrize("error_type", [discord.NotFound, discord.Forbidden])
def test_reputation_deletion_handles_only_missing_messages(queued, error_type, monkeypatch, run, capsys):
    interaction = FakeInteraction()
    error = error_type(SimpleNamespace(status=404 if error_type is discord.NotFound else 403,
                                      reason="test"), "test")
    interaction.message.delete = AsyncMock(side_effect=error)
    game = SimpleNamespace(gamestate={"tilesToResolve": []} if queued else {},
                           removeFromKey=lambda *args: None,
                           addToKey=lambda *args: None)
    if queued:
        game.gamestate["queuedDraws"] = []
    monkeypatch.setattr(Combat, "resolveQueue", AsyncMock())
    monkeypatch.setattr("helpers.CombatHelper.ReputationButtons.resolveGainingReputation", AsyncMock())

    if error_type is discord.Forbidden:
        with pytest.raises(discord.Forbidden):
            run(Combat.drawReputation(game, "drawReputation_1_201_0_blue", interaction, None))
    else:
        run(Combat.drawReputation(game, "drawReputation_1_201_0_blue", interaction, None))
        assert "was already deleted" in capsys.readouterr().out
    interaction.message.delete.assert_awaited_once()
