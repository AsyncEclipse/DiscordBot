"""One real-art rendering case per faction; rule tests run without drawing."""
from PIL import Image, ImageChops, ImageDraw
import pytest

from helpers import FactionData
from helpers.DrawHelper import DrawHelper


def assert_alliance_layout(drawing, player, without_alliances):
    player["alliances"] = {"nova": False, "flare": True, "vortex": True}
    rendered = drawing.player_area(player)
    bounds = (3850, 600, 4570, 720)
    assert rendered.crop(bounds).tobytes() == without_alliances.crop(bounds).tobytes()
    for index, (tile, betrayed) in enumerate(player["alliances"].items()):
        x = 4600 + index * 130
        side = "betrayed" if betrayed else "ally"
        image = drawing.use_resized_image(
            f"images/resources/components/alliances/alliances_{tile}_{side}.png", (120, 120))
        expected = without_alliances.crop((x, 600, x + 120, 720))
        expected.paste(image, (0, 0), mask=image)
        assert x + 120 <= rendered.width
        assert rendered.crop((x, 600, x + 120, 720)).tobytes() == expected.tobytes()


def assert_muon_layout(drawing, player, without_muons):
    player["dread_parts"].extend(["mus", "mus"])
    rendered = drawing.player_area(player)
    source = drawing.use_resized_image(
        "images/resources/components/upgrades/muon_source.png", (137, 145)).resize((64, 64))
    for y in (180, 248):
        bounds = (4760, y, 4824, y + 64)
        expected = without_muons.crop(bounds)
        expected.paste(source, (0, 0), mask=source)
        assert rendered.crop(bounds).tobytes() == expected.tobytes()


def assert_map_layout(drawing):
    image = Image.open(drawing.show_game().fp).convert("L")
    pixels = image.load()
    width, height = image.size

    def has_content(row, x_from, x_to):
        return any(pixels[x, row] > 40 for x in range(x_from, x_to, 10))

    strip_top = next(row for row in range(height) if has_content(row, 0, 900))
    map_bottom = max(row for row in range(strip_top) if has_content(row, 900, width))
    assert strip_top - map_bottom >= 30
    assert drawing.display_remaining_tiles().height >= 250 + drawing.display_turn_order().height


def assert_nebula_rotation(game, drawing, monkeypatch):
    labels = []
    with monkeypatch.context() as patch:
        patch.setattr(DrawHelper, "label_nebula_subsectors",
                      staticmethod(lambda image, position, rotation: labels.append((position, rotation))))
        game.add_tile("207", 0, "295")
        baseline = drawing.board_tile_image("207")
        for rotation in range(60, 360, 60):
            game.add_tile("207", rotation, "295")
            rendered = drawing.board_tile_image("207b")
            difference = ImageChops.difference(rendered, baseline.rotate(rotation)).convert("RGB")
            assert difference.getbbox() is None
            assert labels[-1] == ("207", rotation)


def assert_turtugan_layout(game, drawing, player, labels):
    reserve_text = f"S3 reserve: {len(player['deep_space_sectors'])}"
    bounds = next(bounds for text, bounds in labels if text == reserve_text)
    left, top, right, bottom = bounds
    assert 450 < top < bottom < 470
    assert right < 280
    assert {"TRAITOR", "Passed"} <= {text for text, bounds in labels}
    for text, other in labels:
        if text != reserve_text:
            assert right <= other[0] or other[2] <= left or bottom <= other[1] or other[3] <= top

    player["harvester_placements"] = [
        {"position": "201", "square": "science", "index": 0, "resource": "science"}]
    game.gamestate["board"]["201"].update(science_pop=[0], science1_snap=[700, 700])
    pixels = drawing.board_tile_image("201").convert("RGB").load()
    row = [pixels[x, 700] for x in range(600, 800)]
    blue = [index for index, colour in enumerate(row) if colour == (0, 0, 255)]
    assert blue, "the harvester circle is not drawn"
    assert row[blue[0] - 1] == (0, 0, 0)
    assert row[blue[-1] + 1] == (0, 0, 0)


