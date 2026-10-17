"""A move button pressed a second time must not re-run the move.

The double-press guard (listeners/ButtonListener.py) only refuses the identical
custom id within 3 seconds, so it cannot catch a stale destination button —
a different one, or the same one after the window. The listener therefore
refuses any press on a message an earlier press already used up (deleted):
re-running moveTo would no-op remove_units and still append the ship again.
"""
import pytest

from tests.fakes import buttons, reload

P1 = 1


@pytest.fixture
def no_move_drawing(monkeypatch):
    """The bug is in gamestate, not in the rendered board images."""
    class _NoDraw:
        def mergeLocationsFile(self, _tiles):
            return None

        def board_tile_image_file(self, _tile):
            return None

    monkeypatch.setattr("Buttons.Move.DrawHelper", lambda *_args, **_kwargs: _NoDraw())


def game_ready_for_the_reported_presses(start_game):
    """A lone interceptor at home, blue cruisers parked on both destinations.

    301 and 302 adjoin home 201 across matching wormhole edges, so the
    interceptor can reach both. Destinations are only offered for tiles that
    hold an unpinned ship of the moving player, and with the interceptor being
    the only blue-int on the board a re-executed move cannot be mistaken for
    moving another ship.
    """
    game, channel = start_game()
    game.add_tile("301", 0, "202")
    game.add_tile("302", 60, "202")
    game.gamestate["board"]["301"]["player_ships"] = ["blue-cru"]
    game.gamestate["board"]["302"]["player_ships"] = ["blue-cru"]
    game.update()
    return game, channel


def move_the_interceptor(press, channel):
    """Walk the flow: move button, origin tile, ship; return the offered destination ids."""
    press(channel, P1, "FCIDblue_startMove")
    origin = [k for k in buttons(channel) if k.startswith("FCIDblue_moveFrom_201_")][0]
    press(channel, P1, origin)
    ship = [k for k in buttons(channel) if "moveThisShip" in k and "interceptor" in k][0]
    press(channel, P1, ship)
    return [k for k in buttons(channel) if k.startswith("FCIDblue_moveTo")]


def refused_for_moving(inter):
    return any("already used" in content for content, _kwargs in inter.followup.sent)


def test_double_pressing_a_move_button_after_the_guard_window_is_refused(
        start_game, press, no_move_drawing):
    game, channel = game_ready_for_the_reported_presses(start_game)
    destination = [k for k in move_the_interceptor(press, channel) if "_301_" in k][0]
    press(channel, P1, destination)  # the interceptor moves from 201 to 301
    stock = reload(game).gamestate["players"]["1"]["ship_stock"][0]

    # The bot felt slow and the message is still up, so the player presses the
    # same move button again once the 3 second guard window has expired.
    game = reload(game)
    game.gamestate["lastButtonTime"] -= 10
    game.update()
    inter = press(channel, P1, destination)

    assert refused_for_moving(inter)
    state = reload(game).gamestate
    assert state["board"]["301"]["player_ships"].count("blue-int") == 1
    assert state["board"]["201"]["player_ships"].count("blue-int") == 0
    assert state["players"]["1"]["ship_stock"][0] == stock


def test_pressing_a_different_destination_button_after_the_move_is_refused(
        start_game, press, no_move_drawing):
    game, channel = game_ready_for_the_reported_presses(start_game)
    destinations = move_the_interceptor(press, channel)
    press(channel, P1, [k for k in destinations if "_301_" in k][0])  # the interceptor moves to 301

    inter = press(channel, P1, [k for k in destinations if "_302_" in k][0])

    assert refused_for_moving(inter)
    assert reload(game).gamestate["board"]["302"]["player_ships"].count("blue-int") == 0


def test_a_rapid_double_press_of_the_same_move_button_is_refused(start_game, press, no_move_drawing):
    game, channel = game_ready_for_the_reported_presses(start_game)
    destination = [k for k in move_the_interceptor(press, channel) if "_301_" in k][0]
    press(channel, P1, destination)

    inter = press(channel, P1, destination)  # second click within the 3 second window

    assert any("most recently" in content for content, _kwargs in inter.followup.sent)
    assert reload(game).gamestate["board"]["301"]["player_ships"].count("blue-int") == 1
