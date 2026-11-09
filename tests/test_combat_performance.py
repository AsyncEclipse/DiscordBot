import os

import pytest

from helpers.CombatHelper import Combat
from tests.fakes import FakeChannel, FakeInteraction, POS, player_stats


def test_nested_save_batch_flushes_completed_changes_on_error(make_game, monkeypatch):
    game = make_game({"board": {"101": {}}})
    replacements = []
    replace = os.replace

    def record_replace(source, destination):
        replacements.append(destination)
        replace(source, destination)

    monkeypatch.setattr(os, "replace", record_replace)
    with pytest.raises(ValueError, match="resolution failed"):
        with game.batch_save():
            game.add_damage("blue-int", "101", 1)
            with game.batch_save():
                game.add_damage("blue-int", "101", 1)
            assert not replacements
            raise ValueError("resolution failed")
    assert len(replacements) == 1
    assert game.get_gamestate()["board"]["101"]["damage_tracker"] == {"blue-int": 2}
    game.add_damage("blue-int", "101", 1)
    assert len(replacements) == 2


def test_failed_serialization_preserves_previous_save(make_game, games_dir):
    game = make_game({"board": {}})
    previous = game.get_gamestate()
    game.gamestate["invalid"] = object()
    with pytest.raises(TypeError):
        game.update()
    assert game.get_gamestate() == previous
    assert sorted(path.name for path in games_dir.iterdir()) == ["t.json"]


def test_combat_reports_group_and_split_at_discord_limit(run):
    channel = FakeChannel()
    reports = ["first hit", "second hit"]
    run(Combat.sendCombatReports(channel, reports))
    assert channel.sent == [("first hit\nsecond hit", {})]
    assert reports == []
    reports = ["x" * 2100, "last hit"]
    run(Combat.sendCombatReports(channel, reports))
    assert all(len(content) <= 2000 for content, kwargs in channel.sent)
    assert "".join(content for content, kwargs in channel.sent[1:]) == "x" * 2100 + "\nlast hit"


def test_lethal_hit_saves_once_before_reporting(make_game, monkeypatch, run):
    game = make_game({
        "players": {"1": player_stats("hyd", color="blue"),
                    "2": player_stats("hyd", color="red")},
        "board": {POS: {"owner": 0, "sector": 101,
                        "player_ships": ["blue-int", "red-int"],
                        "attacker": "blue", "defender": "red"}},
    })
    replacements = []
    replace = os.replace

    def record_replace(source, destination):
        replacements.append(destination)
        replace(source, destination)

    monkeypatch.setattr(os, "replace", record_replace)
    reports = []
    interaction = FakeInteraction()
    run(Combat.assignHitTo(game, f"assignHitTo_{POS}_blue_red-int_6_5",
                           interaction, False, deferEnd=True, reports=reports))
    assert len(replacements) == 1
    assert "red-int" not in game.get_gamestate()["board"][POS]["player_ships"]
    assert len(reports) == 1
    assert not interaction.channel.sent


def test_failed_replacement_preserves_previous_save(make_game, games_dir, monkeypatch):
    game = make_game({"board": {}})
    previous = game.get_gamestate()
    game.gamestate["changed"] = True

    def fail_replace(source, destination):
        raise OSError("disk failure")

    monkeypatch.setattr(os, "replace", fail_replace)
    with pytest.raises(OSError, match="disk failure"):
        game.update()
    assert game.get_gamestate() == previous
    assert sorted(path.name for path in games_dir.iterdir()) == ["t.json"]
