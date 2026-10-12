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


@pytest.fixture
def make_game(tmp_path, monkeypatch):
    """Write a gamestate dict to a temp file and return a GamestateHelper for it."""
    from helpers.GamestateHelper import GamestateHelper

    monkeypatch.setattr(config, "gamestate_path", str(tmp_path))

    def _make(gamestate, game_id="t"):
        gamestate.setdefault("game_id", game_id)
        with open(tmp_path / f"{game_id}.json", "w") as f:
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
    def _run(coro):
        async def _drain():
            result = await coro
            for _ in range(10):
                await asyncio.sleep(0)
            return result
        return asyncio.run(_drain())
    return _run
