from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

from Buttons.Draft import DraftButtons
from commands.setup_commands import SetupCommands
from helpers.DrawHelper import DrawHelper
from helpers.GamestateHelper import GamestateHelper
from tests.fakes import FakeChannel, FakeInteraction, FakeRole


class FakeGame:
    def __init__(self, community_mode):
        self.gamestate = {
            "communityMode": community_mode,
            "bannedFactions": [],
            "draftedFactions": [],
        }

    getShortFactionNameFromFull = GamestateHelper.getShortFactionNameFromFull


def test_atlantians_only_appear_in_community_draft():
    standard_buttons = DraftButtons.getDraftButtons(FakeGame(False))
    community_buttons = DraftButtons.getDraftButtons(FakeGame(True))

    assert len(standard_buttons.children) == 16
    assert [button.label for button in community_buttons.children].count("Atlantians") == 1
    assert len(community_buttons.children) == 17


def test_atlantians_faction_lookup_uses_renderer_key():
    game = GamestateHelper.__new__(GamestateHelper)

    assert game.getShortFactionNameFromFull("Atlantians") == "atlantians"
    assert game.get_short_faction_name("Atlantians") == "atlantians"


def test_game_creation_sends_atlantians_board_and_reference(games_dir, run, monkeypatch):
    interaction = FakeInteraction()
    interaction.guild.categories = [SimpleNamespace(name="Games #1-10")]
    interaction.guild.default_role = FakeRole("@everyone")
    interaction.guild.roles = [FakeRole("aeb1")]
    tabletalk = FakeChannel("aeb1-test")
    tabletalk.jump_url = "tabletalk"
    actions = FakeChannel("aeb1-actions")
    actions.jump_url = "actions"
    reference = FakeChannel("Faction Reference")
    actions.create_thread = AsyncMock(side_effect=[FakeChannel("aeb1-bot-map-updates"), reference])
    interaction.guild.create_text_channel = AsyncMock(side_effect=[tabletalk, actions])
    monkeypatch.setattr(DrawHelper, "show_available_techs", lambda self: None)
    monkeypatch.setattr(DrawHelper, "show_minor_species", lambda self: None)
    monkeypatch.setattr(DrawHelper, "show_AI_stats", lambda self: None)

    def get_reference_file(self, filename):
        assert Path(filename).is_file()
        return filename

    monkeypatch.setattr(DrawHelper, "get_file", get_reference_file)
    run(SetupCommands.create_new_game.callback(
        SetupCommands(None), interaction, "test", SimpleNamespace(id=1), 2,
        player2=SimpleNamespace(id=2)))

    atlantians_messages = [(content, kwargs["file"]) for content, kwargs in reference.sent
                          if "file" in kwargs and "atlantians" in kwargs["file"]]
    assert [filename for content, filename in atlantians_messages] == [
        "images/resources/components/factions/atlantians_board.png",
        "images/resources/components/factions/atlantians_info.png",
    ]
    for rule in ["Ancient Labs", "Ancient Spirit", "Ancient Instinct", "Ancient Power", "Price of Power"]:
        assert rule in atlantians_messages[0][0]
