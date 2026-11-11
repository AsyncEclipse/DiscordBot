"""Regression tests for the Lyra colony-ship reroll.

Player bug reports:
1. Answering (or ignoring) a Lyra reroll did not hold the initiative: the bot
   prompted the opponent's initiative while the reroll prompt was unanswered.
2. A single die that missed produced one reroll prompt per point of damage it
   would have dealt (up to four for an Antimatter Cannon die), and a bombing
   reroll could never destroy population because the hit check used speed 3.
"""
from helpers.CombatHelper import Combat
from helpers.PlayerHelper import PlayerHelper
from tests.fakes import FakeInteraction, POS, offered_ids, player_stats


def _player(color, pid, int_parts, cru_parts, name="Enlightened of Lyra"):
    stats = player_stats("hyd", color=color, name=name,
                         cost_interceptor=1, cost_cruiser=5,
                         base_interceptor_speed=4, base_cruiser_speed=4,
                         interceptor_parts=int_parts, cruiser_parts=cru_parts,
                         ship_stock=[7, 4, 2, 4], colony_ships=3)
    return pid, stats


def _game(make_game, players, player_ships, extra=None):
    tile = {"owner": 0, "sector": 101, "disctile": 0, "player_ships": player_ships,
            "attacker": "blue", "defender": "red", "combatants": ["blue", "red"]}
    if extra:
        tile.update(extra)
    return make_game({"advanced_ai": 0, "wa_ai": 0, "player_count": len(players),
                      "rift_cannon": 1, "players": dict(players), "board": {POS: tile}})


def _lyra_ships():
    """Lyra with ion cannons, so the dice are ordinary (yellow) dice."""
    return [_player("blue", "1", ["ioc", "hul"], ["ioc", "hul"]),
            _player("red", "2", ["ioc", "hul"], ["ioc", "hul"], name="Hydran Progress")]


def _token(game):
    """The one unanswered Lyra reroll prompt."""
    pending = game.gamestate["board"][POS]["lyraRerollPending"]
    assert len(pending) == 1
    return next(iter(pending))


def test_lyra_reroll_holds_the_initiative(make_game, no_random, quiet_combat, run):
    """Bug 1: a missed die with a reroll offered must not hand the initiative on
    until the Lyra player answers. Declining then moves it on exactly once."""
    game = _game(make_game, _lyra_ships(), ["blue-int", "red-int"])
    no_random([2])
    inter = FakeInteraction()

    run(Combat.rollDice(game, f"rollDice_{POS}_blue_4_deleteMsg", inter))

    board = game.gamestate["board"][POS]
    assert board["currentSpeed"] == 4
    assert board["currentRoller"] == "blue"
    token = _token(game)
    assert "FCIDred_rollDice_101_red_4_deleteMsg" not in offered_ids(inter)

    run(Combat.declineLyraReroll(game, inter, POS, token))

    board = game.gamestate["board"][POS]
    assert not board["lyraRerollPending"]
    assert board["currentRoller"] == "red"
    assert "FCIDred_rollDice_101_red_4_deleteMsg" in offered_ids(inter)


def test_lyra_reroll_hit_then_hands_the_initiative_on(make_game, no_random, quiet_combat, run):
    """Bug 1: a rerolled die that hits resolves its damage at the Lyra player's
    initiative and only then offers the opponent the next step."""
    game = _game(make_game, _lyra_ships(), ["blue-int", "red-int"])
    no_random([2, 6])
    inter = FakeInteraction()
    run(Combat.rollDice(game, f"rollDice_{POS}_blue_4_deleteMsg", inter))

    run(Combat.resolveLyraReroll(game, inter, POS, _token(game)))

    board = game.gamestate["board"][POS]
    assert board.get("damage_tracker", {}).get("red-int") == 1
    assert not board["lyraRerollPending"]
    assert board["currentRoller"] == "red"
    assert "FCIDred_rollDice_101_red_4_deleteMsg" in offered_ids(inter)


def test_lyra_bombing_miss_offers_one_reroll(make_game, no_random, quiet_combat, run):
    """Bug 2: one Antimatter Cannon die that misses is one reroll prompt, not one
    per point of damage it would have dealt."""
    players = [_player("blue", "1", ["ioc", "hul"], ["anc", "hul"]),
               _player("red", "2", ["ioc", "hul"], ["ioc", "hul"], name="Hydran Progress")]
    game = _game(make_game, players, ["blue-cru"],
                 extra={"owner": "red", "money_pop": [1], "science_pop": [1], "material_pop": [1]})
    no_random([2])
    inter = FakeInteraction()

    run(Combat.rollDice(game, f"rollDice_{POS}_blue_1000_deleteMsg", inter))

    rerolls = [i for i in offered_ids(inter) if "lyraReroll_" in i]
    assert len(rerolls) == 1
    assert len(game.gamestate["board"][POS]["lyraRerollPending"]) == 1


def test_lyra_bombing_reroll_can_hit_population(make_game, no_random, quiet_combat, run):
    """Bug 2: a bombing reroll must be judged at the bombing initiative, so a 6
    offers population targets and kills every cube its damage allows."""
    players = [_player("blue", "1", ["ioc", "hul"], ["anc", "hul"]),
               _player("red", "2", ["ioc", "hul"], ["ioc", "hul"], name="Hydran Progress")]
    game = _game(make_game, players, ["blue-cru"],
                 extra={"owner": "red", "money_pop": [1], "science_pop": [1], "material_pop": [1]})
    no_random([2, 6])
    inter = FakeInteraction()
    run(Combat.rollDice(game, f"rollDice_{POS}_blue_1000_deleteMsg", inter))

    run(Combat.resolveLyraReroll(game, inter, POS, _token(game)))

    # A red direct hit deals 4 damage, so it offers four population hits.
    assert len([i for i in offered_ids(inter) if "killPop" in i]) == 12
    assert not game.gamestate["board"][POS]["lyraRerollPending"]
    assert "FCIDred_rollDice_101_red_4_deleteMsg" not in offered_ids(inter)
