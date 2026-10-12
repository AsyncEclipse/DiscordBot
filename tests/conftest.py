"""Shared pytest fixtures.

Discord I/O is stubbed, so tests drive the engine by writing a gamestate JSON
into a temporary directory and constructing a GamestateHelper against it. The
`make_game` fixture is that factory; `no_random` pins dice and any other random
draw so a test can state the exact rolls it expects.
"""
import asyncio
import json

import pytest

import config
from helpers import CombatHelper
from helpers.CombatHelper import Combat
from helpers.GamestateHelper import GamestateHelper


@pytest.fixture
def make_game(tmp_path, monkeypatch):
    """Write a gamestate dict to a temp file and return a GamestateHelper for it."""
    monkeypatch.setattr(config, "gamestate_path", str(tmp_path))

    def make(gamestate, game_id="t"):
        gamestate.setdefault("game_id", game_id)
        with open(tmp_path / f"{game_id}.json", "w") as f:
            json.dump(gamestate, f)
        return GamestateHelper(None, game_id)

    return make


@pytest.fixture
def no_random(monkeypatch):
    """Replace random.randint with a queue of canned rolls."""
    def use(values):
        dice = iter(values)
        monkeypatch.setattr(CombatHelper.random, "randint", lambda a, b: next(dice))

    return use


@pytest.fixture
def quiet_combat(monkeypatch):
    """Keep combat resolution off Discord and off the filesystem."""
    async def noop(*args, **kwargs):
        return None

    monkeypatch.setattr(Combat, "startCombat", staticmethod(noop))
    monkeypatch.setattr(CombatHelper, "DrawHelper", lambda *a, **k: None)


@pytest.fixture
def run():
    """Await a coroutine and all background tasks it starts."""
    def run_coroutine(coro):
        async def await_tasks():
            result = await coro
            current_task = asyncio.current_task()
            while tasks := asyncio.all_tasks() - {current_task}:
                await asyncio.gather(*tasks)
            return result
        return asyncio.run(await_tasks())
    return run_coroutine
