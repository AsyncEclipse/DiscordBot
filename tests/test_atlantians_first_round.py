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


def test_atlantians_and_terran_explore_then_pass(games_dir, run, press, monkeypatch):
    random.seed(0)
    loaded_images = []
    # Keep the real orientation choices while omitting thumbnail rendering in tests.
    def load_thumbnail(self, filename):
        assert Path(filename).is_file(), filename
        loaded_images.append(filename)
        return Image.new("RGBA", (1024, 890))

    monkeypatch.setattr(DrawHelper, "use_image", load_thumbnail)
    monkeypatch.setattr(DrawHelper, "use_resized_image",
                        lambda self, filename, size: self.use_image(filename).resize(size))
    monkeypatch.setattr(DrawHelper, "show_disc_tile", lambda self, name: None)
    GameInit("Atlantians first round", [[1, "<@1>"], [2, "<@2>"]],
             "def", True, True, False, False, community_factions=True).create_game()
    game = GamestateHelper(None, "aeb1")
    game.setup_techs_and_outer_rim(2, False, False)
    game.gamestate["discTiles"] = ["mog", "sci", "mat", "cru"]
    game.gamestate["tile_deck_100"] = ["102", "103"]
    game.update()
    channel = FakeChannel("aeb1-actions")
    interaction = FakeInteraction(channel, role_names=["aeb1"])
    run(DraftButtons.generalSetup(interaction, game, [1, 2], ["atl", "ter4"]))

    state = reload(game).gamestate
    assert state["players"]["1"]["name"] == "Atlantians"
    assert state["players"]["1"]["nano_tech"] == ["anl"]
    assert state["players"]["1"]["reputation_track"] == ["rep", "rep", "mixed", "mixed"]
    assert state["players"]["2"]["name"] == "Terran Federation"
    assert state["board"]["201"]["sector"] == "266"
    assert state["activePlayerColor"] == ["blue"]
    choice = find_button(channel, "FCIDblue_selectDiscTile_")
    assert choice.split("_")[2] == "sci"
    press(channel, 1, choice)
    press(channel, 1, find_button(channel, "FCIDblue_usedDiscForAbility_"))
    assert reload(game).get_player(1)["science"] == 8

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
        assert DrawHelper(final_game.gamestate).player_area(player).size == (5000, 800)
    DrawHelper(final_game.gamestate).display_turn_order()
    assert loaded_images.count("images/resources/components/layouts/factionImages/atlantians_image.png") == 3
    assert "images/resources/components/layouts/faction_titles/name_trade_atlantians.png" in loaded_images
    for ship in ["interceptor", "cruiser", "dreadnought", "starbase"]:
        assert f"images/resources/components/layouts/blueprints/classes/atlantians_{ship}_class.png" in loaded_images
    assert final_game.get_player(1)["materials"] == 3
    assert final_game.get_player(1)["money"] == 5
    assert final_game.get_player(1)["science"] == 8
