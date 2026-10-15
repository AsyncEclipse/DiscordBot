import pytest

from Buttons.Draft import DraftButtons
from commands.setup_commands import SetupCommands
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
def test_ra_only_appears_in_community_draft(community_mode):
    standard_buttons = DraftButtons.getDraftButtons(FakeGame(False, community_mode))
    community_buttons = DraftButtons.getDraftButtons(FakeGame(True, community_mode))

    assert len(standard_buttons.children) == 16
    assert [button.label for button in standard_buttons.children].count("Remnants of Ra") == 0
    assert [button.label for button in community_buttons.children].count("Remnants of Ra") == 1
    assert len(community_buttons.children) == 18


def test_ra_faction_color_is_supported_setup_color():
    supported_colors = ["blue", "red", "green", "yellow", "purple", "white", "pink", "brown", "teal"]
    assert DraftButtons.getColor("ra") in supported_colors


def test_ra_faction_choice_exists():
    choices = [(choice.name, choice.value) for choice in SetupCommands.factionChoices]
    assert ("Remnants of Ra", "ra") in choices
