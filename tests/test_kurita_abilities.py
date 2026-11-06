"""Kurita Prefecture species rules.

First shot is an opening split of the existing initiative prompt; the Battle Rep
adjustment rides the existing reputation draw and scoring; Elite Warriors and the
extra starbase hull are the printed off-board blueprint values.
"""
import pytest

from Buttons.Reputation import ReputationButtons
from helpers import FactionData
from helpers.CombatHelper import Combat
from helpers.DrawHelper import DrawHelper
from tests.fakes import FakeInteraction, POS, board_tile, offered_ids, player_helper, player_stats


def _stats(faction, color):
    stats = player_stats(faction, color=color)
    for ship in ("interceptor", "cruiser", "dread", "starbase"):
        stats[f"{ship}_parts"] = ["empty"]
    return stats


def _combat_game(make_game, blue="kur", red="hyd", ships=("blue-cru", "red-cru")):
    game = make_game({
        "player_count": 2,
        "players": {"1": _stats(blue, "blue"), "2": _stats(red, "red")},
        "board": board_tile(ships),
        "reputation_tiles": [3],
    })
    return game


def _start_pairing(game, blue_ships, red_ships, owner=0):
    tile = game.gamestate["board"][POS]
    tile["player_ships"] = list(blue_ships) + list(red_ships)
    tile["owner"] = owner
    game.setAttackerAndDefender(["red"], ["blue"], POS)
    tile["firstShotSide"] = Combat.firstShotSideOf(game, tile["attacker"], tile["defender"])
    tile["firstShotPhase"] = "opponent" if tile["firstShotSide"] else None
    tile["currentSpeed"] = None
    tile["currentRoller"] = None
    game.update()
    return tile


def _prompts(game, run, channel, count):
    sequence = []
    for _ in range(count):
        run(Combat.promptNextSpeed(game, POS, channel, False))
        tile = game.gamestate["board"][POS]
        sequence.append((tile["currentSpeed"], tile["currentRoller"]))
    return sequence


def test_first_shot_opponent_shoots_before_kurita(make_game, run):
    game = _combat_game(make_game)
    game.get_player(1).update({"base_cruiser_speed": 5, "base_dread_speed": 3})
    game.get_player(2).update({"base_cruiser_speed": 4, "base_dread_speed": 2})
    _start_pairing(game, ["blue-cru", "blue-drd"], ["red-cru", "red-drd"])

    sequence = _prompts(game, run, FakeInteraction().channel, 4)

    assert sequence == [(4, "red"), (2, "red"), (5, "blue"), (3, "blue")]
    labels = [button.label for button in Combat.getCombatButtons(game, POS).children]
    assert labels[:4] == ["(Attacker) Roll Initative 4 Ships",
                          "(Attacker) Roll Initative 2 Ships",
                          "(Defender) Roll Initative 5 Ships",
                          "(Defender) Roll Initative 3 Ships"]


def test_refresh_preserves_the_current_first_shot_turn(make_game, run):
    game = _combat_game(make_game)
    game.get_player(1)["base_cruiser_speed"] = 5
    game.get_player(2)["base_cruiser_speed"] = 4
    tile = _start_pairing(game, ["blue-cru"], ["red-cru"])
    channel = FakeInteraction().channel
    assert _prompts(game, run, channel, 1) == [(4, "red")]

    run(Combat.refreshCombatPrompt(game, POS, channel))

    assert (tile["currentSpeed"], tile["currentRoller"]) == (4, "red")
    assert tile["firstShotPhase"] == "opponent"
    assert _prompts(game, run, channel, 1) == [(5, "blue")]


def test_first_shot_round_two_returns_to_normal_initiative(make_game, run):
    game = _combat_game(make_game)
    game.get_player(1).update({"base_interceptor_speed": 6, "base_cruiser_speed": 5})
    game.get_player(1)["interceptor_parts"] = ["iom"]
    game.get_player(2).update({"base_cruiser_speed": 4})
    _start_pairing(game, ["blue-int", "blue-cru"], ["red-cru"])

    sequence = _prompts(game, run, FakeInteraction().channel, 5)

    assert sequence == [(4, "red"), (105, "blue"), (6, "blue"), (5, "blue"), (6, "blue")]
    assert game.gamestate["board"][POS]["firstShotPhase"] is None


