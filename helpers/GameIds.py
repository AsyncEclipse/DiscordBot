import os
import re
import config


class GameIds:
    _SAVE_FILE_RE = re.compile(r"^aeb(\d+)_saveFile\.json$")
    _GAME_JSON_RE = re.compile(r"^aeb(\d+)\.json$")

    @staticmethod
    def list_game_ids(gamestate_path: str | None = None) -> list[str]:
        """Return sorted IDs for every aebN.json on disk, including finished games."""
        return GameIds._list_matching(GameIds._GAME_JSON_RE, gamestate_path)

    @staticmethod
    def list_active_game_ids(gamestate_path: str | None = None) -> list[str]:
        """Return sorted IDs for games that still have aebN_saveFile.json.

        endGame deletes that save file, so this is the in-progress set the reminder loop wants.
        """
        return GameIds._list_matching(GameIds._SAVE_FILE_RE, gamestate_path)

    @staticmethod
    def _list_matching(pattern: re.Pattern, gamestate_path: str | None) -> list[str]:
        if gamestate_path is None:
            gamestate_path = config.gamestate_path
        if not os.path.isdir(gamestate_path):
            return []
        found = []
        for filename in os.listdir(gamestate_path):
            match = pattern.match(filename)
            if match:
                number = int(match.group(1))
                found.append((number, f"aeb{number}"))
        found.sort(key=lambda item: item[0])
        return [game_id for _, game_id in found]
