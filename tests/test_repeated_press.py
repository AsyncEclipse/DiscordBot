"""A repeated press of the same button is refused (needs the test framework fixtures)."""
from tests.fakes import reload

P1 = 1


def test_a_repeated_press_of_the_same_button_is_refused(start_game, press):
    game, channel = start_game()
    press(channel, P1, "FCIDblue_passForRound")
    # Remember the raw id, FCID prefix included, or the guard never matches.
    assert reload(game).gamestate["lastButton"] == "FCIDblue_passForRound"

    inter = press(channel, P1, "FCIDblue_passForRound")

    assert any("most recently" in content for content, _kwargs in inter.followup.sent)
