from pathlib import Path

import pytest

from Buttons.Draft import DraftButtons
from helpers.GamestateHelper import GamestateHelper


class FakeGame:
    def __init__(self, community_factions, community_mode):
        self.gamestate = {
            "community_factions": community_factions,
            "communityMode": community_mode,
            "bannedFactions": [],
            "draftedFactions": [],
        }

    getShortFactionNameFromFull = GamestateHelper.getShortFactionNameFromFull


@pytest.mark.parametrize("community_mode", [False, True])
def test_atlantians_only_appear_in_community_draft(community_mode):
    standard_buttons = DraftButtons.getDraftButtons(FakeGame(False, community_mode))
    community_buttons = DraftButtons.getDraftButtons(FakeGame(True, community_mode))

    assert len(standard_buttons.children) == 16
    assert [button.label for button in community_buttons.children].count("Atlantians") == 1
    assert len(community_buttons.children) == 17


@pytest.mark.parametrize("drafted, available", [
    (["hyd"], {"atl"}),
    (["ter4"], {"atl"}),
    (["atl"], {"hyd", "ter4"}),
    (["atl", "hyd"], set()),
    (["atl", "ter4"], set()),
])
def test_community_factions_do_not_share_colour_blocks(drafted, available):
    game = FakeGame(True, False)
    game.gamestate["draftedFactions"] = list(enumerate(drafted))

    buttons = DraftButtons.getDraftButtons(game)
    available_keys = {button.custom_id.split("_")[1] for button in buttons.children}

    assert available_keys & {"atl", "hyd", "ter4"} == available


def test_community_factions_still_respect_explicit_bans():
    game = FakeGame(True, False)
    game.gamestate["bannedFactions"] = ["atl"]

    buttons = DraftButtons.getDraftButtons(game)

    assert "Atlantians" not in [button.label for button in buttons.children]


def test_atlantians_reference_images_exist():
    for name in ["atlantians_board.png", "atlantians_info.png"]:
        assert Path(f"images/resources/components/factions/{name}").is_file()
