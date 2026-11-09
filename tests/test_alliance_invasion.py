import pytest

from Buttons.BlackHole import BlackHoleButtons
from Buttons.Move import MoveButtons
from tests.fakes import FakeInteraction, board_tile, player_helper, players


@pytest.mark.parametrize("arrival", ["move", "black_hole", "neutral_airspace"])
@pytest.mark.parametrize("relationship", ["allied", "enemy", "betrayed"])
def test_arrival_only_alerts_and_unpasses_opponents(make_game, run, arrival, relationship):
    board = board_tile(["blue-int"], owner="blue")
    board.update(board_tile(["red-int"], owner=0 if arrival == "neutral_airspace" else "red", sector=102))
    game = make_game({"player_count": 4, "players": players("blue", "red"), "board": board})
    if relationship != "enemy":
        game.formAlliance("nova", ["blue", "red"])
    if relationship == "betrayed":
        game.betrayAlliance("nova", "blue")
    red = game.getPlayerObjectFromColor("red")
    red["perma_passed"] = True
    game.update()
    blue = game.getPlayerObjectFromColor("blue")
    interaction = FakeInteraction()

    if arrival == "black_hole":
        run(BlackHoleButtons.blackHoleFinish(game, blue, "blackHoleFinish_blue-int_102_noDamage",
                                             player_helper(game, "blue"), interaction))
    else:
        run(MoveButtons.moveTo(game, blue, interaction, "moveTo_101_interceptor_102_1",
                               player_helper(game, "blue")))

    warning = ("another player has entered an airspace you occupy" if arrival == "neutral_airspace"
               else "your system has been invaded")
    has_warning = any(warning in (content or "") for content, kwargs in interaction.channel.sent)
    assert has_warning is (relationship != "allied")
    assert red["perma_passed"] is (relationship == "allied")
    assert "blue-int" in game.gamestate["board"]["102"]["player_ships"]
