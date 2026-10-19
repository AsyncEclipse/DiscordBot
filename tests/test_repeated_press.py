"""Repeated presses: the same button within the debounce window, or any button on a used-up message."""
from types import SimpleNamespace

import pytest

from tests.fakes import buttons, reload

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


def used_up(inter):
    return any("already used" in content for content, _kwargs in inter.followup.sent)


@pytest.fixture
def moving_interceptor(start_game, press, monkeypatch):
    """Blue's interceptor at home 201 with destinations 301 and 302 offered.

    Moving deletes the destination message, so any later press on it is stale.
    """
    monkeypatch.setattr("Buttons.Move.DrawHelper", lambda *_a, **_k: SimpleNamespace(
        mergeLocationsFile=lambda _t: None, board_tile_image_file=lambda _t: None))
    game, channel = start_game()
    for tile, orientation in (("301", 0), ("302", 60)):
        game.add_tile(tile, orientation, "202")
        game.gamestate["board"][tile]["player_ships"] = ["blue-cru"]
    game.update()
    press(channel, P1, "FCIDblue_startMove")
    press(channel, P1, next(k for k in buttons(channel) if k.startswith("FCIDblue_moveFrom_201_")))
    press(channel, P1, next(k for k in buttons(channel) if "moveThisShip" in k and "interceptor" in k))
    destinations = [k for k in buttons(channel) if k.startswith("FCIDblue_moveTo")]
    to = {t: next(k for k in destinations if f"_{t}_" in k) for t in ("301", "302")}
    press(channel, P1, to["301"])
    return game, channel, to


def test_a_used_up_button_is_refused_after_the_window(press, moving_interceptor):
    game, channel, to = moving_interceptor
    game = reload(game)
    game.gamestate["lastButtonTime"] -= 10
    game.update()

    assert used_up(press(channel, P1, to["301"]))
    assert reload(game).gamestate["board"]["301"]["player_ships"].count("blue-int") == 1


def test_another_button_on_a_used_up_message_is_refused(press, moving_interceptor):
    game, channel, to = moving_interceptor

    assert used_up(press(channel, P1, to["302"]))
    assert reload(game).gamestate["board"]["302"]["player_ships"].count("blue-int") == 0
