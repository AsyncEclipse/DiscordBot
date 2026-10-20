from pathlib import Path

import pytest
from PIL import Image

from helpers.DrawHelper import DrawHelper
from helpers.GamestateHelper import GamestateHelper

TM_ARTWORK = {
    "images/resources/components/factions/tm_board.png": (4400, 2475),
    "images/resources/components/factions/tm_info.png": (1855, 957),
    "images/resources/components/factions/tm_ambassador.png": (512, 512),
    "images/resources/components/layouts/factionImages/tm_image.png": (512, 512),
    "images/resources/components/layouts/faction_titles/name_trade_tm.png": (1186, 177),
    "images/resources/components/layouts/blueprints/classes/tm_interceptor_class.png": (300, 115),
    "images/resources/components/layouts/blueprints/classes/tm_cruiser_class.png": (300, 115),
    "images/resources/components/layouts/blueprints/classes/tm_dreadnought_class.png": (315, 148),
    "images/resources/components/layouts/blueprints/classes/tm_starbase_class.png": (300, 115),
}


@pytest.mark.parametrize("path,size", TM_ARTWORK.items())
def test_tm_artwork_exists_and_loads(path, size):
    assert Path(path).is_file(), path
    with Image.open(path) as image:
        assert image.size == size, path
        image.load()


def test_tm_artwork_key_matches_the_name_lookups():
    # DrawHelper asks for <key>_image.png, name_trade_<key>.png and the class images; the key
    # those lookups produce is what the files above are named after.
    assert DrawHelper.get_short_faction_name(None, "Techno-Mages") == "tm"
    assert GamestateHelper.getShortFactionNameFromFull(None, "Techno-Mages") == "tm"
    assert GamestateHelper.get_short_faction_name(None, "Techno-Mages") == "tm"


def test_tm_ambassador_has_transparent_token_corners():
    with Image.open("images/resources/components/factions/tm_ambassador.png") as image:
        alpha = image.getchannel("A")
        for corner in [(0, 0), (511, 0), (0, 511), (511, 511)]:
            assert alpha.getpixel(corner) == 0
        assert alpha.getpixel((256, 256)) >= 250
