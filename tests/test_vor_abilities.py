"""Vorlons: Tech Masters, Organic Tech, Few in Number, Regenerative Hull and the Centre bonus."""
import pytest

from Buttons.Research import ResearchButtons
from helpers.CombatHelper import Combat
from helpers.DrawHelper import DrawHelper
from helpers.PlayerHelper import PlayerHelper
from tests.fakes import FakeChannel, FakeInteraction, buttons, player_stats, reload

TECH = {"name": "Gauss Shield", "track": "grid", "base_cost": 5, "min_cost": 0}


class FakeGame:
    """The research code paths only need these."""

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


def test_tech_masters_charges_2_3_4_more_for_the_wrong_tray():
    player = player_stats("vor")
    for uses, cost in ((0, 6), (1, 7), (2, 8)):
        player["techMasterUses"] = uses
        assert ResearchButtons.calculate_cost(TECH, "military", player) == cost
    assert ResearchButtons.calculate_cost(TECH, "grid", player) == 4
    assert ResearchButtons.calculate_cost(TECH, "military", player_stats("hyd")) == 5


@pytest.mark.parametrize("uses, extra", [(0, 2), (1, 3), (2, 4)])
def test_tech_masters_adds_the_full_surcharge_after_discounts_and_minimum(uses, extra):
    player = player_stats("vor")
    player["techMasterUses"] = uses
    tech = {"track": "grid", "base_cost": 6, "min_cost": 4}
    assert ResearchButtons.calculate_cost(tech, "military", player) == 5 + extra
    # the discount follows the tray the tile goes into, not the tech's own tray
    player["grid_tech"] = ["gas"] * 7
    assert ResearchButtons.calculate_cost(tech, "military", player) == 5 + extra
    player["military_tech"] = ["neb", "stb", "plc", "phs", "adm", "tas"]
    assert ResearchButtons.calculate_cost(tech, "military", player) == 4 + extra


def test_tech_masters_offers_every_tray_and_records_a_wrong_one(run):
    player = player_stats("vor", science=20)
    interaction = FakeInteraction()
    game = FakeGame(player)

    run(ResearchButtons.getTech(game, player, PlayerHelper("1", player), interaction,
                                "getTech_gas_grid"))

    assert set(buttons(interaction.channel)) == {
        "FCIDblue_getTech_gas_military_tm",
        "FCIDblue_getTech_gas_grid_tm",
        "FCIDblue_getTech_gas_nano_tm",
    }
    assert buttons(interaction.channel)["FCIDblue_getTech_gas_military_tm"] == "Military (2 + 2 = 4)"
    assert player["grid_tech"] == []

    run(ResearchButtons.getTech(game, player, PlayerHelper("1", player), interaction,
                                "getTech_gas_military_tm"))

    assert player["military_tech"] == ["gas"]
    assert player["techMasterUses"] == 1
    assert player["science"] == 20 - 4


@pytest.mark.parametrize("grid_count", [0, 7])
def test_tech_masters_menu_uses_the_cheapest_open_tray(make_game, run, grid_count):
    player = player_stats("vor", science=15, money=0, materials=0)
    player["military_tech"] = ["neb", "stb", "plc", "phs", "adm", "tas"]
    player["grid_tech"] = ["gas", "fus", "imh", "poc", "ade", "tad", "anc"][:grid_count]
    game = make_game({"players": {"1": player}, "available_techs": ["qug"]})
    interaction = FakeInteraction()

    run(ResearchButtons.startResearch(game, player, PlayerHelper("1", player), interaction, False))

    # the six-tech military tray is cheapest: 8 (minimum) + 2 surcharge
    assert buttons(interaction.channel)["FCIDblue_getTech_qug_grid"] == "Quantum Grid (10)"
    run(ResearchButtons.getTech(game, player, PlayerHelper("1", player), interaction,
                                "getTech_qug_grid"))
    assert buttons(interaction.channel)["FCIDblue_getTech_qug_military_tm"] == "Military (8 + 2 = 10)"
    grid_offer = buttons(interaction.channel).get("FCIDblue_getTech_qug_grid_tm")
    assert grid_offer == (None if grid_count else "Grid (15)")


