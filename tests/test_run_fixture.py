"""The run fixture waits for background tasks and surfaces their failures."""
import asyncio

import pytest


def test_run_waits_for_delayed_background_side_effect(run):
    effects = []

    async def delayed_effect():
        await asyncio.sleep(0.01)
        effects.append("done")

    async def operation():
        asyncio.create_task(delayed_effect())
        return "result"

    assert run(operation()) == "result"
    assert effects == ["done"]


def test_run_surfaces_background_task_exceptions(run):
    async def fail():
        await asyncio.sleep(0)
        raise RuntimeError("background failure")

    async def operation():
        asyncio.create_task(fail())

    with pytest.raises(RuntimeError, match="background failure"):
        run(operation())
