"""Shared pytest fixtures.

Discord I/O is stubbed (see fakes.py); the engine and save files run for real in
a temp directory. Pick the setup that fits the test:

- `make_game`: hand-write the gamestate dict. For one rule in isolation.
- `start_game` + `press`: a real set-up game, driven by clicking buttons through
  ButtonListener. For flows that span handlers or rounds.
- `games_dir`: only the temp save folder, for tests that create games themselves.

`no_random` pins dice so a test can state the exact rolls it expects.
"""
import asyncio
import json
import random

import pytest

import config


@pytest.fixture
def games_dir(tmp_path, monkeypatch):
    """Point the bot's save folder at a temp dir and keep game creation off config.json."""
    monkeypatch.setattr(config, "gamestate_path", str(tmp_path))
    monkeypatch.setattr(config, "game_number", 1)
    monkeypatch.setattr("setup.GameInit.update_game_number", lambda: None)
    return tmp_path


@pytest.fixture
def make_game(games_dir):
    """Write a gamestate dict to a temp file and return a GamestateHelper for it."""
    from helpers.GamestateHelper import GamestateHelper

    def _make(gamestate, game_id="t"):
        gamestate.setdefault("game_id", game_id)
        with open(games_dir / f"{game_id}.json", "w") as f:
            json.dump(gamestate, f)
        return GamestateHelper(None, game_id)

    return _make


@pytest.fixture
def no_random(monkeypatch):
    """Replace random.randint with a queue of canned rolls."""
    from helpers import CombatHelper

    def _use(values):
        dice = iter(values)
        monkeypatch.setattr(CombatHelper.random, "randint", lambda a, b: next(dice))

    return _use


@pytest.fixture
def quiet_combat(monkeypatch):
    """Keep combat resolution off Discord and off the filesystem."""
    from helpers import CombatHelper
    from helpers.CombatHelper import Combat

    async def _noop(*args, **kwargs):
        return None

    monkeypatch.setattr(Combat, "startCombat", staticmethod(_noop))
    monkeypatch.setattr(CombatHelper, "DrawHelper", lambda *a, **k: None)


@pytest.fixture
def run():
    """Await a coroutine and flush its create_task side effects."""
    from tests.fakes import drain

    return lambda coro: asyncio.run(drain(coro))


@pytest.fixture
def press(run):
    """Click a button through ButtonListener.resolveButton, as the given user."""
    from listeners.ButtonListener import ButtonListener
    from tests.fakes import FakeInteraction

    def _press(channel, user_id, custom_id, message=None):
        game_id = channel.name.split("-")[0]  # the guild role that pings players is named after the game
        inter = FakeInteraction(channel, custom_id=custom_id, user_id=user_id, role_names=[game_id],
                                message=message or channel.message_with(custom_id))
        run(ButtonListener(None).resolveButton(inter))
        return inter

    return _press


@pytest.fixture
def start_game(games_dir, run):
    """Factory: a real set-up game (2-6 players, ids 1..n) with player 1 on turn.

    Returns (game, channel); press buttons in the channel with `press`.
    """
    from helpers.GamestateHelper import GamestateHelper
    from setup.GameInit import GameInit
    from tests.fakes import FakeChannel, FakeInteraction

    def _start(player_count=2, factions=None):
        random.seed(0)  # GameInit shuffles decks and tiles; keep runs reproducible
        factions = factions or ["hyd", "eri", "ori", "dra", "mec", "pla"]
        colors = ["blue", "red", "green", "yellow", "purple", "white"]
        homes = ["201", "203", "205", "207", "209", "211"]  # turn order reads these positions
        players = [[i + 1, f"<@{i + 1}>"] for i in range(player_count)]
        GameInit("T", players, "def", True, True, False, False).create_game()
        game = GamestateHelper(None, "aeb1")
        game.setup_techs_and_outer_rim(player_count, False, False)
        game.add_tile("000", 0, "001")
        for (pid, _), faction, color, pos in zip(players, factions, colors, homes):
            game.player_setup(pid, faction, color, FakeInteraction())
            game.add_tile(pos, 0, game.get_player(pid)["home_planet"], color)
        game.setup_finished()
        run(game.updateNamesAndOutRimTiles(FakeInteraction()))
        game.initilizeKey("activePlayerColor")
        game.addToKey("activePlayerColor", "blue")
        return game, FakeChannel("aeb1-actions")

    return _start