def test_organic_tech_gives_a_free_upgrade_after_research(start_game, press):
    game, channel = start_game(factions=["vor", "eri"])
    game.gamestate["available_techs"] = ["gas"]
    game.get_player(1)["science"] = 40
    game.update()

    press(channel, 1, "FCIDblue_startResearch")
    press(channel, 1, "FCIDblue_getTech_gas_grid")
    assert buttons(channel)["FCIDblue_getTech_gas_grid_tm"] == "Grid (2)"

    press(channel, 1, "FCIDblue_getTech_gas_grid_tm")
    after = reload(game).get_player(1)
    assert after["grid_tech"] == ["gas"]
    assert after["science"] == 38
    offer = next(cid for cid in buttons(channel)
                 if cid.startswith("FCIDblue_ancientInstinctUpgrade_"))
    assert offer == "FCIDblue_ancientInstinctUpgrade_gas_offer"

    discs = after["influence_discs"]
    press(channel, 1, offer)
    inter = press(channel, 1, "FCIDblue_upgradeShip_1_interceptor_gas")
    old_part = next(cid for cid in inter.message.edited["view"].children
                    if cid.custom_id.startswith("FCIDblue_selectOldPart_")
                    and cid.custom_id.endswith("_gas_0"))
    press(channel, 1, old_part.custom_id, inter.message)

    after = reload(game).get_player(1)
    assert after["interceptor_parts"][0] == "gas"
    assert after["influence_discs"] == discs


def test_organic_tech_offer_expires_when_the_research_action_ends(start_game, press):
    game, channel = start_game(factions=["vor", "eri"])
    game.gamestate["available_techs"] = ["gas"]
    game.get_player(1)["science"] = 40
    game.update()

    press(channel, 1, "FCIDblue_startResearch")
    press(channel, 1, "FCIDblue_getTech_gas_grid")
    press(channel, 1, "FCIDblue_getTech_gas_grid_tm")
    offer = next(cid for cid in buttons(channel)
                 if cid.startswith("FCIDblue_ancientInstinctUpgrade_"))

    press(channel, 1, "FCIDblue_finishAction")
    press(channel, 1, offer)

    assert not any(cid.startswith("FCIDblue_upgradeShip_") for cid in buttons(channel))


def _damaged_vorlons_cruiser(make_game, ships, positions):
    return make_game({
        "advanced_ai": 0, "wa_ai": 0, "player_count": 2,
        "players": {"1": player_stats("vor", color="blue"),
                    "2": player_stats("hyd", color="red")},
        "board": {"101": {"owner": 0, "sector": 101, "disctile": 0,
                          "player_ships": ships,
                          "attacker": positions[0], "defender": positions[1],
                          "damage_tracker": {"blue-cru": 1}}},
    })


def test_regenerative_hull_repairs_a_damaged_ship(make_game, run):
    game = _damaged_vorlons_cruiser(make_game, ["blue-cru", "red-cru"], ("red", "blue"))
    run(Combat.checkForMorphShield(game, "101", FakeChannel(),
                                   ["blue-cru", "red-cru"], ["blue", "red"]))
    assert reload(game).gamestate["board"]["101"]["damage_tracker"]["blue-cru"] == 0


def test_regenerative_hull_repairs_against_guardians(make_game, run):
    game = _damaged_vorlons_cruiser(make_game, ["blue-cru", "ai-grd"], ("ai", "blue"))
    run(Combat.checkForMorphShield(game, "101", FakeChannel(),
                                   ["blue-cru", "ai-grd"], ["blue", "ai"]))
    assert reload(game).gamestate["board"]["101"]["damage_tracker"]["blue-cru"] == 0


def test_regenerative_hull_does_not_repair_against_ancients(make_game, run):
    game = _damaged_vorlons_cruiser(make_game, ["blue-cru", "ai-anc"], ("ai", "blue"))
    run(Combat.checkForMorphShield(game, "101", FakeChannel(),
                                   ["blue-cru", "ai-anc"], ["blue", "ai"]))
    assert reload(game).gamestate["board"]["101"]["damage_tracker"]["blue-cru"] == 1


def test_regenerative_hull_repairs_the_last_round_before_the_next_pairing(make_game, run):
    """Game aeb45 tile 206: the Vorlon cruiser (3 damage) killed the Turtugan cruiser
    sitting next to an Ancient. The pairing restarted against the Ancient, where heal
    is off, so the repair for the round that just ended was never applied."""
    vor = player_stats("vor", color="purple")
    vor["cruiser_parts"] = ["elc", "ioc", "nus", "reh", "hul", "hul", "nud"]
    game = make_game({
        "advanced_ai": 0, "wa_ai": 0, "player_count": 2,
        "players": {"1": vor, "2": player_stats("tur", color="teal")},
        "board": {"206": {"owner": 0, "sector": 211, "disctile": 0,
                          "player_ships": ["ai-anc", "teal-cru", "purple-cru"],
                          "attacker": ["purple"], "defender": ["teal"],
                          "combatants": ["teal", "purple"], "engagementRound": 2,
                          "damage_tracker": {"purple-cru": 3}}},
    })

    run(Combat.assignHitTo(game, "assignHitTo_206_purple_teal-cru_6_6",
                           FakeInteraction(FakeChannel()), False))

    tile = reload(game).gamestate["board"]["206"]
    assert tile["defender"] == ["ai"]
    assert tile["damage_tracker"]["purple-cru"] == 2


