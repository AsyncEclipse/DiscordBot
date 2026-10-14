import asyncio

from discord.ui import View

from Buttons.Build import BuildButtons
from helpers.DrawHelper import DrawHelper
from helpers.GamestateHelper import GamestateHelper
from helpers.PlayerHelper import PlayerHelper
from helpers.ShipHelper import PlayerShip


def make_player(name="Atlantians"):
    return {
        "name": name,
        "player_name": "Blue",
        "color": "blue",
        "interceptor_parts": ["ioc", "axc", "mus", "empty"],
        "cruiser_parts": ["elc", "empty"],
        "dread_parts": ["empty"],
        "starbase_parts": ["empty"],
        "orb_parts": ["empty"],
        "ancient_parts": ["socha"],
        "cost_interceptor": 3,
        "cost_cruiser": 5,
        "cost_dread": 8,
        "cost_starbase": 3,
        "cost_orbital": 4,
        "cost_monolith": 10,
        "base_interceptor_speed": 2,
        "base_interceptor_nrg": 0,
        "base_interceptor_comp": 0,
        "military_tech": ["stb"],
        "nano_tech": [],
        "ship_stock": [7, 4, 2, 4],
        "build_apt": 3,
        "reputation_track": [],
    }


class FakeGame:
    def __init__(self):
        self.gamestate = {"board": {"201": {"player_ships": []}}}

    getShipShortName = staticmethod(GamestateHelper.getShipShortName)


class FakeMessage:
    async def edit(self, **kwargs):
        self.edited = kwargs


class FakeInteraction:
    def __init__(self):
        self.message = FakeMessage()


def test_ancient_power_counts_installed_parts_once_and_recalculates_after_removal():
    player = make_player()
    player["ancient_parts"] = ["socha", "cod"]
    player["reputation_track"] = []
    game = DrawHelper({"board": {"201": {"owner": "blue", "vp": 0, "artifact": 0,
                                             "player_ships": ["blue-int"] * 4}}})

    assert PlayerHelper.installed_discovery_part_count(player) == 2
    assert game.get_public_points(player, False) == 2
    assert PlayerShip(player, "interceptor").cost == 4
    assert PlayerHelper.get_ship_cost(player, "cru") == 5

    player["interceptor_parts"].remove("mus")
    assert PlayerHelper.installed_discovery_part_count(player) == 1
    assert game.get_public_points(player, False) == 1
    assert PlayerShip(player, "interceptor").cost == 3


def test_discovery_part_rules_do_not_change_other_factions():
    player = make_player("Hydran Progress")
    game = DrawHelper({"board": {}})

    assert game.get_public_points(player, False) == 0
    assert PlayerShip(player, "interceptor").cost == 3
    assert PlayerHelper.get_ship_cost(player, "int") == 3


def test_build_labels_and_accumulation_use_adjusted_ship_cost():
    player = make_player()
    game = FakeGame()
    view = BuildButtons.buildBuildButtonsView(None, "", 0, "201", View(), player, game)
    interceptor = next(button for button in view.children if button.label.startswith("Interceptor"))
    assert interceptor.label == "Interceptor (4)"

    interaction = FakeInteraction()
    asyncio.run(BuildButtons.buildShip(
        game, player, interaction, "buildShip_none_0_201_Interceptor"))

    assert interaction.message.edited["content"] == "Total cost so far of 4"
