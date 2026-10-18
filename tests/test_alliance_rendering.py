import json

import pytest

from helpers.DrawHelper import DrawHelper


@pytest.mark.parametrize("faction", ["hyd", "ter3"])
def test_alliance_tiles_leave_full_reputation_tracks_visible(faction):
    with open("data/factions.json") as faction_file:
        player = json.load(faction_file)[faction]
    player["color"] = "red"
    player["reputation_track"] = ["amb-hydran-pink"] + [4] * (len(player["reputation_track"]) - 1)
    drawing = DrawHelper({"board": {}})
    without_alliances = drawing.player_area(player)
    player["alliances"] = {"nova": False, "flare": True, "vortex": True}

    rendered = drawing.player_area(player)

    reputation_bounds = (3850, 600, 4570, 720)
    assert rendered.crop(reputation_bounds).tobytes() == without_alliances.crop(reputation_bounds).tobytes()
    for index, (tile, betrayed) in enumerate(player["alliances"].items()):
        x = 4600 + index * 130
        side = "betrayed" if betrayed else "ally"
        image = drawing.use_resized_image(
            f"images/resources/components/alliances/alliances_{tile}_{side}.png", (120, 120))
        expected = without_alliances.crop((x, 600, x + 120, 720))
        expected.paste(image, (0, 0), mask=image)
        assert x + 120 <= rendered.width
        assert rendered.crop((x, 600, x + 120, 720)).tobytes() == expected.tobytes()
