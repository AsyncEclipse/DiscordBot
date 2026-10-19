"""Nebula Sector rules: 295/395 are one hex split into three Subsectors."""
import pytest
from discord.ui import View
from PIL import Image, ImageChops

from Buttons.BlackHole import BlackHoleButtons
from Buttons.DiscoveryTile import DiscoveryTileButtons
from Buttons.Move import MoveButtons
from helpers.DrawHelper import DrawHelper
from helpers.PlayerHelper import PlayerHelper
from tests.fakes import FakeInteraction, player_stats


def _bare_gamestate():
    return {
        "game_id": "t",
        "setup_finished": 1,
        "game_phase": [],
        "game_round": 1,
        "roundNum": 1,
        "advanced_ai": 0,
        "wa_ai": 0,
        "player_count": 2,
        "player_order": [],
        "active_player": [],
        "activePlayerColor": [],
        "lastPingTime": 0,
        "lastButton": "",
        "available_colors": [],
        "used_colors": [],
        "tile_deck_100": [],
        "tile_deck_200": [],
        "tile_deck_300": [],
        "tile_discard": [],
        "tech_deck": [],
        "available_techs": [],
        "reputation_tiles": [],
        "discTiles": [],
        "players": {},
        "board": {},
    }


def test_nebula_placement_expands_into_subsectors(make_game):
    game = make_game(_bare_gamestate())
    game.add_tile("207", 0, "295")
    board = game.gamestate["board"]
    assert sorted(board) == ["207", "207b", "207c"]
    assert board["207"]["player_ships"] == ["ai-anc"]
    assert board["207"]["disctile"] == 0
    assert board["207b"]["disctile"] == 1
    assert board["207c"]["disctile"] == 1
    assert board["207b"]["player_ships"] == []
    assert board["207"]["wormholes"] == [0, 1, 2, 3, 4, 5]
    # ring-2 adjacency of position 207 is [104, 206, 309, 310, 311, 208]:
    # the ancient wedge owns edges 1,2; the discovery wedges 0,5 and 3,4
    assert board["207"]["adjacent"] == ["206", "309", "207b", "207c"]
    assert board["207b"]["adjacent"] == ["104", "208", "207", "207c"]
    assert board["207c"]["adjacent"] == ["310", "311", "207", "207b"]


def test_nebula_internal_move_costs_one_activation(make_game, monkeypatch):
    monkeypatch.setattr(PlayerHelper, "getTechs", lambda self: [])
    game = make_game(_bare_gamestate())
    game.add_tile("207", 0, "295")
    game.add_tile("104", 0, "101")
    game.add_tile("208", 0, "201")
    game.gamestate["players"] = {"1": {"color": "blue", "name": "Blue", "player_name": "Blue"}}
    game.gamestate["board"]["207b"]["player_ships"] = ["blue-int"]
    game.update()
    player = {"color": "blue", "name": "Blue", "player_name": "Blue"}
    tiles = MoveButtons.getTilesInRange(game, player, "207b", 1, 0)
    assert {"207c", "207"} <= tiles
    assert "206" not in tiles  # 206 borders the Ancient Subsector, not 207b


def _neighbour_game(make_game, monkeypatch, rot):
    monkeypatch.setattr(PlayerHelper, "getTechs", lambda self: [])
    game = make_game(_bare_gamestate())
    game.add_tile("207", 0, "295")
    # sector 201 has wormholes [1, 3, 5]: at 0/120/240 its edge facing 207 is a wall
    game.add_tile("208", rot, "201")
    game.gamestate["players"] = {"1": {"color": "blue", "name": "Blue", "player_name": "Blue"}}
    game.update()
    return game, {"color": "blue", "name": "Blue", "player_name": "Blue"}


def test_move_into_nebula_lands_in_edge_owning_subsector(make_game, monkeypatch):
    game, player = _neighbour_game(make_game, monkeypatch, 60)
    game.gamestate["board"]["208"]["player_ships"] = ["blue-int"]
    game.update()
    # 208 is on 207's NW edge, which belongs to Subsector b
    assert MoveButtons.getTilesInRange(game, player, "208", 1, 0) & {"207", "207b", "207c"} == {"207b"}
    game.gamestate["board"]["207b"]["player_ships"] = ["blue-int"]
    game.update()
    assert "208" in MoveButtons.getTilesInRange(game, player, "207b", 1, 0)


def test_nebula_walls_need_jump_drive(make_game, monkeypatch):
    game, player = _neighbour_game(make_game, monkeypatch, 0)
    game.gamestate["board"]["208"]["player_ships"] = ["blue-int"]
    game.gamestate["board"]["207b"]["player_ships"] = ["blue-int"]
    game.update()
    assert "208" not in MoveButtons.getTilesInRange(game, player, "207b", 1, 0)
    assert "208" in MoveButtons.getTilesInRange(game, player, "207b", 1, 1)
    assert "207b" not in MoveButtons.getTilesInRange(game, player, "208", 1, 0)
    assert MoveButtons.getTilesInRange(game, player, "208", 1, 1) & {"207", "207b", "207c"} == {"207b"}