def test_regenerative_hull_does_not_repair_a_ship_that_lost_the_part(make_game, run):
    game = _damaged_vorlons_cruiser(make_game, ["blue-cru", "red-cru"], ("red", "blue"))
    state = reload(game)
    state.get_player(1)["cruiser_parts"] = ["ioc", "nus", "nud", "hul", "hul", "elc"]
    state.update()
    run(Combat.checkForMorphShield(state, "101", FakeChannel(),
                                   ["blue-cru", "red-cru"], ["blue", "red"]))
    assert reload(state).gamestate["board"]["101"]["damage_tracker"]["blue-cru"] == 1


def test_centre_gives_vorlons_two_points_and_others_none(make_game):
    def points(faction, owner, alliances=None):
        player = player_stats(faction, color="blue")
        owner_player = player_stats("hyd", color=owner)
        if alliances:
            player["alliances"] = {alliances: False}
            owner_player["alliances"] = {alliances: False}
        game = make_game({
            "players": {"1": player, "2": owner_player},
            "board": {"000": {"sector": "001", "owner": owner, "vp": 0, "artifact": 0}},
        })
        return DrawHelper(game.gamestate).get_public_points(game.get_player(1), True)

    assert points("vor", "blue") == 2
    assert points("vor", "red") == 0
    assert points("hyd", "blue") == 0
    assert points("vor", "red", alliances="al") == 4  # the Centre plus the faceup Alliance Tile


def test_regenerative_hull_skips_heal_when_last_ancient_dies(make_game, run):
    game = _damaged_vorlons_cruiser(
        make_game, ["ai-anc", "red-cru", "blue-cru"], ("blue", "ai"))

    run(Combat.assignHitTo(game, "assignHitTo_101_blue_ai-anc_6_6", FakeInteraction(), False))

    tile = reload(game).gamestate["board"]["101"]
    assert tile["defender"] != "ai"
    assert "ai-anc" not in tile["player_ships"]
    assert tile["damage_tracker"]["blue-cru"] == 1


@pytest.mark.parametrize("second_target, remaining", [(1, (0, 0)), (0, (1, 0))])
def test_regenerative_hull_repairs_each_damaged_cruiser_once(make_game, run, second_target, remaining):
    ships = ["blue-cru", "blue-cru", "red-cru"]
    game = _damaged_vorlons_cruiser(make_game, ships, ("red", "blue"))
    game.get_player(1)["cruiser_parts"] = ["reh", "hul"]
    game.update()
    interaction = FakeInteraction()
    run(Combat.offerHitPrompt(game, interaction, "101", "red", ["blue-cru"], 6, 1))
    targets = [cid for cid in buttons(interaction.channel) if "_assignHitTo_" in cid]
    assert len(targets) == 2
    run(Combat.assignHitTo(game, targets[second_target].split("_", 1)[1],
                           interaction, False, deferEnd=True))

    game = reload(game)
    run(Combat.checkForMorphShield(game, "101", interaction.channel, ships, ["blue", "red"]))

    assert tuple(reload(game).ship_damage("101", f"blue-cru:{slot}") for slot in range(2)) == remaining


def test_destroying_a_cruiser_preserves_other_cruisers_damage_and_target(make_game, run):
    ships = ["blue-cru", "blue-cru", "red-cru"]
    game = _damaged_vorlons_cruiser(make_game, ships, ("red", "blue"))
    game.add_damage("blue-cru:1", "101", 1)

    interaction = FakeInteraction()
    run(Combat.assignHitTo(game, "assignHitTo_101_red_blue-cru:0_6_6",
                           interaction, False, deferEnd=True))
    game = reload(game)
    assert game.gamestate["board"]["101"]["player_ships"].count("blue-cru") == 1
    assert game.damage_targets("101", "blue-cru") == ["blue-cru:1"]

    run(Combat.assignHitTo(game, "assignHitTo_101_red_blue-cru:0_6_6",
                           interaction, False, deferEnd=True))
    assert game.ship_damage("101", "blue-cru:1") == 1


def test_moving_a_damaged_ship_keeps_damage_separate_at_the_destination(make_game):
    game = _damaged_vorlons_cruiser(make_game, ["blue-cru", "red-cru"], ("red", "blue"))
    game.gamestate["board"]["102"] = {"owner": 0, "player_ships": ["blue-cru"]}
    game.add_damage("blue-cru", "102", 2)

    moved = game.move_unit("blue-cru", "101", "102")

    game = reload(game)
    assert game.ship_damage("102", moved) == 1
    assert game.ship_damage("102", "blue-cru:0") == 2
    assert "blue-cru" not in game.gamestate["board"]["101"]["damage_tracker"]
