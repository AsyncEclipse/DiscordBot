import json

from helpers.GamestateHelper import GamestateHelper
from helpers.PlayerHelper import PlayerHelper
from helpers.ShipHelper import PlayerShip


def _player_stats(faction: str, **overrides):
    with open("data/factions.json", "r") as f:
        stats = dict(json.load(f)[faction])
    stats["player_name"] = "Tester"
    stats["color"] = "blue"
    stats["military_tech"] = []
    stats["grid_tech"] = []
    stats["nano_tech"] = []
    stats["ancient_parts"] = []
    stats.update(overrides)
    return stats


class TestShipsWithParts:
    def test_rho_faction_has_no_dreadnought_or_orbital(self):
        ships = GamestateHelper.getShipsWithParts(_player_stats("rho"))
        assert "dread" not in ships
        assert "orb" not in ships
        assert "cruiser" in ships

    def test_exiles_fly_an_orbital_not_a_starbase(self):
        ships = GamestateHelper.getShipsWithParts(_player_stats("exl"))
        assert "orb" in ships
        assert "starbase" not in ships

    def test_hydran_fields_the_standard_four(self):
        assert GamestateHelper.getShipsWithParts(_player_stats("hyd")) == \
            ["interceptor", "cruiser", "dread", "starbase"]


class TestAvailableShipParts:
    def test_baseline_parts_are_always_available(self):
        parts = PlayerHelper("1", _player_stats("hyd")).getAvailableShipParts()
        assert {"ioc", "elc", "nud", "hul", "nus", "empty"} <= parts

    def test_tech_owned_parts_unlock_the_matching_code(self):
        stats = _player_stats("hyd", grid_tech=["tad"])
        assert "tad" in PlayerHelper("1", stats).getAvailableShipParts()
        assert "fus" not in PlayerHelper("1", stats).getAvailableShipParts()

    def test_ancient_parts_unlock_their_code(self):
        stats = _player_stats("hyd", ancient_parts=["hyg"])
        assert "hyg" in PlayerHelper("1", stats).getAvailableShipParts()

    def test_base_parts_stay_available_so_a_swap_can_undo_a_tech_swap(self):
        stats = _player_stats("hyd", military_tech=["tad"])
        parts = PlayerHelper("1", stats).getAvailableShipParts()
        assert "tad" in parts
        assert "nud" in parts


class TestSlotSwapLegality:
    def test_swapping_a_drive_for_another_drive_stays_a_legal_ship(self):
        stats = _player_stats("hyd", grid_tech=["fud"])
        parts = stats["cruiser_parts"]
        parts[parts.index("nud")] = "fud"
        assert PlayerShip(stats, "cruiser").check_valid_ship()

    def test_swapping_in_an_unaffordable_part_is_rejected(self):
        stats = _player_stats("hyd", grid_tech=["tad"])
        parts = stats["cruiser_parts"]
        parts[parts.index("nus")] = "tad"
        assert not PlayerShip(stats, "cruiser").check_valid_ship()

    def test_range_is_illegal_on_a_starbase(self):
        stats = _player_stats("hyd", grid_tech=["tad"])
        parts = stats["starbase_parts"]
        parts[0] = "tad"
        assert not PlayerShip(stats, "starbase").check_valid_ship()


class TestListingSlots:
    def test_slot_numbers_are_one_based_and_ship_scoped(self):
        stats = _player_stats("hyd")
        with open("data/parts.json", "r") as f:
            part_stats = json.load(f)
        lines = [f"> {n}. {part_stats[p]['name']} ({p})"
                 for n, p in enumerate(stats["cruiser_parts"], start=1)]
        assert lines[0] == "> 1. " + f"{part_stats[stats['cruiser_parts'][0]]['name']} " \
                                 f"({stats['cruiser_parts'][0]})"
        assert len(lines) == len(stats["cruiser_parts"])

    def test_empty_parts_are_still_listed_as_slots(self):
        stats = _player_stats("hyd")
        assert "empty" in stats["cruiser_parts"]
