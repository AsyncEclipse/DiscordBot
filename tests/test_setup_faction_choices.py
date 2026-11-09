"""The setup draft: which factions it offers, their colours, and community bans."""
from Buttons.Draft import DraftButtons
from commands.setup_commands import SetupCommands
from helpers import FactionData
from tests.fakes import FakeGame


def offered_factions(game):
    return [button.custom_id.split("_")[1] for button in DraftButtons.getDraftButtons(game).children
            if button.custom_id.startswith("draftFaction_")]


def test_draft_offers_each_enabled_faction_once():
    standard = {key for key, faction in FactionData.FACTIONS.items() if not faction.get("community")}
    for community_parts in (False, True):
        standard_offered = offered_factions(FakeGame(False, community_parts))
        assert set(standard_offered) == standard
        assert len(standard_offered) == len(standard)
        community_offered = offered_factions(FakeGame(True, community_parts))
        assert set(community_offered) == set(FactionData.FACTIONS)
        assert len(community_offered) == len(set(community_offered))


def test_community_factions_respect_bans_and_do_not_colour_block():
    all_factions = set(FactionData.FACTIONS)
    for key, faction in FactionData.FACTIONS.items():
        if not faction.get("community"):
            continue
        game = FakeGame(True, False)
        game.gamestate["bannedFactions"] = [key]
        assert set(offered_factions(game)) == all_factions - {key}
        game.gamestate["bannedFactions"] = []
        game.gamestate["draftedFactions"] = [(1, key)]
        assert set(offered_factions(game)) == all_factions - {key}


def test_standard_colour_blocks_leave_community_factions_available():
    game = FakeGame(True, False)
    game.gamestate["draftedFactions"] = [(1, "hyd")]
    # Hydran blue blocks the other blue factions and nothing else.
    assert set(offered_factions(game)) == set(FactionData.FACTIONS) - {"hyd", "ter4"}


def test_setup_choices_cover_the_faction_registry():
    choices = {choice.value: choice.name for choice in SetupCommands.factionChoices}
    assert set(choices) == set(FactionData.FACTIONS)
    assert len(choices) == len(SetupCommands.factionChoices)
    for key, faction in FactionData.FACTIONS.items():
        if faction.get("community"):
            assert choices[key] == faction["name"]
        assert DraftButtons.getColor(key) == faction["setup_color"]
