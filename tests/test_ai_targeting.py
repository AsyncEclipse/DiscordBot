"""Regression tests for whole-salvo AI target selection."""
from types import SimpleNamespace

import helpers.CombatHelper as combat_helper
from helpers.CombatHelper import Combat
from tests.fakes import FakeInteraction, POS


def test_ai_allocates_two_hits_to_destroy_largest_ship(make_game, no_random, run, monkeypatch):
    """Two 1-damage hits should be pooled to destroy the largest ship.

    The rulebook requires assigning the salvo to destroy ships from largest
    to smallest when possible.
    """
    players = {
        1: {"color": "red", "player_name": "Red", "name": "Red", "ship_stock": [0, 0, 0, 0]},
    }
    game = make_game({
        "advanced_ai": False,
        "wa_ai": False,
        "player_count": 1,
        "players": players,
        "board": {
            POS: {
                "owner": 0,
                "sector": 101,
                "disctile": 0,
                "player_ships": ["ai-anc", "red-cru", "red-int"],
                "attacker": "ai",
                "defender": "red",
                "combatants": ["ai", "red"],
            }
        },
    })

    def ship_model(_player, ship_type):
        return SimpleNamespace(
            speed=4,
            computer=0,
            shield=1 if ship_type == "cru" else 0,
            hull=1 if ship_type == "cru" else 0,
            cost=5 if ship_type == "cru" else 1,
            missile=[],
            dice=[],
        )

    monkeypatch.setattr(combat_helper, "PlayerShip", ship_model)

    async def do_nothing(*_args, **_kwargs):
        return None

    monkeypatch.setattr(Combat, "promptNextSpeed", staticmethod(do_nothing))
    shield_limited_allocation = Combat.getAIHitAllocation(
        game, "ai", POS, 2, [[5, 1, "yellow"], [6, 1, "yellow"]], computer=1)
    assert shield_limited_allocation == ["red-int", "red-cru"]

    no_random([6, 6])

    run(Combat.rollDiceAI(game, f"rollDice_{POS}_ai_2_deleteMsg", FakeInteraction()))

    remaining_ships = game.gamestate["board"][POS]["player_ships"]
    assert "red-cru" not in remaining_ships
    assert "red-int" in remaining_ships


def test_ai_destroys_smaller_ship_after_larger_ship(make_game, monkeypatch):
    game = targeting_game(make_game, monkeypatch, ["red-cru", "red-int"])
    allocation = Combat.getAIHitAllocation(game, "ai", POS, 2, [[6, 1]] * 3, 0)
    assert allocation.count("red-cru") == 2
    assert allocation.count("red-int") == 1


def test_ai_does_not_target_destroyed_ship(make_game, monkeypatch):
    game = targeting_game(make_game, monkeypatch, ["red-cru"])
    allocation = Combat.getAIHitAllocation(game, "ai", POS, 2, [[6, 1]] * 3, 0)
    assert allocation == ["red-cru", "red-cru", None]


def test_ai_can_destroy_multiple_ships_of_same_type(make_game, monkeypatch):
    game = targeting_game(make_game, monkeypatch, ["red-cru", "red-cru", "red-int"])
    allocation = Combat.getAIHitAllocation(game, "ai", POS, 2, [[6, 1]] * 5, 0)
    assert allocation.count("red-cru") == 4
    assert allocation.count("red-int") == 1


def targeting_game(make_game, monkeypatch, ships):
    game = make_game({
        "players": {1: {"color": "red"}},
        "board": {POS: {"player_ships": ["ai-anc"] + ships}},
    })
    monkeypatch.setattr(Combat, "getOpponentUnitsThatCanBeHit", staticmethod(
        lambda *args: list(dict.fromkeys(ships))))
    monkeypatch.setattr(combat_helper, "PlayerShip", lambda player, ship_type: SimpleNamespace(
        hull=1 if ship_type == "cru" else 0, cost=5 if ship_type == "cru" else 1))
    return game
