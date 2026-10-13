"""Exploring a position with no legal rotation must be refused, not crash."""
from discord.ui import View

from helpers.DrawHelper import DrawHelper


def test_a_position_with_no_legal_orientation_still_draws():
    # No player tiles, so no rotation ever connects and count stays 1.
    view = View()

    _view, file = DrawHelper({"board": {}}).draw_possible_oritentations(
        "104", "303", [], view, {"color": "blue"})

    assert view.children == []
    assert file.filename == "tile_image.webp"

