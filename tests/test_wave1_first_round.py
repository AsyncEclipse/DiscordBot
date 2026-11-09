"""The first eight community factions through setup and one full round together.

Keep the setup hooks and action flows in one game to catch conflicts between factions.
"""
import random

from Buttons.Draft import DraftButtons
from helpers.GamestateHelper import GamestateHelper
from setup.GameInit import GameInit
from tests.fakes import FakeChannel, FakeInteraction, buttons, reload

FACTIONS = ["ra", "atl", "tm", "her", "kur", "tur", "wul", "wra"]


def find_button(channel, prefix):
    return next(
        button.custom_id
        for content, kwargs in reversed(channel.sent)
        for button in getattr(kwargs.get("view"), "children", [])
        if button.custom_id.startswith(prefix)
    )


def setup_wave(games_dir, run, channel):
    random.seed(0)
    GameInit("Wave 1 first round", [[i, f"<@{i}>"] for i in range(1, 9)],
             "def", True, True, False, False, community_factions=True).create_game()
    game = GamestateHelper(None, "aeb1")
    game.setup_techs_and_outer_rim(8, False, False)
    game.gamestate["discTiles"] = ["mog", "sci", "mat", "cru"] * 3
    game.gamestate["tile_deck_100"] = ["101", "102", "103", "104", "106", "107", "109", "110"]
    game.gamestate["available_techs"] = ["neb"]
    game.update()
    interaction = FakeInteraction(channel, role_names=["aeb1"])
    run(DraftButtons.generalSetup(interaction, game, list(range(1, 9)), FACTIONS))
    return game


def test_wave1_community_factions_setup_and_first_round(games_dir, run, press):
    channel = FakeChannel("aeb1-actions")
    game = setup_wave(games_dir, run, channel)

    state = reload(game).gamestate
    colors = {pid: state["players"][str(pid)]["color"] for pid in range(1, 9)}
    homes = {
        "ra": "255", "atl": "266", "tm": "244", "her": "299",
        "kur": "251", "tur": "253", "wul": "252", "wra": "254",
    }
    for pid, key in enumerate(FACTIONS, 1):
        player = state["players"][str(pid)]
        assert player["name"].startswith({
            "ra": "Remnants of Ra", "atl": "Atlantians", "tm": "Techno-Mages",
            "her": "Heralds of Ragnarok", "kur": "Kurita Prefecture",
            "tur": "Turtugan", "wul": "The Wulfen", "wra": "The Wraith",
        }[key])
        assert player["home_planet"] == homes[key]
        assert colors[pid] in ["blue", "red", "green", "yellow", "purple",
                               "white", "pink", "brown", "teal"]
    assert state["board"]["314"]["sector"] == "253"
    assert state["board"]["314"]["number_snap"] == [680, 350]

    assert state["pre_game"]["tasks"] == [["1", "artifact_cube"], ["2", "discovery_tile"],
                                          ["3", "setup_tech"]]
    assert "activePlayerColor" not in state
    assert any("reserve" in content.lower() for content, kwargs in channel.sent)

    # The three setup prompts of the earlier community factions still resolve in one game.
    press(channel, 1, find_button(channel, f"FCID{colors[1]}_ancientsCube_science_"))
    press(channel, 2, find_button(channel, f"FCID{colors[2]}_selectDiscTile_"))
    press(channel, 2, find_button(channel, f"FCID{colors[2]}_keepDiscForPoints"))
    press(channel, 3, f"FCID{colors[3]}_setupTech")
    press(channel, 3, next(cid for cid in buttons(channel)
                           if cid.startswith(f"FCID{colors[3]}_getTech_")))

    explored = []
    for pid, key in enumerate(FACTIONS, 1):
        state = reload(game).gamestate
        color = colors[pid]
        assert state["activePlayerColor"] == [color]
        press(channel, pid, f"FCID{color}_startExplore")
        explore = next(cid for cid in buttons(channel)
                       if cid.startswith(f"FCID{color}_exploreTile_"))
        position = explore.split("_")[2]
        press(channel, pid, explore)
        reserved = [cid for cid in buttons(channel)
                    if cid.startswith(f"FCID{color}_reservedTile_{position}_")
                    and "_random_" not in cid]
        if reserved:
            press(channel, pid, reserved[0])
        press(channel, pid, find_button(channel, f"FCID{color}_placeTile_{position}_"))
        influence = [cid for cid in buttons(channel)
                     if cid.startswith(f"FCID{color}_addInfluenceFinish_{position}")]
        if influence:
            press(channel, pid, influence[0])
        press(channel, pid, f"FCID{color}_finishAction")
        press(channel, pid, f"FCID{color}_endTurn")
        state = reload(game).gamestate
        assert state["board"][position].get("sector") is not None
        assert state["board"][position]["owner"] in (color, 0)
        explored.append(position)

    assert len(set(explored)) == 8
    for pid, key in enumerate(FACTIONS, 1):
        player = reload(game).get_player(pid)
        assert player["explore_action_counters"] == 1
        assert len(player["owned_tiles"]) >= 1
    assert reload(game).gamestate["activePlayerColor"] == [colors[1]]

    tur, tur_color = FACTIONS.index("tur") + 1, colors[FACTIONS.index("tur") + 1]
    for pid in range(1, 9):
        press(channel, pid, f"FCID{colors[pid]}_passForRound")
    for pos, color in list(reload(game).gamestate.get("pendingDiscoveryResolutions", {}).items()):
        pid = next(pid for pid, player_color in colors.items() if player_color == color)
        press(channel, pid, f"FCID{color}_keepDiscForPoints_{pos}")
    press(channel, 1, "runUpkeep")
    press(channel, tur, f"FCID{tur_color}_harvesterSector_314")
    press(channel, tur, f"FCID{tur_color}_placeHarvester_314_scienceadv_0_science")
    assert reload(game).get_player(tur)["harvester_placements"] == [
        {"position": "314", "square": "scienceadv", "index": 0, "resource": "science"}]
    press(channel, 1, "runUpkeep")
    assert reload(game).gamestate["roundNum"] == 2
