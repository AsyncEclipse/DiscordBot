import pytest

from Buttons.Draft import DraftButtons
from Buttons.Research import ResearchButtons
from commands.setup_commands import SetupCommands
from tests.fakes import FakeGame, FakeInteraction, buttons


@pytest.mark.parametrize("community_mode", [False, True])
def test_tm_only_appears_in_community_draft(community_mode):
    standard_buttons = DraftButtons.getDraftButtons(FakeGame(False, community_mode))
    community_buttons = DraftButtons.getDraftButtons(FakeGame(True, community_mode))

    assert len(standard_buttons.children) == 16
    assert [button.label for button in standard_buttons.children].count("Techno-Mages") == 0
    assert [button.label for button in community_buttons.children].count("Techno-Mages") == 1
    assert len(community_buttons.children) == 19


def test_tm_faction_color_is_supported_setup_color():
    supported_colors = ["blue", "red", "green", "yellow", "purple", "white", "pink", "brown", "teal"]
    assert DraftButtons.getColor("tm") in supported_colors


@pytest.mark.parametrize("drafted, available", [
    (["hyd"], {"tm", "atl", "ter1"}),   # hyd is blue; atl and tm are community, so never colour blocked
    (["ter1"], {"tm", "atl", "hyd"}),   # tm shares purple with ter1: the draft offers both
    (["atl"], {"tm", "hyd", "ter1"}),
    (["tm"], {"atl", "hyd", "ter1"}),
    (["tm", "hyd"], {"atl", "ter1"}),
])
def test_techno_mages_do_not_share_colour_blocks(drafted, available):
    game = FakeGame(True, False)
    game.gamestate["draftedFactions"] = list(enumerate(drafted))

    buttons = DraftButtons.getDraftButtons(game)
    available_keys = {button.custom_id.split("_")[1] for button in buttons.children}

    assert available_keys & {"tm", "atl", "hyd", "ter1"} == available


def test_tm_still_respects_explicit_bans():
    game = FakeGame(True, False)
    game.gamestate["bannedFactions"] = ["tm"]

    assert "Techno-Mages" not in [button.label for button in DraftButtons.getDraftButtons(game).children]


def test_tm_faction_choice_exists():
    choices = [(choice.name, choice.value) for choice in SetupCommands.factionChoices]
    assert ("Techno-Mages", "tm") in choices


def test_only_techno_mages_are_offered_the_pregame_tech(start_game, run):
    game, channel = start_game(factions=["hyd", "eri"])
    run(ResearchButtons.offerSetupTech(game, game.get_player(1), FakeInteraction(channel)))
    assert not [content for content, _ in channel.sent]

    game, channel = start_game(factions=["tm", "eri"])
    run(ResearchButtons.offerSetupTech(game, game.get_player(1), FakeInteraction(channel)))
    assert "FCIDblue_setupTech" in buttons(channel)
