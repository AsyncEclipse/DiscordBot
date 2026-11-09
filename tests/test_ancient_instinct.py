import pytest

from Buttons.Research import ResearchButtons
from helpers.PlayerHelper import PlayerHelper
from tests.fakes import FakeInteraction, buttons, player_stats, reload

SAVE_FOR_LATER = "Save For Future Upgrade Action"


class FakeGame:
    def __init__(self, player):
        self.player = player

    def get_player_from_color(self, color):
        return "1"

    def preGameTasks(self):
        return []

    def playerResearchTech(self, player_id, tech, tech_type):
        self.player[f"{tech_type}_tech"].append(tech)

    def update_player(self, player_helper):
        pass


@pytest.mark.parametrize("faction, tech, offered", [
    ("atl", "tad", True),
    ("atl", "wog", False),  # researchable, but not a ship part
    ("hyd", "tad", False),
])
def test_ancient_instinct_offers_upgrade_for_researched_part(run, faction, tech, offered):
    player = player_stats(faction, science=20)
    interaction = FakeInteraction()

    run(ResearchButtons.getTech(FakeGame(player), player, PlayerHelper("1", player), interaction,
                                f"getTech_{tech}_grid"))

    expected = {f"FCIDblue_ancientInstinctUpgrade_{tech}"} if offered else set()
    assert set(buttons(interaction.channel)) == expected


def test_ancient_instinct_installs_the_researched_part_for_free(start_game, press):
    game, channel = start_game(factions=["atl", "eri"])
    game.gamestate["available_techs"] = ["phs"]
    game.get_player(1)["science"] = 40
    game.update()

    press(channel, 1, "FCIDblue_startResearch")
    press(channel, 1, "FCIDblue_getTech_phs_grid")
    offer = next(cid for cid in buttons(channel) if cid.startswith("FCIDblue_ancientInstinctUpgrade_"))
    discs = reload(game).get_player(1)["influence_discs"]

    press(channel, 1, offer)
    ship_menu = buttons(channel)
    assert "FCIDblue_upgradeShip_1_interceptor_phs" in ship_menu
    # nothing to save: this upgrade comes from a tech, not from a kept discovery tile
    assert SAVE_FOR_LATER not in ship_menu.values()

    inter = press(channel, 1, "FCIDblue_upgradeShip_1_interceptor_phs")
    part_menu = {c.custom_id: c.label for c in inter.message.edited["view"].children}
    assert SAVE_FOR_LATER not in part_menu.values()

    press(channel, 1, next(cid for cid in part_menu if cid.endswith("_phs_0")))

    after = reload(game).get_player(1)
    assert after["interceptor_parts"] == ["phs", "nus", "nud", "empty"]
    assert after["influence_discs"] == discs
    assert after["upgrade_action_counters"] == 0
    assert "Replaced Ion Cannon with Phase Shield" in after["detailsOflastAction"]
