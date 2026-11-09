import json

from Buttons.Research import ResearchButtons
from helpers.PlayerHelper import PlayerHelper
from helpers.ShipHelper import PlayerShip
from tests.fakes import FACTIONS, player_stats, reload


def test_wra_faction_stats_match_printed_card_and_board():
    wra = FACTIONS["wra"]
    assert wra["name"] == "The Wraith"
    # 4 materials / 4 science / 2 money / 3 colony ships, printed on the board storage strip.
    assert (wra["materials"], wra["science"], wra["money"]) == (4, 4, 2)
    assert (wra["colony_ships"], wra["base_colony_ships"]) == (3, 3)
    assert wra["home_planet"] == "254"
    assert wra["trade_value"] == 3
    assert wra["influence_discs"] == 12
    # The board prints INF 1 and a bubble 2: one activation flips the standard two colony ships.
    assert wra.get("influence_colony_ships", 2) == 2
    assert [wra[key] for key in ("explore_apt", "research_apt", "upgrade_apt",
                                 "build_apt", "move_apt", "influence_apt")] == [1, 1, 2, 2, 2, 1]
    assert wra["military_tech"] == ["phm"]
    assert wra["grid_tech"] == wra["nano_tech"] == wra["ancient_parts"] == []
    assert wra["reputation_track"] == ["mixed", "rep", "rep", "rep"]
    assert wra["reputation_only_slots"] == [1, 2, 3]
    # One money and one plain science cube start on the home; the Advanced science square is empty.
    assert (wra["money_pop_cubes"], wra["material_pop_cubes"], wra["science_pop_cubes"]) == (11, 12, 11)
    assert wra["population_track"] == [28, 24, 21, 18, 15, 12, 10, 8, 6, 4, 3, 2, 0]
    assert wra["tech_track"] == [-8, -6, -4, -3, -2, -1, 0, 0]
    assert [wra[key] for key in ("cost_interceptor", "cost_cruiser", "cost_dread", "cost_starbase",
                                 "cost_orbital", "cost_monolith")] == [4, 6, 9, 3, 4, 10]
    assert wra["ship_stock"] == [7, 4, 2, 4]
    assert wra["wraithSouls"] == 0


def test_the_mixed_reputation_slot_allows_one_relation_and_the_other_three_do_not():
    wraith = player_stats("wra")
    assert [PlayerHelper.is_reputation_only_slot(wraith, i) for i in range(4)] == [False, True, True, True]
    assert PlayerHelper.has_reputation_slot_for_relation(wraith) is True
    wraith["reputation_track"][0] = "minor-trade-blue"
    assert PlayerHelper.has_reputation_slot_for_relation(wraith) is False


def test_phase_module_is_display_only_and_never_enters_the_tech_deck(start_game):
    game, _channel = start_game(factions=["wra", "eri"])
    with open("data/techs.json", "r") as f:
        phm = json.load(f)["phm"]
    assert phm["track"] == "military"
    assert phm["num"] == 0
    state = reload(game).gamestate
    assert "phm" not in state["tech_deck"]
    assert "phm" not in state["available_techs"]


def test_starting_phase_module_counts_for_the_military_research_discount(start_game):
    game, _channel = start_game(factions=["wra", "eri"])
    with open("data/techs.json", "r") as f:
        starbase = json.load(f)["stb"]
    wraith = reload(game).get_player(1)
    plain = {**wraith, "military_tech": []}

    assert "phm" in wraith["military_tech"]
    # The first military tech is one cheaper because the printed Phase Module is on the track.
    assert ResearchButtons.calculate_cost(starbase, "military", wraith) == 3
    assert ResearchButtons.calculate_cost(starbase, "military", plain) == 4


def test_wraith_phase_modules_replace_starting_computers():
    player = player_stats("wra")
    for ship in ("interceptor", "cruiser", "dread", "starbase"):
        assert PlayerShip(player, ship).computer == 0
        assert "elc" not in player[f"{ship}_parts"]
        assert len(PlayerHelper.get_phase_module_slots(player, ship)) == 1
        slot = PlayerHelper.get_phase_module_slots(player, ship)[0]
        assert player[f"{ship}_parts"][slot] == "empty"
