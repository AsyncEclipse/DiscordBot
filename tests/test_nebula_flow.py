"""Integration: ships move into a Nebula, fight a player and the Ancient, then claim a Discovery Tile.

Set NEBULA_FLOW_OUT=<dir> to keep gamestate snapshots of each stage, e.g. for
local_debug/render_show_game.py <snapshot> <dir>.
"""
import itertools
import os
import shutil

import pytest

import config
from helpers.DrawHelper import DrawHelper
from tests.fakes import buttons, reload

P1, P2 = 1, 2


@pytest.fixture(autouse=True)
def no_images(monkeypatch):
    # rendering the map takes ~40s per press; the flow only needs the buttons
    for name in ("mergeLocationsFile", "board_tile_image_file", "player_area", "show_player_ship_area",
                 "show_AI_stats", "show_map", "show_game"):
        monkeypatch.setattr(DrawHelper, name, lambda *a, **k: None)


def _move(press, ch, pid, color, origin, ship, dest):
    press(ch, pid, f"FCID{color}_startMove")
    press(ch, pid, f"FCID{color}_moveFrom_{origin}_1")
    press(ch, pid, f"FCID{color}_moveThisShip_{origin}_{ship}_1")
    offered = set(buttons(ch).values()) - {"Restart Turn"}
    press(ch, pid, f"FCID{color}_moveTo_{origin}_{ship}_{dest}_1")
    press(ch, pid, f"FCID{color}_finishAction")
    press(ch, pid, f"FCID{color}_endTurn")
    return offered


def _ids(channel):
    return [c.custom_id for _, kw in channel.sent for c in getattr(kw.get("view"), "children", [])]


def _snapshot(game, name):
    out = os.environ.get("NEBULA_FLOW_OUT")
    if out:
        shutil.copy(os.path.join(config.gamestate_path, f"{game.game_id}.json"), os.path.join(out, f"{name}.json"))


def test_nebula_move_combat_and_discovery(start_game, press, no_random):
    game, ch = start_game()
    board = game.gamestate["board"]
    # turn both homes (wormholes 0,1,3,4) so each has a wormhole facing 202
    board["201"]["orientation"] = board["203"]["orientation"] = 60
    game.update()
    game.add_tile("202", 0, "295")
    game.gamestate["board"]["202b"]["player_ships"] = ["red-cru"]  # parked there in an earlier round
    game.update()

    # each ship enters only the Subsector owning the edge it crosses
    assert _move(press, ch, P1, "blue", "201", "interceptor", "202b") == {"202b"}
    assert _move(press, ch, P2, "red", "203", "interceptor", "202") == {"202"}
    _snapshot(game, "nebula_moved")

    press(ch, P1, "FCIDblue_passForRound")
    press(ch, P2, "FCIDred_passForRound")
    assert sorted(t.name.split("Tile ")[1] for t in ch.threads) == ["202, Combat", "202b, Combat"]
    no_random(itertools.repeat(6))
    for thread in ch.threads:
        for _ in range(10):
            roll = next((cid for cid in buttons(thread) if "rollDice_" in cid), None)
            if roll is None:
                break
            press(thread, P1 if roll.startswith("FCIDblue") else P2, roll)
        for cid in _ids(thread):
            if "_dontDrawReputation_" in cid:
                press(thread, P1 if cid.startswith("FCIDblue") else P2, cid)
        assert not any("addInfluenceFinish" in cid for cid in _ids(thread))
    board = reload(game).gamestate["board"]
    assert board["202"]["player_ships"] == ["ai-anc"]  # the Ancient wins its Subsector
    assert board["202b"]["player_ships"] == ["red-cru"]  # red's cruiser beats blue's interceptor
    _snapshot(game, "nebula_fought")

    # end of the Combat Phase: only the lone ship owner in a Discovery Subsector is offered it
    press(ch, P1, "readyForUpkeep")
    press(ch, P2, "readyForUpkeep")
    n = len(ch.sent)
    press(ch, P1, "runUpkeep")
    claims = [c.custom_id for _, kw in ch.sent[n:] for c in getattr(kw.get("view"), "children", [])
              if "exploreDiscoveryTile" in c.custom_id]
    assert claims == ["FCIDred_exploreDiscoveryTile_202b_deleteMsg"]
    press(ch, P2, claims[0])
    board = reload(game).gamestate["board"]
    assert board["202b"]["disctile"] == 0
    assert board["202c"]["disctile"] == 1
    assert "FCIDred_keepDiscForPoints" in _ids(ch)
    _snapshot(game, "nebula_claimed")
