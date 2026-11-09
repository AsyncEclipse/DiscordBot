"""Faction facts from data/factions.json.

A faction's numbers, colour, artwork key and abilities live in the file, not in
`if player["name"] == ...` branches. A game saved before a field was added keeps
its old copy of the row, so facts are read from the file here, keyed by name.
"""
import json

with open("data/factions.json", "r") as f:
    FACTIONS = json.load(f)

BY_NAME = {name: faction for faction in FACTIONS.values()
           for name in [faction["name"], *faction.get("name_aliases", [])]}


def of(player):
    """The faction row for a player: the player's own copy wins, the file fills in what a save predates."""
    if not player:
        return {}
    row = BY_NAME.get(player.get("name"))
    if row is None:
        return player
    return {**row, **player}


def has(player, ability):
    """Whether the player's faction declares the ability."""
    return ability in of(player).get("abilities", [])


def artwork_name(full_name):
    """The image and emoji key of a faction: artwork names differ from data keys (exl -> exile)."""
    return BY_NAME.get(full_name, {}).get("artwork", full_name)


def battle_rep_points(player):
    """Kurita: the +1/-1 battle markers sitting next to the reputation tiles still on the track."""
    bonuses = player.get("reputationBonuses", {})
    return sum(bonuses.get(str(x), 0) for x, tile in enumerate(player["reputation_track"]) if isinstance(tile, int))


def starting_sector_line(faction_key, sectors):
    """List all home-sector planets, including unpopulated advanced squares."""
    sector = sectors[FACTIONS[faction_key]["home_planet"]]
    planets = []
    for resource, icon, label in (("money", "🟡", "Money"),
                                  ("science", "🟣", "Science"),
                                  ("material", "🟤", "Materials"),
                                  ("neutral", "⚪", "Neutral")):
        for suffix, prefix in (("", ""), ("adv", "Advanced ")):
            count = len(sector[f"{resource}{suffix}_pop"])
            if count:
                planets.append(f"{count} {icon} {prefix}{label}")
    return "- Starting sector planets: " + ", ".join(planets)