def test_first_shot_mirror_uses_normal_order(make_game, run):
    game = _combat_game(make_game, blue="kur", red="kur")
    game.get_player(1).update({"base_cruiser_speed": 5})
    game.get_player(2).update({"base_cruiser_speed": 4})
    tile = _start_pairing(game, ["blue-cru"], ["red-cru"])

    assert tile["firstShotSide"] == []
    assert tile["firstShotPhase"] is None
    assert _prompts(game, run, FakeInteraction().channel, 1) == [(5, "blue")]


def test_first_shot_delays_only_kurita_in_an_alliance(make_game):
    game = _combat_game(make_game)
    game.gamestate["players"]["3"] = _stats("hyd", "green")
    game.formAlliance("nova", ["blue", "green"])
    game.gamestate["board"][POS]["player_ships"] = ["blue-cru", "green-cru", "red-cru"]
    game.setAttackerAndDefender(["red"], ["blue", "green"], POS)

    tile = game.gamestate["board"][POS]
    assert Combat.findSidesInTile(game, POS) == [["blue", "green"], ["red"]]
    assert Combat.firstShotSideOf(game, tile["attacker"], tile["defender"]) == ["blue"]


def test_start_combat_resets_the_opening_for_each_pairing(make_game, run):
    game = _combat_game(make_game)
    tile = game.gamestate["board"][POS]
    tile["firstShotPhase"] = "kurita"
    tile["firstShotSide"] = ["blue"]
    tile["currentSpeed"] = 5
    tile["currentRoller"] = "blue"

    run(Combat.startCombat(game, FakeInteraction().channel, POS))

    assert tile["firstShotSide"] == ["blue"]
    assert tile["firstShotPhase"] == "opponent"


def test_other_factions_have_normal_order(make_game, run):
    game = _combat_game(make_game, blue="hyd", red="eri")
    game.get_player(1).update({"base_cruiser_speed": 5})
    game.get_player(2).update({"base_cruiser_speed": 4})
    tile = _start_pairing(game, ["blue-cru"], ["red-cru"])

    assert tile["firstShotPhase"] is None
    assert _prompts(game, run, FakeInteraction().channel, 1) == [(5, "blue")]


# --- Battle Reputation ---------------------------------------------------------

def _winner_game(make_game, survivors, owner, blue_ships=(), red_ships=()):
    game = _combat_game(make_game)
    tile = game.gamestate["board"][POS]
    tile["player_ships"] = list(blue_ships) + list(red_ships) + [f"{color}-cru" for color in survivors]
    tile["owner"] = owner
    tile["combatants"] = ["blue", "red"]
    tile["sector"] = 101
    tile["vp"] = 0
    tile["artifact"] = 0
    tile["attacker"] = ["red"]
    tile["defender"] = ["blue"]
    game.gamestate["reputation_tiles"] = [3]
    game.update()
    return game


def _draw(game, interaction, color, run):
    button = next(cid for cid in offered_ids(interaction)
                  if cid.startswith(f"FCID{color}_drawReputation_"))
    run(Combat.drawReputation(game, button.replace(f"FCID{color}_", "", 1), interaction,
                              player_helper(game, color)))
    return game.getPlayerObjectFromColor(color)


def test_winning_battle_adds_one_to_the_drawn_battle_rep(make_game, run):
    game = _winner_game(make_game, ["blue"], owner="blue")
    interaction = FakeInteraction()
    run(Combat.declareAWinner(game, interaction, POS))

    player = _draw(game, interaction, "blue", run)

    assert any("drew 1 reputation tiles (+1 for the battle)" in content
               for content, _kwargs in interaction.channel.sent)
    assert player["reputationBonuses"] == {"0": 1}
    assert DrawHelper(game.gamestate).get_public_points(player, False) == 0
    game.gamestate["gameEnded"] = True
    # The drawn reputation tile (3) plus the winning battle marker (+1).
    assert DrawHelper(game.gamestate).get_public_points(player, False) == 4


