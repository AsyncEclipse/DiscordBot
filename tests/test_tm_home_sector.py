import json

from PIL import Image


def tm_home_sector():
    with open("data/sectors.json", "r") as f:
        return json.load(f)["244"]


def test_tm_home_sector_data():
    sector = tm_home_sector()
    assert sector["name"] == "Artemis VII"
    assert sector["type"] == "home"
    assert sector["vp"] == 3
    assert sector["artifact"] == 1
    assert sector["wormholes"] == [0, 1, 3, 4]
    # The tile prints two science squares; both start populated.
    assert sector["science_pop"] == [1, 1]
    assert sector["money_pop"] == [] and sector["material_pop"] == []
    assert sector["scienceadv_pop"] == [] and sector["materialadv_pop"] == []
    for key, coords in sector.items():
        if key.endswith("_snap") and coords:
            assert len(coords) == 2, f"{key} {coords} is not a point"
            assert 0 <= coords[0] <= 1024 and 0 <= coords[1] <= 890, f"{key} {coords} is off the tile"


def test_tm_home_sector_tile_art():
    path = "images/resources/hexes/244.png"
    with Image.open(path) as tile:
        assert tile.size == (1024, 890)
        # Corners cut like every other sector tile, or the tile paints its background
        # over the sectors around it wherever the two are composited.
        assert tile.convert("RGBA").getpixel((0, 0))[3] == 0
        tile.load()