def test_influence_refused_in_nebula(make_game, run):
    from Buttons.Influence import InfluenceButtons
    from tests.fakes import FakeChannel, FakeInteraction
    game = make_game(_bare_gamestate())
    game.add_tile("207", 0, "295")
    game.gamestate["players"] = {"1": {"color": "blue", "name": "Blue", "player_name": "Blue",
                                       "influence_discs": 3}}
    game.update()
    inter = FakeInteraction(FakeChannel("t-actions"), custom_id="addInfluenceFinish_207b", user_id=1)
    run(InfluenceButtons.addInfluenceFinish(game, game.gamestate["players"]["1"], inter,
                                            "addInfluenceFinish_207b"))
    assert game.gamestate["board"]["207b"]["owner"] == 0
    assert any("Nebula Sectors may never contain Influence Discs." in content
               for content, _ in inter.channel.sent)


@pytest.mark.parametrize("sector", ["295", "395"])
@pytest.mark.parametrize("rotation,suffixes", [
    (0, "baaccb"), (60, "aaccbb"), (120, "accbba"),
    (180, "ccbbaa"), (240, "cbbaac"), (300, "bbaacc"),
])
def test_rotated_nebula_edges_and_movement(make_game, monkeypatch, sector, rotation, suffixes):
    monkeypatch.setattr(PlayerHelper, "getTechs", lambda self: [])
    game = make_game(_bare_gamestate())
    game.add_tile("207", rotation, sector)
    player = player_stats("hyd", color="blue")
    game.gamestate["players"] = {"1": player}
    board = game.gamestate["board"]
    neighbors = ["104", "206", "309", "310", "311", "208"]
    board["207"]["player_ships"] = []
    for edge, (neighbor, suffix) in enumerate(zip(neighbors, suffixes)):
        target = "207" + ("" if suffix == "a" else suffix)
        assert game.nebula_subsector_for_edge("207", edge) == target
        assert neighbor in board[target]["adjacent"]
        # A fully open neighbouring sector isolates Nebula edge ownership from other walls.
        board[neighbor] = {"sector": "101", "orientation": 0, "owner": 0,
                           "wormholes": list(range(6)), "player_ships": ["blue-int"]}
        destinations = MoveButtons.getTilesInRange(game, player, neighbor, 1, 0)
        assert destinations & {"207", "207b", "207c"} == {target}
        assert neighbor in MoveButtons.getTilesInRange(game, player, target, 1, 0)
        for other in {"207", "207b", "207c"} - {target}:
            assert neighbor not in board[other]["adjacent"]


@pytest.mark.parametrize("sector,expected", [("295", 6), ("395", 6), ("201", 1)])
def test_nebula_keeps_all_placement_rotations(make_game, run, monkeypatch, sector, expected):
    game = make_game(_bare_gamestate())
    game.add_tile("208", 60, "201")
    drawing = DrawHelper(game.gamestate)
    monkeypatch.setattr(drawing, "base_tile_image_with_rotation_in_context",
                        lambda *args: Image.new("RGBA", (1, 1)))

    async def options():
        view, image = drawing.draw_possible_oritentations(sector, "207", ["208"], View(), {"color": "blue"})
        return [int(button.custom_id.split("_")[-1]) for button in view.children]

    rotations = run(options())
    assert len(rotations) == expected
    if expected == 6:
        assert rotations == [0, 60, 120, 180, 240, 300]


def test_nebula_movement_labels_preserve_saved_button_ids(make_game, run, monkeypatch):
    game = make_game(_bare_gamestate())
    game.add_tile("207", 120, "295")
    player = player_stats("hyd", color="blue")
    game.gamestate["players"] = {"1": player}
    game.gamestate["board"]["207b"]["player_ships"] = ["blue-int"]
    monkeypatch.setattr(DrawHelper, "mergeLocationsFile", lambda self, positions: None)
    inter = FakeInteraction()

    run(MoveButtons.moveThisShip(game, player, inter, "moveThisShip_207b_interceptor_1"))

    labels = {button.custom_id: button.label for content, kwargs in inter.channel.sent
              for button in getattr(kwargs.get("view"), "children", [])}
    assert labels["FCIDblue_moveTo_207b_interceptor_207_1"] == "207-A"
    assert labels["FCIDblue_moveTo_207b_interceptor_207c_1"] == "207-C"


