from copy import deepcopy

import pytest

from helpers.GamestateHelper import GamestateHelper


@pytest.mark.parametrize("relation", ["diplomacy", "minor"])
def test_relations_preserve_atlantians_reputation_only_slots(relation, monkeypatch):
    player = {"name": "Atlantians", "color": "blue", "reputation_track": [1, 2, 4, 3]}
    other = {"name": "Terran Federation", "color": "red", "reputation_track": ["amb", "mixed"]}
    game = object.__new__(GamestateHelper)
    game.gamestate = {"players": {"1": deepcopy(player), "2": other},
                      "reputation_tiles": [], "minor_species": ["Point Per Ambassador"]}
    monkeypatch.setattr(game, "update", lambda: None)
    if relation == "diplomacy":
        game.formRelationsBetween(game.gamestate["players"]["1"], other)
    else:
        game.formMinorSpeciesRelations(game.gamestate["players"]["1"], "Point Per Ambassador")
    assert game.gamestate["players"]["1"]["reputation_track"][:3] == [1, 2, 4]
    assert game.gamestate["players"]["1"]["reputation_track"][3].startswith("mixed-")
    assert game.gamestate["reputation_tiles"] == [3]


def test_returning_reputation_preserves_slot_type(monkeypatch):
    player = {"name": "Atlantians", "color": "blue", "reputation_track": [1, 2, 4, 3]}
    game = object.__new__(GamestateHelper)
    game.gamestate = {"players": {"1": player}, "reputation_tiles": []}
    monkeypatch.setattr(game, "update", lambda: None)
    game.returnReputation(1, player)
    game.returnReputation(3, player)
    assert player["reputation_track"] == ["rep", 2, 4, "mixed"]
    assert game.gamestate["reputation_tiles"] == [1, 3]


def test_a_full_track_refuses_relations(monkeypatch):
    taken = ["rep", "rep", "mixed-terran_federation-red", "mixed-minor-The Sentinels"]
    player = {"name": "Atlantians", "color": "blue", "reputation_track": deepcopy(taken)}
    other = {"name": "Terran Federation", "color": "red", "reputation_track": ["amb", "mixed"]}
    game = object.__new__(GamestateHelper)
    game.gamestate = {"players": {"1": player, "2": other}, "reputation_tiles": [],
                      "minor_species": ["The Sentinels"]}
    monkeypatch.setattr(game, "update", lambda: None)

    assert game.formRelationsBetween(player, other) is False
    assert game.formMinorSpeciesRelations(player, "The Sentinels") is False
    assert player["reputation_track"] == taken
    assert other["reputation_track"] == ["amb", "mixed"]
    assert game.gamestate["minor_species"] == ["The Sentinels"]
