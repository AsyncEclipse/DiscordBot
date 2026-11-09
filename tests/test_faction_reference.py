import json

from helpers import FactionData


def test_starting_sector_lists_all_eight_planet_types():
    sector = {f"{resource}{suffix}_pop": [1, 0]
              for resource in ("money", "science", "material", "neutral")
              for suffix in ("", "adv")}
    line = FactionData.starting_sector_line("hyd", {"224": sector})
    assert line == (
        "- Starting sector planets: 2 🟡 Money, 2 🟡 Advanced Money, "
        "2 🟣 Science, 2 🟣 Advanced Science, "
        "2 🟤 Materials, 2 🟤 Advanced Materials, "
        "2 ⚪ Neutral, 2 ⚪ Advanced Neutral"
    )


def test_every_faction_has_a_single_starting_sector_line():
    with open("data/sectors.json") as sector_file:
        sectors = json.load(sector_file)
    for key in FactionData.FACTIONS:
        line = FactionData.starting_sector_line(key, sectors)
        assert line.startswith("- Starting sector planets: ")
        assert "\n" not in line
        assert "0 " not in line
    assert FactionData.starting_sector_line("hyd", sectors) == (
        "- Starting sector planets: 1 🟡 Money, "
        "1 🟣 Advanced Science, 1 🟤 Advanced Materials"
    )
    assert len({FactionData.starting_sector_line(key, sectors)
                for key in ("ter1", "ter2", "ter3", "ter4", "ter5", "ter6")}) == 1
