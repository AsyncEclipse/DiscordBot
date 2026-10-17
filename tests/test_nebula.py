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

