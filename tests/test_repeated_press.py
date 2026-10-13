"""A repeated press of the same button within the debounce window is refused."""
from tests.fakes import reload

P1 = 1


def refused(inter):
    return any("most recently" in content for content, _kwargs in inter.followup.sent)


def test_a_quick_repeat_of_the_same_button_is_refused(start_game, press):
    game, channel = start_game()
    press(channel, P1, "FCIDblue_passForRound")
    # Remember the raw id, FCID prefix included, or the guard never matches.
    assert reload(game).gamestate["lastButton"] == "FCIDblue_passForRound"

    assert refused(press(channel, P1, "FCIDblue_passForRound"))


def test_the_same_button_is_allowed_again_after_the_window(start_game, press):
    game, channel = start_game()
    press(channel, P1, "FCIDblue_passForRound")
    game = reload(game)
    game.gamestate["lastButtonTime"] -= 10
    game.update()

    assert not refused(press(channel, P1, "FCIDblue_passForRound"))
