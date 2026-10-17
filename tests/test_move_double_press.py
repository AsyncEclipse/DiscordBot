"""Recreates the reported bug: pressing a move button a second time duplicates an interceptor.

The double-press guard (listeners/ButtonListener.py) only refuses the *identical*
custom id within a 3 second window. When the second click lands after that window
(the bot often takes longer than 3s per action), MoveButtons.moveTo runs again:
remove_units silently no-ops because the ship already left the origin, while
add_units appends the ship to the destination a second time and drains a ship
from stock. These tests pin the current buggy behaviour; flip the assertions
once the second press is refused.
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
    """A lone interceptor at home, a blue cruiser already one tile away.

    301 adjoins home 201 across matching wormhole edges, so the interceptor can
    reach it. Destinations are only offered for tiles that hold an unpinned
    ship of the moving player, and with the interceptor being the only blue-int
    on the board a re-executed move cannot be mistaken for moving another
    ship — the duplicate is unambiguous.
    """
    game, channel = start_game()
    game.add_tile("301", 0, "202")
    game.gamestate["board"]["301"]["player_ships"] = ["blue-cru"]
    game.update()
    return game, channel


def move_the_interceptor(press, channel):
    """Walk the flow: move button, origin tile, ship; return the destination button id."""
    press(channel, P1, "FCIDblue_startMove")
    origin = [k for k in buttons(channel) if k.startswith("FCIDblue_moveFrom_201_")][0]
    press(channel, P1, origin)
    ship = [k for k in buttons(channel) if "moveThisShip" in k and "interceptor" in k][0]
    press(channel, P1, ship)
    return [k for k in buttons(channel) if k.startswith("FCIDblue_moveTo") and "_301_" in k][0]


def test_double_pressing_a_move_button_after_the_guard_window_duplicates_the_interceptor(
        start_game, press, no_move_drawing):
    game, channel = game_ready_for_the_reported_presses(start_game)
    destination = move_the_interceptor(press, channel)
    press(channel, P1, destination)  # the interceptor moves from 201 to 301
    stock = reload(game).gamestate["players"]["1"]["ship_stock"][0]

    # The bot felt slow and the message is still up, so the player presses the
    # same move button again once the 3 second guard window has expired.
    game = reload(game)
    game.gamestate["lastButtonTime"] -= 10
    game.update()
    press(channel, P1, destination)

    state = reload(game).gamestate
    assert state["board"]["301"]["player_ships"].count("blue-int") == 2  # BUG: duplicated
    assert state["board"]["201"]["player_ships"].count("blue-int") == 0  # remove_units no-opped
    assert state["players"]["1"]["ship_stock"][0] == stock - 1  # the phantom came out of stock


def test_a_rapid_double_press_of_the_same_move_button_is_refused(start_game, press, no_move_drawing):
    game, channel = game_ready_for_the_reported_presses(start_game)
    destination = move_the_interceptor(press, channel)
    press(channel, P1, destination)

    inter = press(channel, P1, destination)  # second click within the 3 second window

    assert any("most recently" in content for content, _kwargs in inter.followup.sent)
    assert reload(game).gamestate["board"]["301"]["player_ships"].count("blue-int") == 1
