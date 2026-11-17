"""Every community home tile draws the whole monolith.

The home tiles crop the hex at the bottom, so a monolith anchored too low is
drawn past the artwork and only a sliver shows. Render the tile with and without
the unit and require almost all of the icon's pixels to reach the image.
"""
import pytest
from PIL import Image, ImageChops
from helpers import FactionData
from helpers.DrawHelper import DrawHelper
from helpers.ImageCache import ImageCacheHelper

COMMUNITY = [key for key, row in FactionData.FACTIONS.items() if row.get("community")]


@pytest.mark.render
@pytest.mark.parametrize("faction", COMMUNITY)
def test_monolith_is_drawn_whole_on_home_tile(start_game, faction):
    game, channel = start_game(factions=[faction, "eri"])
    player = game.get_player(1)
    tile = game.gamestate["board"]["201"]
    drawing = DrawHelper(game.gamestate)

    without = drawing.board_tile_image("201").convert("RGBA")
    tile["player_ships"].append(f"{player['color']}-mon")
    with_mon = drawing.board_tile_image("201").convert("RGBA")

    changed = ImageChops.difference(with_mon, without).convert("RGB").convert("L")
    drawn = sum(1 for value in changed.getdata() if value > 8)
    icon = ImageCacheHelper("images/resources").get_image("mon.png")
    whole = sum(1 for alpha in icon.getchannel("A").getdata() if alpha > 40)

    assert drawn >= 0.9 * whole, f"{faction} monolith is cut off by the tile edge"
