from pathlib import Path

import pytest
from PIL import Image

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
