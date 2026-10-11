import json

from helpers.GamestateHelper import GamestateHelper
from helpers.PlayerHelper import PlayerHelper


def _stats(faction: str, **overrides):
    with open("data/factions.json", "r") as f:
        stats = dict(json.load(f)[faction])
    stats.update({"player_name": "Tester", "color": "blue", "military_tech": [],
                  "grid_tech": [], "nano_tech": [], "ancient_parts": []})
    stats.update(overrides)
    return stats


def test_ships_with_parts_follows_the_faction():
    assert GamestateHelper.getShipsWithParts(_stats("hyd")) == \
        ["interceptor", "cruiser", "dread", "starbase"]
    assert "dread" not in GamestateHelper.getShipsWithParts(_stats("rho"))
    assert GamestateHelper.getShipsWithParts(_stats("exl"))[-1] == "orb"


def test_available_parts_unlock_from_techs_and_ancient_tiles():
    baseline = PlayerHelper("1", _stats("hyd")).getAvailableShipParts()
    assert {"ioc", "elc", "nud", "hul", "nus", "empty"} <= baseline
    assert "tad" not in baseline

    owned = PlayerHelper("1", _stats("hyd", grid_tech=["tad"], ancient_parts=["hyg"])).getAvailableShipParts()
    assert {"tad", "hyg"} <= owned
    assert baseline <= owned, "a tech must never cost you the parts you already had"



def test_old_exile_part_is_renamed_so_custom_ids_parse():
    stats = _stats("exl")
    stats["orb_parts"] = ["iot_exile", "empty"]
    PlayerHelper("1", stats).renameOldExileParts("orb")
    assert stats["orb_parts"] == ["iotexile", "empty"]