@pytest.mark.render
@pytest.mark.parametrize("faction", FactionData.FACTIONS)
def test_faction_rendering(start_game, monkeypatch, faction):
    loaded = []
    resized = []
    labels = []
    tile_labels = []
    use_image = DrawHelper.use_image
    use_resized_image = DrawHelper.use_resized_image
    draw_text = ImageDraw.ImageDraw.text

    def record_image(drawing, filename):
        loaded.append(filename)
        return use_image(drawing, filename)

    def record_resized_image(drawing, filename, size):
        resized.append(filename)
        return use_resized_image(drawing, filename, size)

    def record_text(draw, xy, text, *args, **kwargs):
        if draw._image.size == (1024, 890):
            tile_labels.append(text)
        if draw._image.size == (5000, 800):
            bounds = draw.textbbox(xy, text, font=kwargs.get("font"), anchor=kwargs.get("anchor"),
                                   stroke_width=kwargs.get("stroke_width", 0))
            labels.append((text, bounds))
        return draw_text(draw, xy, text, *args, **kwargs)

    monkeypatch.setattr(DrawHelper, "use_image", record_image)
    monkeypatch.setattr(DrawHelper, "use_resized_image", record_resized_image)
    monkeypatch.setattr(ImageDraw.ImageDraw, "text", record_text)
    game, channel = start_game(factions=[faction, "eri"])
    player = game.get_player(1)
    if faction in ("hyd", "ter3"):
        player["reputation_track"] = ["amb-hydran-pink"] + [4] * (len(player["reputation_track"]) - 1)
    if faction == "tur":
        player.update(username="Turtugan player", traitor=True, disc_tiles_for_points=5, passed=True)
        game.gamestate["activePlayerColor"] = []
    if faction == "wra":
        player["wraithSouls"] = 2
        player["wraithPowerSpent"] = 9

    drawing = DrawHelper(game.gamestate)
    image = drawing.player_area(player)
    assert image.size == (5000, 800)
    player_labels = list(labels)
    home = drawing.board_tile_image("201")
    assert home.size == (1024, 890)
    assert "201" in tile_labels
    assert str(player["home_planet"]) not in tile_labels
    art = FactionData.artwork_name(player["name"])
    assert f"images/resources/components/layouts/factionImages/{art}_image.png" in loaded
    assert f"images/resources/components/layouts/faction_titles/name_trade_{art}.png" in loaded
    ships = ["interceptor", "cruiser", "dreadnought", "starbase"]
    if faction == "wul":
        ships.remove("interceptor")
    if faction == "rho":
        ships.remove("dreadnought")
    if faction == "exl":
        ships[-1] = "orbital"
    class_art = "terran" if faction.startswith("ter") else art
    for ship in ships:
        path = f"images/resources/components/layouts/blueprints/classes/{class_art}_{ship}_class.png"
        assert path in loaded

    if faction in ("hyd", "ter3"):
        assert_alliance_layout(drawing, player, image)
    if faction in ("eri", "wul"):
        assert_muon_layout(drawing, player, image)
    if faction == "hyd":
        game.gamestate["minor_species"] = ["Point Per Ambassador"]
        assert_map_layout(drawing)
        assert_nebula_rotation(game, drawing, monkeypatch)
    if faction == "tur":
        assert_turtugan_layout(game, drawing, player, player_labels)
    if faction in ("kur", "tur"):
        texts = {text for text, _bounds in player_labels}
        assert "+1 CMP" in texts
        assert "+1 HULL" in texts
    if faction == "kur":
        assert "3 PWR" in {text for text, _bounds in player_labels}
    if faction == "wul":
        assert not any(path.endswith("/blueprint_interceptor.png") for path in loaded)
        with monkeypatch.context() as patch:
            def omit_number(draw, xy, text, *args, **kwargs):
                if text != "201":
                    return draw_text(draw, xy, text, *args, **kwargs)
            patch.setattr(ImageDraw.ImageDraw, "text", omit_number)
            without_number = drawing.board_tile_image("201")
        bounds = ImageChops.difference(home.convert("RGB"), without_number.convert("RGB")).getbbox()
        assert bounds is not None
        left, top, right, bottom = bounds
        assert 650 <= left < right <= 850
        assert 310 <= top < bottom <= 430
    if faction == "wra":
        assert "images/resources/hexes/numberless/254.png" in loaded
        assert "images/resources/hexes/254.png" not in loaded
        assert "+2" in {text for text, bounds in player_labels}
        assert "images/resources/components/upgrades/wraith_soul_count.png" in resized
        assert any(text == "2" and 4600 < bounds[0] < bounds[2] < 4660
                   and 660 < bounds[1] < bounds[3] < 720 for text, bounds in player_labels)
        assert sum(path.endswith("/wraith_phase_module.png") for path in resized) == 4
    if faction in ("her", "kur"):
        assert drawing.faction_portrait(art).size == (600, 600)
        assert loaded[-1] == f"images/resources/components/layouts/factionImages/{art}_image.png"
    if FactionData.FACTIONS[faction].get("community"):
        with Image.open(f"images/resources/components/factions/{art}_ambassador.png") as ambassador:
            assert ambassador.size == (512, 512)
            alpha = ambassador.convert("RGBA").getchannel("A")
            assert alpha.getpixel((0, 0)) == 0
            assert alpha.getpixel((256, 256)) >= 250
            if faction in ("atl", "ra", "tm", "her", "kur", "wra"):
                assert all(alpha.getpixel(corner) == 0
                           for corner in ((511, 0), (0, 511), (511, 511)))
    if faction in ("tur", "wra"):
        paths = [f"images/resources/components/layouts/factionImages/{art}_image.png"]
        if faction == "wra":
            paths.append("images/resources/components/layouts/blueprints/classes/wraith_interceptor_class.png")
        for path in paths:
            with Image.open(path) as image:
                assert image.convert("RGBA").getpixel((0, 0))[3] == 0


@pytest.mark.render
@pytest.mark.parametrize("souls", [0, 12])
def test_wraith_soul_counter_draws_the_accumulated_number(start_game, monkeypatch, souls):
    game, channel = start_game(factions=["wra", "eri"])
    player = game.get_player(1)
    player["wraithSouls"] = souls
    labels = []
    draw_text = ImageDraw.ImageDraw.text

    def record_counter(draw, xy, text, *args, **kwargs):
        if xy == (4640, 688):
            labels.append(text)
        return draw_text(draw, xy, text, *args, **kwargs)

    monkeypatch.setattr(ImageDraw.ImageDraw, "text", record_counter)
    DrawHelper(game.gamestate).player_area(player)

    assert labels == [str(souls)]
