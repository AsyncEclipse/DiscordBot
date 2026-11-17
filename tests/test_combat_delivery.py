"""Discord delivery failures must not lose combat results or reputation choices."""
from types import SimpleNamespace

import aiohttp
import discord
import pytest

from helpers.CombatHelper import Combat
from tests.fakes import FakeChannel, FakeInteraction, POS, offered_ids, player_helper, player_stats, reload


@pytest.fixture
def battle(make_game):
    return make_game({
        "advanced_ai": 0, "wa_ai": 0, "player_count": 2, "roundNum": 1,
        "players": {
            "1": player_stats("ter6", color="blue", interceptor_parts=["plc", "elc", "nud", "nus"]),
            "2": player_stats("dra", color="red", base_dread_speed=1, base_dread_comp=2,
                              dread_parts=["anc", "anc", "nud", "nus"]),
        },
        "tilesToResolve": [101], "queuedQuestions": [], "queuedDraws": [],
        "reputation_tiles": [1, 2, 3, 4],
        "board": {POS: {"owner": "red", "sector": 101, "disctile": 0,
                        "player_ships": ["red-drd", "blue-int"],
                        "attacker": "blue", "defender": "red", "combatants": ["blue", "red"]}},
    })


@pytest.mark.parametrize("failure", ["connection", "http", "timeout"])
def test_failed_destruction_report_still_offers_reputation(battle, no_random, run, monkeypatch, caplog,
                                                          failure):
    interaction = FakeInteraction()
    send = interaction.channel.send

    async def fail_report(content, **kwargs):
        if "dealt 4 damage" in content:
            if failure == "connection":
                raise aiohttp.ClientConnectionError("connection dropped")
            if failure == "timeout":
                raise TimeoutError("request timed out")
            raise discord.HTTPException(SimpleNamespace(status=503, reason="Unavailable"), "unavailable")
        return await send(content, **kwargs)

    monkeypatch.setattr(interaction.channel, "send", fail_report)
    no_random([4, 5])
    run(Combat.rollDice(battle, f"rollDice_{POS}_red_2_deleteMsg", interaction))

    assert "blue-int" not in reload(battle).gamestate["board"][POS]["player_ships"]
    assert "FCIDred_drawReputation_2_101_2_red" in offered_ids(interaction)
    assert "Failed to send combat report" in caplog.text


def test_missing_offers_survive_reload_and_refresh_without_duplicate_answers(battle, no_random, run,
                                                                           monkeypatch, caplog):
    interaction = FakeInteraction()
    send = interaction.channel.send

    async def fail_offers(content, **kwargs):
        if "reputation tiles here" in content:
            # Both players' exact draw amounts must already be on disk before delivery.
            offers = reload(battle).gamestate["reputationOffers"]
            assert {offer["count"] for offer in offers.values()} == {1, 2}
            raise aiohttp.ClientConnectionError("connection dropped")
        return await send(content, **kwargs)

    monkeypatch.setattr(interaction.channel, "send", fail_offers)
    no_random([4, 5])
    run(Combat.rollDice(battle, f"rollDice_{POS}_red_2_deleteMsg", interaction))
    assert "Failed to send reputation offer" in caplog.text

    game = reload(battle)
    channel = FakeChannel("t-combat")
    refreshed = FakeInteraction(channel)
    run(Combat.refreshImage(game, f"refreshImage_{POS}", refreshed))
    ids = offered_ids(refreshed)
    assert "FCIDblue_drawReputation_1_101_1_blue" in ids
    assert "FCIDred_drawReputation_2_101_2_red" in ids

    # Refreshing while both prompts are visible must not permit two answers.
    run(Combat.refreshCombatPrompt(game, POS, channel))
    run(Combat.dontDrawReputation(game, "dontDrawReputation_101_1_blue", refreshed,
                                 player_helper(game, "blue")))
    run(Combat.drawReputation(game, "drawReputation_2_101_2_red", refreshed,
                             player_helper(game, "red")))
    track = game.get_player(2)["reputation_track"][:]
    bag = game.gamestate["reputation_tiles"][:]
    run(Combat.drawReputation(game, "drawReputation_1_101_1_blue", refreshed,
                             player_helper(game, "blue")))
    run(Combat.drawReputation(game, "drawReputation_2_101_2_red", refreshed,
                             player_helper(game, "red")))
    run(Combat.dontDrawReputation(game, "dontDrawReputation_101_2_red", refreshed,
                                 player_helper(game, "red")))
    assert game.get_player(2)["reputation_track"] == track
    assert game.gamestate["reputation_tiles"] == bag
    assert game.gamestate["queuedQuestions"] == []
    assert game.gamestate["queuedDraws"] == []

    channel = FakeChannel("t-combat")
    run(Combat.refreshCombatPrompt(reload(game), POS, channel))
    assert not any("reputation tiles here" in content for content, kwargs in channel.sent)
