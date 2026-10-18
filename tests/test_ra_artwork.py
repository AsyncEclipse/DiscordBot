from pathlib import Path

import pytest
from PIL import Image

from helpers.DrawHelper import DrawHelper
from helpers.GamestateHelper import GamestateHelper

RA_ARTWORK = {
    "images/resources/components/factions/ra_board.png": (4547, 2539),
    "images/resources/components/factions/ra_info.png": (1855, 957),
    "images/resources/components/factions/ra_ambassador.png": (512, 512),
    "images/resources/components/layouts/factionImages/ra_image.png": (512, 512),
    "images/resources/components/layouts/faction_titles/name_trade_ra.png": (1186, 177),
    "images/resources/components/layouts/blueprints/classes/ra_interceptor_class.png": (300, 115),
    "images/resources/components/layouts/blueprints/classes/ra_cruiser_class.png": (300, 115),
    "images/resources/components/layouts/blueprints/classes/ra_dreadnought_class.png": (315, 148),
    "images/resources/components/layouts/blueprints/classes/ra_starbase_class.png": (300, 115),
}


@pytest.mark.parametrize("path,size", RA_ARTWORK.items())
def test_ra_artwork_exists_and_loads(path, size):
    assert Path(path).is_file(), path
    with Image.open(path) as image:
        assert image.size == size, path
        image.load()


def test_ra_artwork_key_matches_the_name_lookups():
    # DrawHelper asks for <key>_image.png, name_trade_<key>.png and the class images; the key
    # those lookups produce is what the files above are named after.
    assert DrawHelper.get_short_faction_name(None, "Remnants of Ra") == "ra"
    assert GamestateHelper.getShortFactionNameFromFull(None, "Remnants of Ra") == "ra"
    assert GamestateHelper.get_short_faction_name(None, "Remnants of Ra") == "ra"


def test_ra_ambassador_has_transparent_token_corners():
    with Image.open("images/resources/components/factions/ra_ambassador.png") as image:
        alpha = image.getchannel("A")
        for corner in [(0, 0), (511, 0), (0, 511), (511, 511)]:
            assert alpha.getpixel(corner) == 0
        assert alpha.getpixel((256, 256)) == 255
