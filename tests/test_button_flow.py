"""Integration tests: press real buttons through ButtonListener.resolveButton."""
from tests.fakes import buttons, reload

P1, P2 = 1, 2


def test_press_through_listener(start_game, press):
    _game, channel = start_game()
    inter = press(channel, P1, "FCIDblue_showReputation")
    assert "reputation tiles" in inter.followup.sent[0][0]


def test_pass_then_next_player_gets_turn(start_game, press):
    game, channel = start_game()
    press(channel, P1, "FCIDblue_passForRound")
    state = reload(game).gamestate
    assert state["players"][str(P1)]["passed"]
    assert state["activePlayerColor"] == ["red"]
    assert any(l and "Build" in l for l in buttons(channel).values())
    # a second press in the same process must not be blocked by the first one's lock
    press(channel, P2, "FCIDred_passForRound")
    assert reload(game).gamestate["players"][str(P2)]["passed"]


def test_a_repeated_press_of_the_same_button_is_refused(start_game, press):
    game, channel = start_game()
    press(channel, P1, "FCIDblue_passForRound")
    # Remember the raw id, FCID prefix included, or the guard never matches.
    assert reload(game).gamestate["lastButton"] == "FCIDblue_passForRound"

    inter = press(channel, P1, "FCIDblue_passForRound")

    assert any("most recently" in content for content, _kwargs in inter.followup.sent)