@pytest.mark.parametrize("rotation,target", [(0, "207b"), (60, "207"), (180, "207c")])
def test_black_hole_returns_to_the_rotated_border_subsector(make_game, run, rotation, target):
    game = make_game(_bare_gamestate())
    game.add_tile("207", rotation, "295")
    # Only the northern edge leads to empty space.
    for neighbor in ["206", "309", "310", "311", "208"]:
        game.gamestate["board"][neighbor] = {"sector": "101"}

    async def options():
        return BlackHoleButtons.findBlackHoleOptions(game, {"color": "blue"}, "blue-int", "bhborder", "no")

    view = run(options())
    assert [button.custom_id for button in view.children] == [f"FCIDblue_blackHoleFinish_blue-int_{target}_no"]


@pytest.mark.parametrize("rotation_a", range(0, 360, 60))
@pytest.mark.parametrize("rotation_b", range(0, 360, 60))
def test_movement_between_rotated_nebulas(make_game, monkeypatch, rotation_a, rotation_b):
    monkeypatch.setattr(PlayerHelper, "getTechs", lambda self: [])
    game = make_game(_bare_gamestate())
    game.add_tile("207", rotation_a, "295")
    game.add_tile("208", rotation_b, "395")
    board = game.gamestate["board"]
    board["207"]["player_ships"] = board["208"]["player_ships"] = []
    player = player_stats("hyd", color="blue")
    game.gamestate["players"] = {"1": player}
    # 207's NW edge meets 208's SE edge.
    source = game.nebula_subsector_for_edge("207", 5)
    target = game.nebula_subsector_for_edge("208", 2)
    assert MoveButtons.getTilesInRange(game, player, source, 1, 0) & {"208", "208b", "208c"} == {target}
    assert MoveButtons.getTilesInRange(game, player, target, 1, 0) & {"207", "207b", "207c"} == {source}


@pytest.mark.parametrize("rotation,source", [(0, "207b"), (60, "207"), (120, "207"),
                                            (180, "207c"), (240, "207c"), (300, "207b")])
def test_exploring_from_the_rotated_nebula_subsector(make_game, run, monkeypatch, rotation, source):
    game = make_game(_bare_gamestate())
    game.add_tile("207", rotation, "295")
    drawing = DrawHelper(game.gamestate)
    monkeypatch.setattr(drawing, "base_tile_image_with_rotation_in_context",
                        lambda *args: Image.new("RGBA", (1, 1)))

    async def options():
        for origin in ["207", "207b", "207c"]:
            view, image = drawing.draw_possible_oritentations("395", "104", [origin], View(), {"color": "blue"})
            assert len(view.children) == (6 if origin == source else 0)

    run(options())


def test_render_rotates_ships_and_discoveries_with_the_subsectors(make_game, monkeypatch):
    def assets(self, path):
        if "/hexes/" in path:
            return Image.new("RGBA", (1024, 890))
        if path.endswith("/anc.png"):
            return Image.new("RGBA", (326, 326), "red")
        if path.endswith("discovery_2ptback.png"):
            return Image.new("RGBA", (80, 80), "green")
        return Image.new("RGBA", (1, 1))

    monkeypatch.setattr(DrawHelper, "use_image", assets)
    labels = []
    monkeypatch.setattr(DrawHelper, "label_nebula_subsectors",
                        staticmethod(lambda image, position, rotation: labels.append((position, rotation))))
    game = make_game(_bare_gamestate())
    game.add_tile("207", 0, "295")
    baseline = DrawHelper(game.gamestate).board_tile_image("207")
    assert baseline.getbbox() is not None
    for rotation in range(0, 360, 60):
        game.add_tile("207", rotation, "295")
        rendered = DrawHelper(game.gamestate).board_tile_image("207b")
        assert ImageChops.difference(rendered, baseline.rotate(rotation)).convert("RGB").getbbox() is None
        assert labels[-1] == ("207", rotation)



def test_atlantians_nebula_choices_bury_unplaceable_discoveries(make_game):
    game = make_game({
        "board": {"202b": {"type": "nebula", "disctile": 1}},
        "discTiles": ["sci", "mon", "mat", "cru", "orb", "rep"],
    })

    assert DiscoveryTileButtons.drawAtlantiansDiscoveryChoices(game, "202b") == ["rep", "sci"]
    assert game.gamestate["discTiles"] == ["mon", "orb"]


def test_atlantians_nebula_choices_stop_when_only_unplaceable_tiles_remain(make_game):
    game = make_game({"board": {"202b": {"type": "nebula"}}, "discTiles": ["orb", "mon"]})

    assert DiscoveryTileButtons.drawAtlantiansDiscoveryChoices(game, "202b") == []
    assert sorted(game.gamestate["discTiles"]) == ["mon", "orb"]
