import json
from pathlib import Path

# config.py reads config.json on import. That file is gitignored (it holds the bot token),
# so clones and CI start without it. Create a dummy only when none exists.
_ROOT = Path(__file__).resolve().parents[1]
_CONFIG = _ROOT / "config.json"
if not _CONFIG.exists():
    _CONFIG.write_text(
        json.dumps(
            {
                "token": "test-token",
                "game_number": 46,
                "gamestate_path": str(_ROOT / "tests" / "tmp_games"),
            }
        )
    )
