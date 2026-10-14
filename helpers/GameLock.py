"""One lock per game, so two button presses never read-modify-write the same save at once.

The bot is a single process on one event loop, so an asyncio.Lock is enough: it is held
across awaits, which is where button handling actually interleaves.

shortcut: in-process only, add a file lock if a second bot process ever shares gamestate_path.
"""
import asyncio

_locks: dict[str, asyncio.Lock] = {}


def game_lock(game_id: str) -> asyncio.Lock:
    return _locks.setdefault(game_id, asyncio.Lock())