def test_losing_battle_subtracts_one(make_game, run):
    game = _winner_game(make_game, ["red"], owner="red")
    interaction = FakeInteraction()
    run(Combat.declareAWinner(game, interaction, POS))

    player = _draw(game, interaction, "blue", run)

    assert player["reputationBonuses"] == {"0": -1}


def test_declined_draw_leaves_no_battle_rep(make_game, run):
    game = _winner_game(make_game, ["blue"], owner="blue")
    interaction = FakeInteraction()
    run(Combat.declareAWinner(game, interaction, POS))
    button = next(cid for cid in offered_ids(interaction)
                  if cid.startswith("FCIDblue_dontDrawReputation_"))
    run(Combat.dontDrawReputation(game, button.replace("FCIDblue_", "", 1), interaction,
                                  player_helper(game, "blue")))

    player = game.getPlayerObjectFromColor("blue")
    assert "reputationBonuses" not in player
    assert game.gamestate["battleRepAdjustments"] == {}


def test_full_track_replacement_keeps_the_adjustment(make_game, run):
    game = make_game({"players": {"1": _stats("kur", "blue")}, "reputation_tiles": [5]})
    game.get_player(1)["reputation_track"] = [1, 2, 3, 4]

    run(ReputationButtons.resolveGainingReputation(game, 1, FakeInteraction(),
                                                   player_helper(game, "blue"), False,
                                                   battle_rep_adjustment=1))

    player = game.getPlayerObjectFromColor("blue")
    assert player["reputation_track"][0] == 5
    assert player["reputationBonuses"] == {"0": 1}


def test_returned_tile_drops_its_battle_marker(make_game, run):
    game = make_game({"players": {"1": _stats("kur", "blue")}, "reputation_tiles": [3]})
    game.get_player(1)["reputation_track"] = [4, 4, 4, 4]

    run(ReputationButtons.resolveGainingReputation(game, 1, FakeInteraction(),
                                                   player_helper(game, "blue"), False,
                                                   battle_rep_adjustment=1))

    player = game.getPlayerObjectFromColor("blue")
    assert player["reputation_track"] == [4, 4, 4, 4]
    assert FactionData.battle_rep_points(player) == 0


def test_replacement_compares_tile_plus_marker(make_game, run):
    # 3 (+1 won) beats a 3 (-1 lost) slot, even though the bare tiles tie
    game = make_game({"players": {"1": _stats("kur", "blue")}, "reputation_tiles": [3]})
    player = game.get_player(1)
    player["reputation_track"] = [4, 3, 4, 4]
    player["reputationBonuses"] = {"1": -1, "2": 1}

    run(ReputationButtons.resolveGainingReputation(game, 1, FakeInteraction(),
                                                   player_helper(game, "blue"), False,
                                                   battle_rep_adjustment=1))

    player = game.getPlayerObjectFromColor("blue")
    assert player["reputation_track"] == [4, 3, 4, 4]
    assert player["reputationBonuses"] == {"1": 1, "2": 1}
    assert FactionData.battle_rep_points(player) == 2


def test_replacing_a_marked_tile_with_a_plain_draw_drops_the_marker(make_game, run):
    game = make_game({"players": {"1": _stats("kur", "blue")}, "reputation_tiles": [4]})
    player = game.get_player(1)
    player["reputation_track"] = [4, 2, 4, 4]
    player["reputationBonuses"] = {"1": 1}

    run(ReputationButtons.resolveGainingReputation(game, 1, FakeInteraction(),
                                                   player_helper(game, "blue"), False))

    player = game.getPlayerObjectFromColor("blue")
    assert player["reputation_track"] == [4, 4, 4, 4]
    assert "reputationBonuses" not in player


