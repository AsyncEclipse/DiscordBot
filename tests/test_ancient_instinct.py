import asyncio
import json

import pytest

from Buttons.Research import ResearchButtons
from Buttons.Upgrade import UpgradeButtons
from helpers.DrawHelper import DrawHelper
from helpers.PlayerHelper import PlayerHelper
from helpers.ShipHelper import PlayerShip
from tests.fakes import FakeInteraction, FakeMessage, player_stats


class FakeGame:
    def __init__(self, player):
        self.gamestate = {"players": {"1": player}, "available_techs": ["gas"]}
        self.player = player

    def get_player_from_color(self, color):
        return "1"

    def getShipsWithParts(self, player):
        return ["interceptor"]

    def getShipShortName(self, ship):
        return "int"

    def update_player(self, player_helper):
        pass

    def playerResearchTech(self, player_id, tech, tech_type):
        self.player[f"{tech_type}_tech"].append(tech)

    def get_short_faction_name(self, name):
        return "atl"


def test_ancient_instinct_upgrades_only_its_researched_tech_once(monkeypatch):
    player = player_stats("atl", grid_tech=["tad", "gas"], ancientInstinctResearchAction=True,
                          ancientInstinctAvailableTechs=[], ancientInstinctUsed=False)
    game = FakeGame(player)
    monkeypatch.setattr(DrawHelper, "player_area", lambda self, stats: None)
    monkeypatch.setattr(DrawHelper, "show_player_ship_area", lambda self, image: None)
    monkeypatch.setattr(DrawHelper, "availablePartsFile", lambda self, parts: None)
    monkeypatch.setattr(DrawHelper, "show_player_ship", lambda self, image, ship, name: None)
    monkeypatch.setattr(PlayerShip, "check_valid_ship", lambda self: True)

    interaction = FakeInteraction()
    interaction.message = None
    asyncio.run(ResearchButtons.offerAncientInstinctUpgrade(
        game, player, PlayerHelper("1", player), interaction, "tad", {"name": "Tachyon Drive"}))
    asyncio.run(ResearchButtons.offerAncientInstinctUpgrade(
        game, player, PlayerHelper("1", player), interaction, "gas", {"name": "Gauss Shield"}))
    assert player["ancientInstinctAvailableTechs"] == ["tad", "gas"]
    assert interaction.channel.sent[-2][1]["view"].children[0].custom_id == \
        "FCIDblue_ancientInstinctUpgrade_tad"
    asyncio.run(UpgradeButtons.startAncientInstinctUpgrade(game, player, interaction, "tad"))
    ship_choice = interaction.channel.sent[-1][1]["view"].children[0].custom_id
    assert ship_choice == "FCIDblue_upgradeShip_1_interceptor_free_ai_tad"

    asyncio.run(UpgradeButtons.upgradeShip(
        game, player, interaction, "upgradeShip_1_interceptor_free_ai_tad", PlayerHelper("1", player)))
    old_part_choice = interaction.channel.sent[-1][1]["view"].children[0].custom_id
    assert old_part_choice == "FCIDblue_selectOldPart_1_interceptor_ioc_free_0_ai_tad"

    asyncio.run(UpgradeButtons.selectOldPart(
        game, player, interaction, "selectOldPart_1_interceptor_ioc_free_0_ai_tad", PlayerHelper("1", player)))
    tech_choice = interaction.channel.sent[-1][1]["view"].children[1].custom_id
    assert tech_choice == "FCIDblue_chooseUpgrade_1_interceptor_ioc_tad_0_free_ai_tad"

    asyncio.run(UpgradeButtons.chooseUpgrade(
        game, player, interaction, "chooseUpgrade_1_interceptor_ioc_tad_0_free_ai_tad", PlayerHelper("1", player)))
    assert player["interceptor_parts"][0] == "tad"
    assert player["ancientInstinctUsed"] is True
    assert player["influence_discs"] == player_stats("atl")["influence_discs"]

    asyncio.run(UpgradeButtons.chooseUpgrade(
        game, player, interaction, "chooseUpgrade_1_interceptor_ioc_tad_0_free_ai_tad", PlayerHelper("1", player)))
    assert interaction.followup.sent[-1][0] == "That Ancient Instinct upgrade is not available."
    assert player["interceptor_parts"][0] == "tad"

    asyncio.run(UpgradeButtons.undoUpgrade(
        game, player, interaction, "undoUpgrade_1", PlayerHelper("1", player)))
    assert interaction.followup.sent[-1][0] == "That upgrade can no longer be undone."
    assert player["interceptor_parts"][0] == "tad"

    interaction.message = FakeMessage()
    undo_view = interaction.channel.sent[-1][1]["view"]
    undo_button = next(button for button in undo_view.children if button.custom_id.startswith("FCIDblue_undoUpgrade"))
    assert undo_button.custom_id == "FCIDblue_undoUpgrade_1_ai_tad"
    asyncio.run(UpgradeButtons.undoUpgrade(
        game, player, interaction, undo_button.custom_id.removeprefix("FCIDblue_"), PlayerHelper("1", player)))
    assert player["interceptor_parts"][0] == "ioc"
    assert player["ancientInstinctUsed"] is False
    asyncio.run(UpgradeButtons.chooseUpgrade(
        game, player, interaction, "chooseUpgrade_1_interceptor_ioc_tad_0_free_ai_tad", PlayerHelper("1", player)))
    assert player["interceptor_parts"][0] == "tad"
    assert player["ancientInstinctUsed"] is True


