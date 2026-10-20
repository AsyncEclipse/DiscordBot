import pytest

from Buttons.Draft import DraftButtons
from commands.setup_commands import SetupCommands
from tests.fakes import FakeGame


@pytest.mark.parametrize("community_mode", [False, True])
def test_ra_only_appears_in_community_draft(community_mode):
    standard_buttons = DraftButtons.getDraftButtons(FakeGame(False, community_mode))
    community_buttons = DraftButtons.getDraftButtons(FakeGame(True, community_mode))

    assert len(standard_buttons.children) == 16
    assert [button.label for button in standard_buttons.children].count("Remnants of Ra") == 0
    assert [button.label for button in community_buttons.children].count("Remnants of Ra") == 1
    assert len(community_buttons.children) == 19


def test_ra_faction_color_is_yellow():
    assert DraftButtons.getColor("ra") == "yellow"


@pytest.mark.parametrize("drafted, available", [
    (["hyd"], {"ra", "atl"}),
    (["ter4"], {"ra", "atl"}),
    (["atl"], {"ra", "hyd", "ter4"}),
    (["ra"], {"atl", "hyd", "ter4"}),
    (["ra", "hyd"], {"atl"}),
    (["atl", "hyd"], {"ra"}),
])
def test_remnants_do_not_share_colour_blocks(drafted, available):
    game = FakeGame(True, False)
    game.gamestate["draftedFactions"] = list(enumerate(drafted))

    buttons = DraftButtons.getDraftButtons(game)
    available_keys = {button.custom_id.split("_")[1] for button in buttons.children}

    assert available_keys & {"ra", "atl", "hyd", "ter4"} == available


def test_remnants_still_respect_explicit_bans():
    game = FakeGame(True, False)
    game.gamestate["bannedFactions"] = ["ra"]

    assert "Remnants of Ra" not in [button.label for button in DraftButtons.getDraftButtons(game).children]


def test_ra_faction_choice_exists():
    choices = [(choice.name, choice.value) for choice in SetupCommands.factionChoices]
    assert ("Remnants of Ra", "ra") in choices
