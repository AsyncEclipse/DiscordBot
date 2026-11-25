"""Children of Cog, Legion of Midas, The Horde, Vorlons and the Hegemony through setup and a round."""
import random

from Buttons.Draft import DraftButtons
from helpers.GamestateHelper import GamestateHelper
from setup.GameInit import GameInit
from tests.fakes import FakeChannel, FakeInteraction, buttons, reload

FACTIONS = ["cog", "mid", "hor", "vor", "heg"]
NAMES = {"cog": "Children of Cog", "mid": "Legion of Midas", "hor": "The Horde",
         "vor": "Vorlons", "heg": "Hegemony of the Highest Cushion"}
HOMES = {"cog": "256", "mid": "277", "hor": "288", "vor": "235", "heg": "276"}


def find_button(channel, prefix):
    return next(
        button.custom_id
        for content, kwargs in reversed(channel.sent)
        for button in getattr(kwargs.get("view"), "children", [])
        if button.custom_id.startswith(prefix)
    )


def test_community5_factions_setup_and_first_round(games_dir, run, press):
    random.seed(0)
    GameInit("Wave 5 first round", [[i, f"<@{i}>"] for i in range(1, 6)],
             "def", True, True, False, False, community_factions=True).create_game()
    game = GamestateHelper(None, "aeb1")
    game.setup_techs_and_outer_rim(5, False, False)
    game.gamestate["discTiles"] = ["mog", "sci", "mat", "cru"]
    game.gamestate["tile_deck_100"] = ["101", "102", "103", "104", "105", "106"]
    game.update()
    channel = FakeChannel("aeb1-actions")
    interaction = FakeInteraction(channel, role_names=["aeb1"])
    run(DraftButtons.generalSetup(interaction, game, [1, 2, 3, 4, 5], FACTIONS))

    state = reload(game).gamestate
    colors = {pid: state["players"][str(pid)]["color"] for pid in range(1, 6)}
    for pid, key in enumerate(FACTIONS, 1):
        player = state["players"][str(pid)]
        assert player["name"].startswith(NAMES[key])
        assert player["home_planet"] == HOMES[key]
    midas = FACTIONS.index("mid") + 1
    midas_color = colors[midas]
    assert state["pre_game"]["tasks"] == [[str(midas), "neutral_pop"]]
    press(channel, midas, find_button(channel, f"FCID{midas_color}_midasNeutralPop_money"))
    state = reload(game).gamestate
    assert state["pre_game"]["tasks"] == []
    assert state["activePlayerColor"] == [colors[1]]

    midas_tile = next(tile for tile in state["board"].values() if tile.get("owner") == midas_color)
    assert midas_tile["neutral_pop"] == [1]
    assert midas_tile["moneyadv_pop"] == [1]
    assert state["players"][str(midas)]["money_pop_cubes"] == 10

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

    assert len(set(explored)) == 5
    for pid in range(1, 6):
        player = reload(game).get_player(pid)
        assert player["explore_action_counters"] == 1
        assert len(player["owned_tiles"]) >= 1
    assert reload(game).gamestate["activePlayerColor"] == [colors[1]]

    for pid in range(1, 6):
        press(channel, pid, f"FCID{colors[pid]}_passForRound")
    for pos, color in list(reload(game).gamestate.get("pendingDiscoveryResolutions", {}).items()):
        pid = next(pid for pid, player_color in colors.items() if player_color == color)
        press(channel, pid, f"FCID{color}_keepDiscForPoints_{pos}")
    press(channel, 1, "runUpkeep")
    final = reload(game)
    assert final.gamestate["roundNum"] == 2

    # three more Nano techs each, so the round-1 render shows a filled tray
    for pid in range(1, 6):
        player = final.get_player(pid)
        extra = [tech for tech in ["nar", "fud", "adr", "adl", "orb"] if tech not in player["nano_tech"]][:3]
        player["nano_tech"] += extra
    final.update()
    assert all(len(reload(game).get_player(pid)["nano_tech"]) >= 3 for pid in range(1, 6))
