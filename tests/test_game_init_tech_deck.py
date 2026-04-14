import json
import pytest
import config


def _minimal_gamestate():
    return {
        "game_id": "test0",
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


def _run_setup_techs(tmp_path, community_parts: bool = False, rift_cannon: bool = True):
    """Run setup_techs_and_outer_rim() against a temp game and return the resulting gamestate."""
    from helpers.GamestateHelper import GamestateHelper

    gs = _minimal_gamestate()
    gs["community_parts"] = community_parts
    gs["rift_cannon"] = rift_cannon

    game_path = tmp_path / f"{gs['game_id']}.json"
    with open(game_path, "w") as f:
        json.dump(gs, f)

    original_path = config.gamestate_path
    config.gamestate_path = str(tmp_path)
    try:
        game = GamestateHelper(None, gs["game_id"])
        game.setup_techs_and_outer_rim(2, False, False)
        return game.gamestate
    finally:
        config.gamestate_path = original_path


def _all_techs(gs):
    return gs["tech_deck"] + gs["available_techs"]


class TestCommunityParts:
    def test_community_parts_enabled(self, tmp_path):
        gs = _run_setup_techs(tmp_path, community_parts=True)
        all_techs = _all_techs(gs)
        assert "phs" not in all_techs
        assert "imh" not in all_techs
        assert "phsmod" in all_techs
        assert "imhmod" in all_techs

    def test_community_parts_disabled(self, tmp_path):
        gs = _run_setup_techs(tmp_path, community_parts=False)
        all_techs = _all_techs(gs)
        assert "phsmod" not in all_techs
        assert "imhmod" not in all_techs
        assert "phs" in all_techs
        assert "imh" in all_techs


class TestRiftCannon:
    def test_rift_cannon_disabled(self, tmp_path):
        gs = _run_setup_techs(tmp_path, rift_cannon=False)
        assert "rican" not in _all_techs(gs)

    def test_rift_cannon_enabled(self, tmp_path):
        gs = _run_setup_techs(tmp_path, rift_cannon=True)
        assert "rican" in _all_techs(gs)
