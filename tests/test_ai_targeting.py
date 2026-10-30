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
