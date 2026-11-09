import random

import pytest

from Buttons.Draft import DraftButtons
from helpers.GamestateHelper import GamestateHelper
from setup.GameInit import GameInit
from tests.fakes import FakeChannel, FakeInteraction, reload


@pytest.mark.parametrize("factions, colors", [
    (["wra", "mec"], {"The Wraith": "white", "Mechanema": "blue"}),
    (["mec", "wra"], {"Mechanema": "white", "The Wraith": "blue"}),
])
def test_multi_faction_setup_assigns_the_faction_colour_it_actually_got(games_dir, run, factions, colors):
    random.seed(0)
    GameInit("Wraith setup", [[1, "<@1>"], [2, "<@2>"]],
             "def", True, True, False, False).create_game()
    game = GamestateHelper(None, "aeb1")
    game.setup_techs_and_outer_rim(2, False, False)
    game.add_tile("000", 0, "001")
    channel = FakeChannel("aeb1-actions")
    interaction = FakeInteraction(channel, role_names=["aeb1"])

    run(DraftButtons.generalSetup(interaction, game, [1, 2], factions))

    state = reload(game).gamestate
    wraith = next(player for player in state["players"].values() if player["name"] == "The Wraith")
    other = next(player for player in state["players"].values() if player["name"] == "Mechanema")
    assert wraith["color"] == colors["The Wraith"]
    assert other["color"] == colors["Mechanema"]
    wraith_home = next(pos for pos, tile in state["board"].items() if tile.get("sector") == "254")
    assert state["board"][wraith_home]["owner"] == wraith["color"]
    assert wraith["military_tech"] == ["phm"]
    assert wraith["reputation_track"] == ["mixed", "rep", "rep", "rep"]
    assert (wraith["money"], wraith["science"], wraith["materials"]) == (2, 4, 4)
    assert wraith["wraithSouls"] == 0
