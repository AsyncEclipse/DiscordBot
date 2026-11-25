"""The setup command's faction list is split across Discord messages."""
from Buttons.Draft import DraftButtons
from commands.setup_commands import SetupCommands, faction_autocomplete
from helpers import FactionData
from tests.fakes import FakeGame, FakeInteraction


def offered_factions(game):
    return [button.custom_id.split("_")[1]
            for start in range(0, len(FactionData.FACTIONS), 25)
            for button in DraftButtons.getDraftButtons(game, start).children
            if button.custom_id.startswith("draftFaction_")]


def test_draft_pages_include_each_enabled_faction_once():
    standard = {key for key, faction in FactionData.FACTIONS.items() if not faction.get("community")}
    for community_parts in (False, True):
        standard_offered = offered_factions(FakeGame(False, community_parts))
        assert set(standard_offered) == standard
        assert len(standard_offered) == len(standard)
        game = FakeGame(True, community_parts)
        offered = offered_factions(game)
        assert set(offered) == set(FactionData.FACTIONS)
        assert len(offered) == len(set(offered))
        first_message = DraftButtons.getDraftButtons(game).children
        assert len(first_message) == 25
        assert all(button.custom_id.startswith("draftFaction_") for button in first_message)
        assert len(DraftButtons.getDraftButtons(game, 25).children) == len(offered) - 25


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
    assert set(offered_factions(game)) == set(FactionData.FACTIONS) - {"hyd", "ter4"}


def test_setup_choices_cover_the_faction_registry():
    choices = {choice.value: choice.name for choice in SetupCommands.factionChoices}
    assert set(choices) == set(FactionData.FACTIONS)
    assert len(choices) == len(SetupCommands.factionChoices)
    for key, faction in FactionData.FACTIONS.items():
        if faction.get("community"):
            assert choices[key] == faction["name"]
            assert DraftButtons.getColor(key) == faction["setup_color"]


def test_setup_game_factions_use_autocomplete():
    for number in range(1, 10):
        parameter = next(p for p in SetupCommands.game.parameters if p.name == f"faction{number}")
        assert parameter.autocomplete is not None
        assert not parameter.choices


def test_faction_autocomplete_filters_and_caps_at_25(run):
    assert len(SetupCommands.factionChoices) > 25
    everything = run(faction_autocomplete(FakeInteraction(), ""))
    assert len(everything) == 25
    filtered = run(faction_autocomplete(FakeInteraction(), "vor"))
    assert [choice.value for choice in filtered] == ["vor"]
