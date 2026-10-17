"""Techno-Mages through setup and a full first round, on the real engine and save files."""
import random
from pathlib import Path

from PIL import Image

from Buttons.Draft import DraftButtons
from helpers.DrawHelper import DrawHelper
from helpers.GamestateHelper import GamestateHelper
from setup.GameInit import GameInit
from tests.fakes import FakeChannel, FakeInteraction, buttons, reload


def find_button(channel, prefix):
    return next(
        button.custom_id
        for content, kwargs in reversed(channel.sent)
        for button in getattr(kwargs.get("view"), "children", [])
        if button.custom_id.startswith(prefix)
    )


def test_techno_mages_and_atlantians_explore_then_pass(games_dir, run, press, monkeypatch):
    """Engine only: the round's flows render art internally, so it is stubbed out (the stub
    checks the file exists)."""
    random.seed(0)

    def load_thumbnail(self, filename):
        assert Path(filename).is_file(), filename
        return Image.new("RGBA", (1024, 890))

    monkeypatch.setattr(DrawHelper, "use_image", load_thumbnail)
    monkeypatch.setattr(DrawHelper, "use_resized_image",
                        lambda self, filename, size: self.use_image(filename).resize(size))
    GameInit("Techno-Mages first round", [[1, "<@1>"], [2, "<@2>"]],
             "def", True, True, False, False, community_factions=True).create_game()
    game = GamestateHelper(None, "aeb1")
    game.setup_techs_and_outer_rim(2, False, False)
    game.gamestate["discTiles"] = ["mog", "sci", "mat", "cru"]
    game.gamestate["tile_deck_100"] = ["102", "103"]
    game.gamestate["available_techs"] = ["neb"]
    game.update()
    channel = FakeChannel("aeb1-actions")
    interaction = FakeInteraction(channel, role_names=["aeb1"])
    run(DraftButtons.generalSetup(interaction, game, [1, 2], ["tm", "atl"]))

    state = reload(game).gamestate
    assert state["players"]["1"]["name"] == "Techno-Mages"
    assert state["players"]["1"]["military_tech"] == []
    assert state["players"]["1"]["reputation_track"] == ["amb", "mixed", "mixed", "mixed"]
    # 2/6/3 from the board's storage strip, one Build activation, both home science squares populated.
    assert (state["players"]["1"]["materials"], state["players"]["1"]["science"],
            state["players"]["1"]["money"]) == (2, 6, 3)
    assert state["players"]["1"]["build_apt"] == 1
    assert state["players"]["1"]["science_pop_cubes"] == 10
    assert state["board"]["201"]["sector"] == "244"
    assert state["board"]["207"]["sector"] == "266"
    assert state["activePlayerColor"] == ["purple"]

    # The pre-game tech purchase: one technology from the standard menu, no influence disc.
    # generalSetup hands the first faction purple, and atl takes the still-free blue.
    discs = state["players"]["1"]["influence_discs"]
    press(channel, 1, "FCIDpurple_setupTech")
    press(channel, 1, next(cid for cid in buttons(channel) if cid.startswith("FCIDpurple_getTech_")))
    player = reload(game).get_player(1)
    assert player["military_tech"] == ["neb"]
    assert player["science"] == 4
    assert player["influence_discs"] == discs

    # The other community setup hook, Atlantians' discovery choice, runs in the same game.
    press(channel, 2, find_button(channel, "FCIDblue_selectDiscTile_"))
    press(channel, 2, find_button(channel, "FCIDblue_keepDiscForPoints"))
    assert reload(game).get_player(2)["disc_tiles_for_points"] == 1

    explored_positions = []
    for player_id, color in [(1, "purple"), (2, "blue")]:
        assert reload(game).gamestate["activePlayerColor"] == [color]
        press(channel, player_id, f"FCID{color}_startExplore")
        explore = next(custom_id for custom_id in buttons(channel)
                       if custom_id.startswith(f"FCID{color}_exploreTile_1"))
        position = explore.split("_")[2]
        explored_positions.append(position)
        press(channel, player_id, explore)
        placement = find_button(channel, f"FCID{color}_placeTile_{position}_")
        press(channel, player_id, placement)
        press(channel, player_id, find_button(channel, f"FCID{color}_addInfluenceFinish_{position}"))
        assert reload(game).gamestate["board"][position]["owner"] == color
        press(channel, player_id, f"FCID{color}_finishAction")
        press(channel, player_id, f"FCID{color}_endTurn")

    press(channel, 1, "FCIDpurple_passForRound")
    assert reload(game).gamestate["activePlayerColor"] == ["blue"]
    press(channel, 2, "FCIDblue_passForRound")
    final_game = reload(game)
    assert final_game.is_everyone_passed()
    assert "runUpkeep" in buttons(channel)
    assert len(set(explored_positions)) == 2
    assert {final_game.gamestate["board"][position]["sector"]
            for position in explored_positions} == {"102", "103"}
    for player in final_game.gamestate["players"].values():
        assert player["explore_action_counters"] == 1
        assert len(player["owned_tiles"]) == 2
        assert player["passed"]
    # 2/4/3 after the pre-game tech, plus the 2 money for passing first.
    assert final_game.get_player(1)["materials"] == 2
    assert final_game.get_player(1)["science"] == 4
    assert final_game.get_player(1)["money"] == 5
    # Atlantians start 3/3/3, kept their setup discovery tile for 2 points, and did not pass first.
    assert final_game.get_player(2)["materials"] == 3
    assert final_game.get_player(2)["science"] == 3
    assert final_game.get_player(2)["money"] == 3