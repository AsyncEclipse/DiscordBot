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


def test_atlantians_reference_images_exist():
    for name in ["atlantians_board.png", "atlantians_info.png"]:
        assert Path(f"images/resources/components/factions/{name}").is_file()
