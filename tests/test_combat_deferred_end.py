"""A deferred multi-target hit must still end the pairing when it kills the last ship.

Carapace missiles and rift dice defer combat-end checks until their target button is
pressed. If that hit removes the last ship of a side, the deferred path must call
`checkCombatEnd`; otherwise the pairing never advances.
"""
from helpers.CombatHelper import Combat
from tests.fakes import FakeInteraction, POS, offered_ids, player_stats


def test_deferred_multi_target_hit_that_ends_the_side_calls_check_combat_end(make_game, monkeypatch, run):
    blue = player_stats("hyd", color="blue", name="Hydran Progress")
    red = player_stats("hyd", color="red", name="Hydran Progress")
    game = make_game({
        "advanced_ai": 0,
        "wa_ai": 0,
        "player_count": 2,
        "players": {"1": blue, "2": red},
        "board": {POS: {"owner": 0, "sector": 101, "disctile": 0,
                        "player_ships": ["red-int"],
                        "attacker": "blue", "defender": "red",
                        "combatants": ["blue", "red"]}},
    })

    checked = []
    prompted = []

    async def check(game, interaction, pos, old_length):
        checked.append((pos, old_length))

    async def prompt(*args, **kwargs):
        prompted.append(True)

    monkeypatch.setattr(Combat, "checkCombatEnd", staticmethod(check))
    monkeypatch.setattr(Combat, "promptNextSpeed", staticmethod(prompt))

    run(Combat.assignHitTo(game, f"assignHitTo_{POS}_blue_red-int_6_5_defer",
                           FakeInteraction(), True))

    assert "red-int" not in game.gamestate["board"][POS]["player_ships"]
    assert checked == [(POS, 1)]
    assert not prompted


def test_mixed_rift_and_ion_salvo_ends_the_combat_once(make_game, no_random, run):
    """A rift die defers the salvo's combat-end check; a later ion killing hit must
    not declare the winner a second time, which offered an extra reputation draw."""
    blue = player_stats("hyd", color="blue", name="Hydran Progress",
                        cost_cruiser=5, base_cruiser_speed=4, base_cruiser_comp=1,
                        cruiser_parts=["rican", "ioc", "hul", "hul", "hul"])
    red = player_stats("hyd", color="red", name="Hydran Progress")
    game = make_game({
        "advanced_ai": 0,
        "wa_ai": 0,
        "rift_cannon": 1,
        "player_count": 2,
        "players": {"1": blue, "2": red},
        "board": {POS: {"owner": 0, "sector": 101, "disctile": 0,
                        "player_ships": ["blue-cru", "ai-anc"],
                        "attacker": "blue", "defender": "ai",
                        "combatants": ["blue", "ai"]}},
    })

    no_random([4, 5])  # rift 4 damages the Ancient, ion 5 kills it
    inter = FakeInteraction()
    run(Combat.rollDice(game, f"rollDice_{POS}_blue_4_deleteMsg", inter))

    draws = [cid for cid in offered_ids(inter) if "drawReputation" in cid]
    assert draws == ["FCIDblue_drawReputation_2_101_1_blue"]
