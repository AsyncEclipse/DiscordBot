"""The combat message lists every initiative step. Pressing one out of order must not
skip the step the battle is actually waiting for (a pending missile salvo).
"""
from helpers.CombatHelper import Combat
from tests.fakes import FakeInteraction, POS, board_tile, players


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
    Combat.getCombatButtons(game, POS)
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
    Combat.getCombatButtons(game, POS)
    run(Combat.promptNextSpeed(game, POS, interaction.channel, False))

    tile = game.gamestate["board"][POS]
    pending = (tile["currentSpeed"], tile["currentRoller"])
    interaction.channel.sent.clear()
    run(Combat.rollDice(game, f"rollDice_{POS}_{pending[1]}_{pending[0]}_deleteMsg", interaction))

    assert any("missiles" in content for content, _kwargs in interaction.channel.sent if content)
    assert [pending[0], pending[1]] in tile.get("rolledSteps", [])
