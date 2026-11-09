def _minimal_gamestate():
    return {
        "game_name": "Test",
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
        "reputation_tiles": [4, 3, 2, 1],
        "discTiles": [],
        "players": {},
        "board": {},
    }


def _setup_techs(make_game, community_parts=False, rift_cannon=True):
    """Run setup_techs_and_outer_rim() on a minimal game and return the resulting gamestate."""
    game = make_game({**_minimal_gamestate(), "community_parts": community_parts, "rift_cannon": rift_cannon})
    game.setup_techs_and_outer_rim(2, False, False)
    return game.gamestate["tech_deck"] + game.gamestate["available_techs"]


def test_community_parts_enabled(make_game):
    techs = _setup_techs(make_game, community_parts=True)
    assert "phs" not in techs
    assert "imh" not in techs
    assert "phsmod" in techs
    assert "imhmod" in techs


def test_community_parts_disabled(make_game):
    techs = _setup_techs(make_game, community_parts=False)
    assert "phsmod" not in techs
    assert "imhmod" not in techs
    assert "phs" in techs
    assert "imh" in techs


def test_rift_cannon_disabled(make_game):
    assert "rican" not in _setup_techs(make_game, rift_cannon=False)


def test_rift_cannon_enabled(make_game):
    assert "rican" in _setup_techs(make_game, rift_cannon=True)
