"""Exploring a position with no legal rotation must be refused, not crash."""
from discord.ui import View

from Buttons.Explore import ExploreButtons
from helpers.DrawHelper import DrawHelper


def test_a_position_with_no_legal_orientation_still_draws():
    # No player tiles, so no rotation ever connects and count stays 1.
    view = View()

    _view, file = DrawHelper({"board": {}}).draw_possible_oritentations(
        "104", "303", [], view, {"color": "blue"})

    assert view.children == []
    assert file.filename == "tile_image.webp"



def test_exploring_a_position_you_are_not_connected_to_is_refused(start_game, press):
    game, channel = start_game()
    blue = game.getPlayerObjectFromColor("blue")
    reachable = ExploreButtons.getTilesToExplore(game, blue)
    position = next(p for p in ("318", "317", "316", "315", "101", "102", "103", "104", "106")
                    if p not in reachable)

    press(channel, 1, f"FCIDblue_exploreTile_{position}")

    sent = [content or "" for content, _kwargs in channel.sent]
    assert any("cannot explore" in content for content in sent)
    assert not any("Tile explored" in content for content in sent)
