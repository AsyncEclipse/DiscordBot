"""The aeb ids that exist on disk, so no caller walks a hardcoded id range.

A game is in progress while its aebN_saveFile.json exists: endGame deletes that file
and leaves aebN.json behind, so reminders read save files and stats read every game.
"""
import os

import config


def list_game_ids() -> list[str]:
    """Sorted ids of every game ever started, finished ones included."""
    return _list_ids(".json")


def list_active_game_ids() -> list[str]:
    """Sorted ids of the games still in progress, i.e. those with a save file."""
    return _list_ids("_saveFile.json")


def _list_ids(suffix: str) -> list[str]:
    if not os.path.isdir(config.gamestate_path):
        return []
    numbers = []
    for filename in os.listdir(config.gamestate_path):
        if not filename.startswith("aeb") or not filename.endswith(suffix):
            continue
        number = filename[3:-len(suffix)]
        if number.isdigit():
            numbers.append(int(number))
    return [f"aeb{number}" for number in sorted(numbers)]
