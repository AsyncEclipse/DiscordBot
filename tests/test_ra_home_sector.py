import json
from pathlib import Path

from PIL import Image

from helpers.DrawHelper import DrawHelper


def ra_home_sector():
    with open("data/sectors.json", "r") as f:
        return json.load(f)["255"]


def test_ra_home_sector_data():
    sector = ra_home_sector()
    assert sector["name"] == "Osiris Seth"
    assert sector["type"] == "home"
    assert sector["vp"] == 3
    assert sector["artifact"] == 1
    assert sector["wormholes"] == [0, 1, 3, 4]
    assert sector["money_pop"] == [1]
    assert sector["materialadv_pop"] == [0]
    assert sector["scienceadv_pop"] == [0]
    for key, coords in sector.items():
        if key.endswith("_snap") and coords:
            assert len(coords) == 2, f"{key} {coords} is not a point"
            assert 0 <= coords[0] <= 1024 and 0 <= coords[1] <= 890, f"{key} {coords} is off the tile"


def test_ra_home_sector_tile_art():
    path = "images/resources/hexes/255.png"
    assert Path(path).is_file(), path
    with Image.open(path) as tile:
        assert tile.size == (1024, 890)
        tile.load()


def test_ra_home_sector_renders(make_game, monkeypatch):
    # Stub the art like the round-1 tests do: this covers the tile's data going through the
    # drawing code, and keeps the suite off the one-time image cache load real art costs.
    monkeypatch.setattr(DrawHelper, "use_image", lambda self, filename: Image.new("RGBA", (1024, 890)))
    monkeypatch.setattr(DrawHelper, "use_resized_image",
                        lambda self, filename, size: self.use_image(filename).resize(size))
    tile = dict(ra_home_sector())
    tile.update({"sector": "255", "orientation": 0, "owner": "blue"})
    tile["player_ships"] = ["blue-int", "blue-cru"]
    game = make_game({
        "board": {"201": tile},
        "players": {"1": {"color": "blue", "name": "Remnants of Ra", "owned_tiles": ["201"]}},
        "player_count": 2,
    })
    image = DrawHelper(game.gamestate).board_tile_image("201")
    assert image.width >= 300
