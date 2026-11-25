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


TECH_TRACK = [-8, -6, -4, -3, -2, -1, 0, 0]
TECH_TRACK_VP = [0, 0, 0, 0, 1, 2, 3, 5]
CALL_TO_ARMS_MATERIALS = {"int": 1, "cru": 2, "drd": 3}
TECH_MASTERS_EXTRA = {"first": 2, "step": 1}


def tech_track(player):
    """The faction's printed research discounts, indexed from the last slot."""
    return of(player).get("tech_track", TECH_TRACK)


def tech_track_max(player):
    """How many Tech Tiles the faction's track holds (seven unless the board prints fewer)."""
    return of(player).get("tech_track_max", 7)


def tech_track_vp(player):
    """End-game VP by number of Tech Tiles on one track."""
    return of(player).get("tech_track_vp", TECH_TRACK_VP)


def tech_track_display(player):
    """The printed discount cells, first printed cell first."""
    track = tech_track(player)
    return [track[tech_track_max(player) - 1 - index]
            for index in range(tech_track_max(player))]


def call_to_arms_materials(player):
    """The printed materials gained per ship type destroyed while the sector is not yours."""
    return of(player).get("call_to_arms_materials", CALL_TO_ARMS_MATERIALS)


def tech_masters_extra(player):
    """Tech Masters' extra science: the first wrong-tray cost and the step added per later use."""
    return of(player).get("tech_masters_extra", TECH_MASTERS_EXTRA)


def action_apt(player, action, default=None):
    """The activations this action has, including a paid Midas Touch activation.

    A default lets an old save that predates the field behave as it did before.
    """
    apt = player[f"{action}_apt"] if default is None else player.get(f"{action}_apt", default)
    return apt + (1 if player.get("midasBoost") == action else 0)


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
