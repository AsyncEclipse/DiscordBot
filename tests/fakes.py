"""Reusable test doubles and builders shared by the test suite.

Discord is never available in tests, so interaction, channel, guild and message
objects are stubbed here. Anything that is a plain helper rather than a pytest
fixture belongs in this module; fixtures live in conftest.py.
"""
import copy
import json

FACTIONS = json.load(open("data/factions.json"))


class FakeMessage:
    async def delete(self):
        pass


class FakeChannel:
    def __init__(self, name="aeb1-actions"):
        self.name = name
        self.sent = []

    async def send(self, content=None, **kwargs):
        self.sent.append((content, kwargs))
        return FakeMessage()


class FakeUser:
    name = "tester"
    mention = "<@tester>"
    id = 195677939050872832
    display_name = "tester"


class FakeGuild:
    emojis = []
    channels = []
    roles = []

    def get_member(self, _id):
        return None


class FakeInteraction:
    def __init__(self, channel=None):
        self.channel = channel or FakeChannel()
        self.user = FakeUser()
        self.guild = FakeGuild()
        self.message = FakeMessage()


def player_stats(faction, **overrides):
    """A faction's stats with the colour/identity fields the bot fills in at setup."""
    stats = copy.deepcopy(FACTIONS[faction])
    color = overrides.pop("color", "blue")
    stats.update({
        "player_name": color,
        "username": color,
        "color": color,
        "military_tech": [],
        "grid_tech": [],
        "nano_tech": [],
        "ancient_parts": [],
    })
    stats.update(overrides)
    return stats


def players(*colors):
    """A gamestate players dict with one Hydran Progress per colour."""
    return {str(i): player_stats("hyd", color=color) for i, color in enumerate(colors, 1)}


def board_tile(ships=(), owner=0, sector=101, **extra):
    """A board dict holding one sector, keyed the way the gamestate keys it."""
    tile = {"owner": owner, "sector": sector, "disctile": 0, "player_ships": list(ships)}
    tile.update(extra)
    return {str(sector): tile}


def offered_buttons(interaction):
    """Every button offered across the messages the fake channel received."""
    return [child for _content, kwargs in interaction.channel.sent
            for child in getattr(kwargs.get("view"), "children", [])]


def offered_labels(interaction):
    """Button labels offered across every message the fake channel received."""
    return [getattr(button, "label", None) for button in offered_buttons(interaction)]


def offered_ids(interaction):
    """Button custom_ids offered across every message the fake channel received."""
    return [getattr(button, "custom_id", None) for button in offered_buttons(interaction)]


def sent_text(interaction):
    return "\n".join(str(content) for content, _kwargs in interaction.channel.sent)
