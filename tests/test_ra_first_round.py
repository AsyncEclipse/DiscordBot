"""Remnants of Ra through setup and a full first round, on the real engine and save files."""
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


def test_remnants_of_ra_and_atlantians_explore_then_pass(games_dir, run, press, monkeypatch):
    """Engine only: the round's flows render art internally, so it is stubbed out (the stub
    checks the file exists)."""
    random.seed(0)

    def load_thumbnail(self, filename):
        assert Path(filename).is_file(), filename
        return Image.new("RGBA", (1024, 890))

    monkeypatch.setattr(DrawHelper, "use_image", load_thumbnail)
    monkeypatch.setattr(DrawHelper, "use_resized_image",
                        lambda self, filename, size: self.use_image(filename).resize(size))
    GameInit("Remnants of Ra first round", [[1, "<@1>"], [2, "<@2>"]],
             "def", True, True, False, False, community_factions=True).create_game()
    game = GamestateHelper(None, "aeb1")
    game.setup_techs_and_outer_rim(2, False, False)
    game.gamestate["discTiles"] = ["mog", "sci", "mat", "cru"]
    game.gamestate["tile_deck_100"] = ["102", "103"]
    game.update()
    channel = FakeChannel("aeb1-actions")
    interaction = FakeInteraction(channel, role_names=["aeb1"])
    run(DraftButtons.generalSetup(interaction, game, [1, 2], ["ra", "atl"]))

    state = reload(game).gamestate
    assert state["players"]["1"]["name"] == "Remnants of Ra"
    assert state["players"]["1"]["military_tech"] == ["plc"]
    assert state["players"]["1"]["reputation_track"] == ["mixed", "mixed", "mixed", "mixed"]
    assert state["players"]["1"]["money"] == 2
    assert state["players"]["2"]["name"] == "Atlantians"
    assert state["players"]["2"]["nano_tech"] == ["anl"]
    assert state["board"]["201"]["sector"] == "255"
    assert state["board"]["207"]["sector"] == "266"
    assert state["activePlayerColor"] == ["blue"]

    # Power of the Ancients includes the home sector: the setup offers the disc cube.
    press(channel, 1, find_button(channel, "FCIDblue_ancientsCube_science_"))
    state = reload(game).gamestate
    assert state["board"]["201"]["disc_pop"] == [1]
    assert state["players"]["1"]["science_pop_cubes"] == 11

    # The other community setup hook, Atlantians' discovery choice, runs in the same game.
    press(channel, 2, find_button(channel, "FCIDred_selectDiscTile_"))
    press(channel, 2, find_button(channel, "FCIDred_keepDiscForPoints"))
    assert reload(game).get_player(2)["disc_tiles_for_points"] == 1

    explored_positions = []
    for player_id, color in [(1, "blue"), (2, "red")]:
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

    press(channel, 1, "FCIDblue_passForRound")
    assert reload(game).gamestate["activePlayerColor"] == ["red"]
    press(channel, 2, "FCIDred_passForRound")
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
    # 3/3/2 from the card, plus the 2 money an Explore grants.
    assert final_game.get_player(1)["materials"] == 3
    assert final_game.get_player(1)["science"] == 3
    assert final_game.get_player(1)["money"] == 4
    # Atlantians start 3/3/3, kept their setup discovery tile for 2 points, and did not pass first.
    assert final_game.get_player(2)["materials"] == 3
    assert final_game.get_player(2)["science"] == 3
    assert final_game.get_player(2)["money"] == 3
