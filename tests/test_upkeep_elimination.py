from Buttons.Influence import InfluenceButtons
from Buttons.Turn import TurnButtons
from helpers.PlayerHelper import PlayerHelper
from tests.fakes import FakeInteraction, reload


def test_upkeep_ignores_eliminated_players_but_still_rejects_repeat_presses(start_game, press, run):
    game, channel = start_game()
    game.gamestate["peopleToCheckWith"] = ["blue", "red"]
    player = game.get_player(2)
    run(InfluenceButtons.eliminatePlayer(
        game, player, FakeInteraction(channel), PlayerHelper("2", player), False))
    assert reload(game).gamestate["peopleToCheckWith"] == ["blue"]

    assert not reload(game).is_everyone_passed()
    press(channel, 1, "runUpkeep")
    assert reload(game).gamestate["roundNum"] == 1

    press(channel, 1, "FCIDblue_passForRound")
    press(channel, 1, "readyForUpkeep")
    assert reload(game).is_everyone_passed()
    assert not reload(game).get_player(2).get("passed", False)

    press(channel, 1, "runUpkeep")
    assert reload(game).gamestate["roundNum"] == 2

    run(TurnButtons.runUpkeep(reload(game), FakeInteraction(channel)))
    assert reload(game).gamestate["roundNum"] == 2
    assert "Not everyone has passed" in channel.sent[-1][0]
