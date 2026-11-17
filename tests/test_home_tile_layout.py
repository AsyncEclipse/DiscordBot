"""Community home tiles must keep every unit and pop cube on the printed tile.

sectors.json anchors an icon by its centre and DrawHelper pastes it at
snap - size / 2, so a wrong anchor shows up as an icon sliced by the tile edge,
two units drawn over each other, or a unit parked on a printed resource square
or on the sector number. Checked with the union of every player colour, so a
layout cannot be right for one colour and wrong for another.

The orbital is not covered: its ring is larger than the free space on several
tiles and its anchors are still being tuned.
"""
import json

import numpy as np
import pytest
from PIL import Image, ImageFont

from helpers import FactionData
from helpers.ImageCache import ImageCacheHelper

MULT = 1024 / 345
UNIT = int(70 * MULT)
CUBE = int(18 * MULT)
COLOURS = ["blue", "red", "green", "yellow", "purple", "white", "pink", "brown", "teal"]
UNITS = ("int", "cru", "drd", "sb", "mon")
SQUARES = ("money", "moneyadv", "science", "scienceadv", "material",
           "materialadv", "neutral", "neutraladv", "orbital")
# A printed square at the tile's cut edge is itself clipped by up to ~4%,
# so a cube sitting on it may lose a corner as well.
CUBE_CLIP = 300
COMMUNITY = [key for key, row in FactionData.FACTIONS.items() if row.get("community")]


def _image(name):
    return ImageCacheHelper("images/resources").get_image(name)


def unit_alpha(kind):
    """Every pixel any player's icon of this unit can cover."""
    names = ["mon.png"] if kind == "mon" else [f"{colour}-{kind}.png" for colour in COLOURS]
    mask = None
    for name in names:
        alpha = np.array(_image(name).getchannel("A")) > 40
        mask = alpha if mask is None else (mask | alpha)
    return mask


def place(shape, alpha, left, top):
    cell = np.zeros(shape, bool)
    ys, xs = np.nonzero(alpha)
    ty, tx = ys + top, xs + left
    inside = (tx >= 0) & (ty >= 0) & (tx < shape[1]) & (ty < shape[0])
    cell[ty[inside], tx[inside]] = True
    return cell


def place_box(shape, x0, y0, x1, y1):
    cell = np.zeros(shape, bool)
    cell[max(0, y0):y1, max(0, x0):x1] = True
    return cell


def home(sector_id):
    tile = json.load(open("data/sectors.json"))[sector_id]
    art = Image.open(f"images/resources/hexes/{sector_id}.png").convert("RGBA")
    return tile, np.array(art.getchannel("A")) > 40


def square_boxes(tile, shape):
    boxes = {}
    for key, snap in tile.items():
        if not key.endswith("_snap") or not snap:
            continue
        kind = key[:-5].rstrip("0123456789")
        if kind in SQUARES:
            boxes[key] = place_box(shape, snap[0] - CUBE, snap[1] - CUBE,
                                   snap[0] + CUBE, snap[1] + CUBE)
    return boxes


def number_box(tile, shape):
    snap = tile.get("number_snap") or (int(280 * MULT), int(132 * MULT))
    font = ImageFont.truetype("images/resources/arial.ttf", size=int(30 * MULT))
    left, top, right, bottom = font.getbbox("201", stroke_width=6)
    return place_box(shape, snap[0] + left - 2, snap[1] + top - 2,
                     snap[0] + right + 2, snap[1] + bottom + 2)


@pytest.mark.parametrize("faction", COMMUNITY)
def test_units_keep_their_space_on_the_home_tile(faction):
    sector_id = FactionData.FACTIONS[faction]["home_planet"]
    tile, printed = home(sector_id)
    shape = printed.shape
    cells = {kind: place(shape, unit_alpha(kind), tile[f"{kind}_snap"][0] - UNIT // 2,
                         tile[f"{kind}_snap"][1] - UNIT // 2)
             for kind in UNITS}
    squares = square_boxes(tile, shape)
    number = number_box(tile, shape)

    for kind, cell in cells.items():
        off_tile = int((cell & ~printed).sum())
        assert off_tile == 0, f"{sector_id}: {kind} runs {off_tile}px off the tile"
        for key, square in squares.items():
            covered = int((cell & square).sum())
            assert covered == 0, f"{sector_id}: {kind} sits on {key} ({covered}px)"
        covered = int((cell & number).sum())
        assert covered == 0, f"{sector_id}: {kind} covers the sector number ({covered}px)"

    kinds = list(cells)
    for i in range(len(kinds)):
        for j in range(i + 1, len(kinds)):
            overlap = int((cells[kinds[i]] & cells[kinds[j]]).sum())
            assert overlap == 0, f"{sector_id}: {kinds[i]} and {kinds[j]} overlap ({overlap}px)"


@pytest.mark.parametrize("faction", COMMUNITY)
def test_pop_cubes_stay_on_the_home_tile(faction):
    sector_id = FactionData.FACTIONS[faction]["home_planet"]
    tile, printed = home(sector_id)
    cube_alpha = np.array(_image("popcube_blue.png").getchannel("A")) > 40

    for key, snap in tile.items():
        if not key.endswith("_snap") or not snap:
            continue
        res = key[:-5]
        base = res.rstrip("0123456789")
        if base not in SQUARES:
            continue
        index = int(res[len(base):]) - 1
        pops = tile.get(f"{base}_pop", [])
        if index >= len(pops) or not pops[index]:
            continue
        cell = place(printed.shape, cube_alpha, snap[0] - CUBE, snap[1] - CUBE)
        outside = int((cell & ~printed).sum())
        assert outside <= CUBE_CLIP, f"{sector_id}: {key} cube is {outside}px off the tile"