def test_ancient_instinct_does_not_offer_a_tech_without_a_ship_part():
    player = player_stats("atl", ancientInstinctResearchAction=True,
                          ancientInstinctAvailableTechs=[], ancientInstinctUsed=False)
    interaction = FakeInteraction()
    game = FakeGame(player)
    with open("data/parts.json", "r") as parts_file:
        parts = json.load(parts_file)

    assert "wog" not in parts
    asyncio.run(ResearchButtons.offerAncientInstinctUpgrade(
        game, player, PlayerHelper("1", player), interaction, "wog", {"name": "Wormhole Generator"}))
    assert interaction.channel.sent == []
    assert player["ancientInstinctAvailableTechs"] == []


@pytest.mark.parametrize("button_command", [True, False])
def test_research_action_offers_ancient_instinct_for_the_new_tech(monkeypatch, button_command):
    player = player_stats("atl", science=3)
    game = FakeGame(player)
    interaction = FakeInteraction()
    initial_influence = player["influence_discs"]
    monkeypatch.setattr(DrawHelper, "show_available_techs", lambda self: None)
    monkeypatch.setattr(DrawHelper, "show_tech_ref_image", lambda *args: None)

    asyncio.run(ResearchButtons.startResearch(
        game, player, PlayerHelper("1", player), interaction, button_command))
    assert player["ancientInstinctResearchAction"] is True
    research_button = next(
        button.custom_id for _content, kwargs in interaction.channel.sent
        for button in getattr(kwargs.get("view"), "children", [])
        if button.custom_id == "FCIDblue_getTech_gas_grid")
    asyncio.run(ResearchButtons.getTech(
        game, player, PlayerHelper("1", player), interaction, research_button.removeprefix("FCIDblue_")))

    assert "gas" in player["grid_tech"]
    assert player["ancientInstinctAvailableTechs"] == ["gas"]
    assert player["influence_discs"] == initial_influence - int(button_command)
    assert any(
        button.custom_id == "FCIDblue_ancientInstinctUpgrade_gas"
        for _content, kwargs in interaction.channel.sent
        for button in getattr(kwargs.get("view"), "children", []))


def test_regular_upgrade_menu_keeps_its_existing_custom_id(monkeypatch):
    player = player_stats("atl")
    game = FakeGame(player)
    interaction = FakeInteraction()
    monkeypatch.setattr(DrawHelper, "player_area", lambda self, stats: None)
    monkeypatch.setattr(DrawHelper, "show_player_ship_area", lambda self, image: None)

    asyncio.run(UpgradeButtons.startUpgrade(game, player, interaction, False, "dummy", "dum"))

    assert interaction.channel.sent[-1][1]["view"].children[0].custom_id == \
        "FCIDblue_upgradeShip_1_interceptor_dummy"
