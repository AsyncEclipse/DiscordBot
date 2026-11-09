"""Reusable test doubles and builders shared by the test suite.

Discord is never available in tests, so interaction, channel, guild and message
objects are stubbed here. Anything that is a plain helper rather than a pytest
fixture belongs in this module; fixtures live in conftest.py.
"""
import copy
import itertools
import json
from datetime import datetime, timezone
from types import SimpleNamespace

import discord

from helpers.GamestateHelper import GamestateHelper
from helpers.PlayerHelper import PlayerHelper

FACTIONS = json.load(open("data/factions.json"))
POS = "101"  # the sector board_tile() builds by default


class FakeImage:
    """Let exploration build real rotation choices without composing or encoding pixels."""

    def paste(self, *args, **kwargs):
        return None

    def crop(self, *args, **kwargs):
        return self

    def save(self, *args, **kwargs):
        return None


class FakeMessage:
    _ids = itertools.count(1)

    def __init__(self, channel=None):
        self.id = next(self._ids)
        self.flags = SimpleNamespace(ephemeral=False)
        self.channel = channel
        self.components = []

    async def delete(self):
        if self.channel is not None:
            self.channel.deleted.add(self.id)

    async def edit(self, **kwargs):
        self.edited = kwargs

    async def create_thread(self, name):
        thread = FakeChannel(name)
        self.channel.threads.append(thread)
        return thread


class FakeClient:
    """Stands in for discord.Client. fetch_channel finds the fake channels by id."""

    channels = {}

    async def fetch_channel(self, channel_id):
        if channel_id not in FakeClient.channels:
            raise discord.NotFound(SimpleNamespace(status=404, reason="Not Found"), "Unknown Channel")
        return FakeClient.channels[channel_id]


class FakeChannel:
    _ids = itertools.count(1000)

    def __init__(self, name="aeb1-actions"):
        self.id = next(FakeChannel._ids)
        self.name = name
        self.threads = []
        self.sent = []
        self.messages = []  # parallel to sent: the message each send created
        self.deleted = set()
        FakeClient.channels[self.id] = self

    async def send(self, content=None, **kwargs):
        self.sent.append((content, kwargs))
        self.messages.append(FakeMessage(self))
        return self.messages[-1]

    async def fetch_message(self, message_id):
        if message_id in self.deleted:
            raise discord.NotFound(SimpleNamespace(status=404, reason="Not Found"), "Unknown Message")
        # Unknown ids still yield a stand-in message, as Discord would return the real one.
        return next((message for message in self.messages if message.id == message_id), FakeMessage(self))

    async def edit(self, **kwargs):
        self.edited = kwargs

    def message_with(self, custom_id):
        """The latest message carrying this button, as Discord hands it to the press."""
        for (_content, kwargs), message in zip(reversed(self.sent), reversed(self.messages)):
            if any(getattr(c, "custom_id", None) == custom_id for c in getattr(kwargs.get("view"), "children", [])):
                return message
        return None


class FakeUser:
    name = "tester"
    mention = "<@tester>"
    id = 195677939050872832
    display_name = "tester"


class FakeRole:
    def __init__(self, name):
        self.name = name
        self.mention = f"<@&{name}>"


class FakeGuild:
    emojis = []
    channels = []

    def __init__(self, role_names=()):
        self.roles = [FakeRole(n) for n in role_names]

    def get_member(self, _id):
        return None


class FakeResponder:
    """Stands in for interaction.response / interaction.followup; records sends."""

    def __init__(self):
        self.sent = []

    async def defer(self, **kwargs):
        pass

    async def send(self, content=None, **kwargs):
        self.sent.append((content, kwargs))

    send_message = send


class FakeInteraction:
    def __init__(self, channel=None, custom_id=None, user_id=None, role_names=(), message=None):
        self.channel = channel or FakeChannel()
        self.user = FakeUser()
        if user_id is not None:
            self.user.id = user_id
        self.guild = FakeGuild(role_names)
        self.message = message or FakeMessage()
        self.data = {"custom_id": custom_id}
        self.created_at = datetime.now(timezone.utc)
        self.response = FakeResponder()
        self.followup = FakeResponder()
        self.client = FakeClient()


class FakeGame:
    """Stand-in for the draft/setup code paths: only the gamestate keys they read."""

    def __init__(self, community_factions, community_mode):
        self.gamestate = {
            "community_factions": community_factions,
            "communityMode": community_mode,
            "bannedFactions": [],
            "draftedFactions": [],
        }


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


def board_tile(ships=(), owner=0, sector=int(POS), **extra):
    """A board dict holding one sector, keyed the way the gamestate keys it."""
    tile = {"owner": owner, "sector": sector, "disctile": 0, "player_ships": list(ships)}
    tile.update(extra)
    return {str(sector): tile}


def player_helper(game, color):
    """A PlayerHelper for the player with this colour."""
    return PlayerHelper(game.get_player_from_color(color), game.getPlayerObjectFromColor(color))


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


def buttons(channel):
    """custom_id -> label for every button in the most recent message that has any."""
    for _content, kwargs in reversed(channel.sent):
        children = getattr(kwargs.get("view"), "children", [])
        if children:
            return {c.custom_id: c.label for c in children}
    return {}


def reload(game):
    """Re-read a game from disk: what the next button press will see."""
    return type(game)(None, game.game_id)
