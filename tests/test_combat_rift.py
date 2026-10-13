"""Regression tests for Rift Cannon combat resolution.

Player bug reports:
1. Backfire damage is assigned one die at a time instead of as a volley, so a
   Ship type's backfire is never used to destroy a ship.
2. In a 3+ player sector, hits are aimed at whichever player happens to be
   last in the mutable ship order, so a salvo can spill onto a third player.
3. A backfire that destroys the firing ship cancels that same die's damage to
   the target (a roll of 6 must still deal 3 to the target), and a mutual
   destruction must not be scored as a win.

Backfire is pooled per Ship type (dice of one type roll simultaneously), but a
volley's backfire may be assigned to any of the owner's rift-armed ships, so a
cruiser's two backfires can still destroy an interceptor.
"""
from helpers.CombatHelper import Combat
from tests.fakes import FakeInteraction, POS, offered_labels, player_stats


def _player(color, pid, int_parts, cru_parts, name="Hydran Progress"):
    stats = player_stats("hyd", color=color, name=name,
                         cost_interceptor=1, cost_cruiser=5,
                         base_interceptor_speed=4, base_cruiser_speed=4,
                         interceptor_parts=int_parts, cruiser_parts=cru_parts,
                         ship_stock=[7, 4, 2, 4], colony_ships=3)
    return pid, stats


def _game(make_game, players, player_ships, extra=None):
    board = {
        POS: {
            "owner": 0,
            "sector": 101,
            "disctile": 0,
            "player_ships": player_ships,
            "attacker": "blue",
            "defender": "red",
            "combatants": [p["color"] for _, p in players],
        }
    }
    if extra:
        board[POS].update(extra)
    return make_game({
        "advanced_ai": 0,
        "wa_ai": 0,
        "player_count": len(players),
        "rift_cannon": 1,
        "players": dict(players),
        "board": board,
    })


def _damage(game):
    return game.gamestate["board"][POS].get("damage_tracker", {})


def test_lyra_declined_rerolls_pool_backfire_per_ship_type(make_game, no_random, quiet_combat, run):
    """A Lyra player who declines every reroll must still get the pooled
    per-Ship-type backfire (same outcome as the non-Lyra case)."""
    players = [_player("blue", "1", ["rican", "hul"],
                       ["rican", "rican", "hul", "hul", "hul"], name="Enlightened of Lyra"),
               _player("red", "2", ["rican"], ["rican", "hul"])]
    game = _game(make_game, players, ["blue-cru", "blue-int", "red-int"])
    no_random([1, 1, 1])
    inter = FakeInteraction()

    run(Combat.rollDice(game, f"rollDice_{POS}_blue_4_deleteMsg", inter))
    pending = game.gamestate["board"][POS]["pendingRiftDice"]
    assert sorted(pending.values()) == ["cru", "cru", "int"]

    for die_id in list(pending):
        run(Combat.resolveLyraRiftRoll(
            game, f"resolveLyraRiftRoll_{POS}_blue_1_4_0_{die_id}", inter))

    assert "blue-int" not in game.gamestate["board"][POS]["player_ships"]
    assert _damage(game).get("blue-cru") == 1


def test_rift_six_still_damages_target_when_backfire_destroys_shooter(
        make_game, no_random, quiet_combat, run, monkeypatch):
    """Bug 3: a 6 backfires for 1 and deals 3 to the target; the target damage
    must not be cancelled by the shooter dying to the backfire, and a mutual
    destruction is not a win (no discovery/influence offered)."""
    players = [_player("blue", "1", ["rican"], ["rican", "hul"]),
               _player("red", "2", ["rican"], ["rican", "hul"])]
    game = _game(make_game, players, ["blue-int", "ai-anc"],
                 extra={"attacker": "blue", "defender": "ai", "combatants": ["blue", "ai"]})
    drawn = {}
    original = game.getReputationTilesToDraw
    monkeypatch.setattr(game, "getReputationTilesToDraw",
                        lambda position, color: drawn.setdefault(color, original(position, color)))
    no_random([6])
    inter = FakeInteraction()

    run(Combat.rollDice(game, f"rollDice_{POS}_blue_4_deleteMsg", inter))

    assert "ai-anc" not in game.gamestate["board"][POS]["player_ships"]
    assert "blue-int" not in game.gamestate["board"][POS]["player_ships"]
    assert drawn.get("blue") == 2
    assert "Explore Discovery Tile" not in offered_labels(inter)
    assert "Place Influence" not in offered_labels(inter)


def test_multi_opponent_salvo_does_not_spill_onto_third_player(make_game):
    """Bug 2: with three players in the sector the opponent is chosen by list
    position; once the real opponent is eliminated the next hit must not jump
    to the third player."""
    players = [_player("red", "1", ["rican"], ["rican", "hul"]),
               _player("blue", "2", ["rican"], ["rican", "hul"]),
               _player("green", "3", ["rican"], ["rican", "hul"])]
    game = _game(make_game, players, ["red-cru", "blue-cru", "green-cru"],
                 extra={"attacker": "blue", "defender": "green",
                        "combatants": ["red", "blue", "green"]})
    ships = game.gamestate["board"][POS]["player_ships"][:]
    assert Combat.getOpponentUnitsThatCanBeHit(game, "blue", ships, 6, 0, POS, 4) == ["green-cru"]

    game.gamestate["board"][POS]["player_ships"].remove("green-cru")
    ships = game.gamestate["board"][POS]["player_ships"][:]
    hits = Combat.getOpponentUnitsThatCanBeHit(game, "blue", ships, 6, 0, POS, 4)
    assert not any(s.startswith("red") for s in hits)
