"""The combat message lists every initiative step. Pressing one out of order must not
skip the step the battle is actually waiting for (a pending missile salvo).
"""
import pytest

from commands.tile_commands import TileCommands
from helpers.CombatHelper import Combat
from tests.fakes import FakeChannel, FakeInteraction, POS, board_tile, offered_ids, player_stats, players, reload


def missile_battle(make_game):
    game = make_game({"player_count": 2, "players": players("blue", "red"),
                      "board": board_tile(["blue-cru", "red-cru"], 0)})
    player = game.get_player_from_color("blue")
    game.gamestate["players"][str(player)]["cruiser_parts"] = ["ioc", "plm", "nus", "nud", "hul"]
    game.update()
    return game


def speeds(game):
    return Combat.getBothCombatantShipsBySpeed(game, ["red"], ["blue"],
                                               game.gamestate["board"][POS]["player_ships"], POS)


def test_a_later_card_step_does_not_skip_the_pending_missile_step(make_game, run):
    game = missile_battle(make_game)
    interaction = FakeInteraction()
    game.setAttackerAndDefender(["red"], ["blue"], POS)
    run(Combat.promptNextSpeed(game, POS, interaction.channel, False))

    tile = game.gamestate["board"][POS]
    pending = (tile["currentSpeed"], tile["currentRoller"])
    assert pending[0] > 99, pending          # the battle is waiting for a missile salvo

    ships_step = next(pair for pair in speeds(game) if pair[0] < 90)
    interaction.channel.sent.clear()
    run(Combat.rollDice(game, f"rollDice_{POS}_{ships_step[1]}_{ships_step[0]}_deleteMsg", interaction))

    assert (tile["currentSpeed"], tile["currentRoller"]) == pending
    assert [ships_step[0], ships_step[1]] not in tile.get("rolledSteps", [])
    assert not any("rolled the following" in content
                   for content, _kwargs in interaction.channel.sent if content)
    assert any("current" in content for content, _kwargs in interaction.channel.sent if content)


def test_the_pending_step_itself_still_rolls(make_game, run):
    game = missile_battle(make_game)
    interaction = FakeInteraction()
    game.setAttackerAndDefender(["red"], ["blue"], POS)
    run(Combat.promptNextSpeed(game, POS, interaction.channel, False))

    tile = game.gamestate["board"][POS]
    pending = (tile["currentSpeed"], tile["currentRoller"])
    interaction.channel.sent.clear()
    run(Combat.rollDice(game, f"rollDice_{POS}_{pending[1]}_{pending[0]}_deleteMsg", interaction))

    assert any("missiles" in content for content, _kwargs in interaction.channel.sent if content)
    assert [pending[0], pending[1]] in tile.get("rolledSteps", [])


@pytest.mark.parametrize("resume", [False, True])
def test_new_matchup_pings_the_first_roller_after_refresh(make_game, run, resume):
    game = make_game({"player_count": 3, "players": {
        "1": player_stats("hyd", color="purple", player_name="<@1>", base_cruiser_speed=4),
        "2": player_stats("hyd", color="blue", base_cruiser_speed=1),
        "3": player_stats("hyd", color="yellow"),
    }, "board": board_tile(["purple-cru", "blue-cru", "yellow-cru"], "purple")})
    game.setAttackerAndDefender(["yellow"], ["blue"], POS)
    tile = game.gamestate["board"][POS]
    tile.update(currentSpeed=1, currentRoller="blue", rolledSteps=[[2, "blue"]])
    game.remove_units(["yellow-cru"], POS)
    game.add_damage("blue-cru", POS, 1)
    interaction = FakeInteraction(FakeChannel(f"{game.game_id}-Combat"))

    run(Combat.refreshImage(game, f"refreshImage_{POS}", interaction))
    assert tile["attacker"] == ["yellow"]

    if resume:
        run(TileCommands.resume_combat.callback(TileCommands(None), interaction, POS))
    else:
        run(Combat.checkCombatEnd(game, interaction, POS, 3))

    game = reload(game)
    tile = game.gamestate["board"][POS]
    assert tile["defender"] == ["purple"]
    assert (tile["currentSpeed"], tile["currentRoller"]) == (5, "purple")
    assert not tile.get("rolledSteps")
    assert game.add_damage("blue-cru", POS, 0) == 1
    assert f"FCIDpurple_rollDice_{POS}_purple_5_deleteMsg" in offered_ids(interaction)
    assert any("<@1>, it is your turn" in content for content, _ in interaction.channel.sent if content)


def test_explicit_restart_keeps_damage_and_refuses_pending_hits(make_game, run):
    game = missile_battle(make_game)
    game.setAttackerAndDefender(["blue"], ["red"], POS)
    ship_step = next(pair for pair in speeds(game) if pair[0] < 90)
    tile = game.gamestate["board"][POS]
    tile.update(currentSpeed=ship_step[0], currentRoller=ship_step[1], rolledSteps=[list(ship_step)])
    game.add_damage("blue-cru", POS, 1)
    game.setUnresolvedHits(1, POS)
    interaction = FakeInteraction(FakeChannel(f"{game.game_id}-Combat"))
    command = TileCommands.resume_combat.callback

    run(command(TileCommands(None), interaction, POS, restart=True))
    assert reload(game).gamestate["board"][POS]["rolledSteps"] == [list(ship_step)]
    assert "Resolve the pending hits" in interaction.channel.sent[-1][0]

    game.setUnresolvedHits(0, POS)
    run(command(TileCommands(None), interaction, POS, restart=True))
    game = reload(game)
    tile = game.gamestate["board"][POS]
    assert tile["currentSpeed"] > 99
    assert not tile.get("rolledSteps")
    assert game.add_damage("blue-cru", POS, 0) == 1