def test_queued_battle_rep_keeps_its_adjustment(make_game, run):
    game = make_game({
        "players": {"1": _stats("kur", "blue"), "2": _stats("kur", "red")},
        "reputation_tiles": [3, 4],
        "roundNum": 1,
        "queuedDraws": [[101, 1, "blue", 1], [102, 1, "red", 1]],
        "queuedQuestions": [],
        "tilesToResolve": [],
        "battleRepAdjustments": {"101-1-blue": 1, "102-1-red": -1},
    })

    run(Combat.resolveQueue(game, FakeInteraction(), forcedResolve=True))

    assert FactionData.battle_rep_points(game.getPlayerObjectFromColor("blue")) == 1
    assert FactionData.battle_rep_points(game.getPlayerObjectFromColor("red")) == -1
    assert game.gamestate["battleRepAdjustments"] == {}


def test_battle_rep_side_win_with_destroyed_player(make_game, run):
    game = _winner_game(make_game, ["green"], owner="green", red_ships=["red-cru"])
    game.gamestate["players"]["3"] = _stats("hyd", "green")
    game.formAlliance("nova", ["blue", "green"])
    interaction = FakeInteraction()
    run(Combat.declareAWinner(game, interaction, POS))

    player = _draw(game, interaction, "blue", run)

    assert FactionData.battle_rep_points(player) == 1


# --- Retreat ------------------------------------------------------------------

def _retreat_game(make_game, faction):
    game = make_game({
        "player_count": 2,
        "players": {"1": _stats(faction, "blue"), "2": _stats("hyd", "red")},
        "board": board_tile(["blue-cru", "blue-drd"]),
    })
    game.get_player(1).update({"base_cruiser_speed": 5, "base_dread_speed": 3})
    tile = game.gamestate["board"][POS]
    tile["owner"] = "blue"
    tile["attacker"] = ["red"]
    tile["defender"] = ["blue"]
    tile["ships_destroyed_by_blue"] = ["int"]
    game.update()
    return game


@pytest.mark.parametrize("faction, penalty", [("kur", True), ("hyd", False)])
def test_retreating_any_ship_draws_no_battle_rep(make_game, run, faction, penalty):
    game = _retreat_game(make_game, faction)

    run(Combat.startToRetreatUnits(game, f"startToRetreatUnits_{POS}_blue_5",
                                   FakeInteraction()))

    tile = game.gamestate["board"][POS]
    assert ("retreatPenaltyblue" in tile) is penalty
    expected = 0 if penalty else 2  # the default draw plus the destroyed interceptor
    assert game.getReputationTilesToDraw(POS, "blue") == expected


# --- Data-only printed stats --------------------------------------------------

def test_traitor_card_is_minus_four_for_kurita():
    game = {"board": {}, "players": {}}
    drawing = DrawHelper(game)
    assert drawing.get_public_points(player_stats("kur", color="blue", traitor=True), False) == -4
    assert drawing.get_public_points(player_stats("hyd", color="blue", traitor=True), False) == -2
    assert drawing.get_public_points(player_stats("rho", color="blue", traitor=True), False) == 0


def test_retreat_penalty_ends_with_the_pairing(make_game, run):
    game = _winner_game(make_game, ["red"], owner="red")
    game.gamestate["board"][POS]["retreatPenaltyblue"] = True
    interaction = FakeInteraction()
    run(Combat.declareAWinner(game, interaction, POS))
    assert not any(cid.startswith("FCIDblue_drawReputation_") for cid in offered_ids(interaction))
    assert "retreatPenaltyblue" not in game.gamestate["board"][POS]
    assert game.getReputationTilesToDraw(POS, "blue") == 1


def test_a_combat_roll_names_each_computer_source(make_game, no_random, run):
    game = _combat_game(make_game)
    game.gamestate["players"]["1"]["cruiser_parts"] = ["elc", "ioc", "nus", "hul", "nud"]
    game.update()
    _start_pairing(game, ["blue-cru"], ["red-cru"])
    inter = FakeInteraction()
    no_random([3])
    run(Combat.rollDice(game, f"rollDice_{POS}_blue_2_deleteMsg", inter))

    assert any("+2 computer (+1 Electron Computer, +1 Elite Warriors)" in content
               for content, _kwargs in inter.channel.sent)
