"""Button presses in one game run one at a time; different games don't wait on each other."""
import asyncio

import discord

from listeners.ButtonListener import ButtonListener
from tests.fakes import FakeChannel, FakeInteraction


def press_through_on_interaction(listener, channel_name):
    inter = FakeInteraction(FakeChannel(channel_name), custom_id="FCIDblue_noop")
    inter.type = discord.InteractionType.component
    return listener.on_interaction(inter)


def test_presses_in_the_same_game_do_not_interleave(run, monkeypatch):
    events = []

    async def slow_resolve(inter):
        events.append("start")
        await asyncio.sleep(0.01)  # a real handler awaits Discord here, which is where presses interleave
        events.append("end")

    listener = ButtonListener(None)
    monkeypatch.setattr(listener, "resolveButton", slow_resolve)

    async def both():
        await asyncio.gather(press_through_on_interaction(listener, "aeb1-actions"),
                             press_through_on_interaction(listener, "aeb1-tabletalk"))

    run(both())

    assert events == ["start", "end", "start", "end"]


def test_presses_in_different_games_run_together(run, monkeypatch):
    events = []

    async def slow_resolve(inter):
        events.append("start")
        await asyncio.sleep(0.01)
        events.append("end")

    listener = ButtonListener(None)
    monkeypatch.setattr(listener, "resolveButton", slow_resolve)

    async def both():
        await asyncio.gather(press_through_on_interaction(listener, "aeb1-actions"),
                             press_through_on_interaction(listener, "zzz9-actions"))

    run(both())

    assert events == ["start", "start", "end", "end"]
