import pytest

from Buttons.Research import ResearchButtons
from helpers.DrawHelper import DrawHelper
from helpers.PlayerHelper import PlayerHelper
from tests.fakes import FakeInteraction, buttons, player_stats


class FakeGame:
    def __init__(self, player):
        self.player = player

    def get_player_from_color(self, color):
        return "1"

    def playerResearchTech(self, player_id, tech, tech_type):
        self.player[f"{tech_type}_tech"].append(tech)

    def update_player(self, player_helper):
        pass


@pytest.mark.parametrize("faction, tech, offered", [
    ("Atlantians", "tad", True),
    ("Atlantians", "wog", False),  # researchable, but not a ship part
    ("Hydran Progress", "tad", False),
])
def test_ancient_instinct_offers_upgrade_for_researched_part(run, monkeypatch, faction, tech, offered):
    monkeypatch.setattr(DrawHelper, "show_tech_ref_image", lambda *args: None)
    player = player_stats("atl", name=faction, science=20)
    interaction = FakeInteraction()

    run(ResearchButtons.getTech(FakeGame(player), player, PlayerHelper("1", player), interaction,
                                f"getTech_{tech}_grid"))

    expected = {f"FCIDblue_ancientInstinctUpgrade_{tech}"} if offered else set()
    assert set(buttons(interaction.channel)) == expected
