"""Nebula Sector rules: 295/395 are one hex split into three Subsectors."""
from Buttons.Move import MoveButtons
from helpers.PlayerHelper import PlayerHelper


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
    assert board["207b"]["adjacent"] == ["104", "208", "207c", "207"]
    assert board["207c"]["adjacent"] == ["310", "311", "207b", "207"]


def test_nebula_edge_resolution_rotates_with_orientation(make_game):
    game = make_game(_bare_gamestate())
    game.add_tile("207", 120, "295")
    board = game.gamestate["board"]
    assert board["207"]["adjacent"][:2] == ["208", "104"]
    assert board["207b"]["adjacent"][:2] == ["311", "310"]
    assert board["207c"]["adjacent"][:2] == ["206", "309"]
    assert game.nebula_subsector_for_edge("207", 0, None) == "207c"
    assert game.nebula_subsector_for_edge("207", 1, None) == "207b"
    assert game.nebula_subsector_for_edge("207", 3, None) == "207"


def test_nebula_internal_move_needs_two_activations(make_game, monkeypatch):
    monkeypatch.setattr(PlayerHelper, "getTechs", lambda self: [])
    game = make_game(_bare_gamestate())
    game.add_tile("207", 0, "295")
    game.add_tile("104", 0, "101")
    game.add_tile("208", 0, "201")
    game.gamestate["players"] = {"1": {"color": "blue", "name": "Blue", "player_name": "Blue"}}
    game.gamestate["board"]["207b"]["player_ships"] = ["blue-int"]
    game.update()
    player = {"color": "blue", "name": "Blue", "player_name": "Blue"}
    tiles1 = MoveButtons.getTilesInRange(game, player, "207b", 1, 0)
    assert tiles1 == {"207b", "104", "208"}
    tiles2 = MoveButtons.getTilesInRange(game, player, "207b", 2, 0)
    assert {"207c", "207"} <= tiles2


def test_move_into_nebula_lands_in_edge_owning_subsector(make_game, monkeypatch):
    monkeypatch.setattr(PlayerHelper, "getTechs", lambda self: [])
    game = make_game(_bare_gamestate())
    game.add_tile("207", 0, "295")
    game.add_tile("104", 0, "101")
    # tile 101 spawns an Ancient that would pin the ship; the test only needs the map topology
    game.gamestate["board"]["104"]["player_ships"] = []
    game.gamestate["players"] = {"1": {"color": "blue", "name": "Blue", "player_name": "Blue"}}
    game.update()
    # 104 sits south of 207, so the shared edge belongs to the SW discovery wedge
    tiles = MoveButtons.getTilesInRange(game, {"color": "blue", "name": "Blue", "player_name": "Blue"}, "104", 1, 0)
    assert "207c" in tiles
    assert "207" not in tiles and "207b" not in tiles


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
