"""Game ids are read from the save folder instead of the old hardcoded id range."""
import config

from helpers.GameIds import list_active_game_ids, list_game_ids


def test_active_games_are_the_ones_with_save_files(games_dir):
    (games_dir / "aeb1.json").write_text("{}")
    (games_dir / "aeb1_saveFile.json").write_text("{}")
    (games_dir / "aeb2000_saveFile.json").write_text("{}")  # past the old aeb0..aeb1499 scan
    (games_dir / "aeb2_saveFile.json.bak").write_text("{}")
    (games_dir / "not_a_game.json").write_text("{}")

    assert list_active_game_ids() == ["aeb1", "aeb2000"]


def test_all_games_include_finished_ones(games_dir):
    (games_dir / "aeb1.json").write_text("{}")
    (games_dir / "aeb1_saveFile.json").write_text("{}")
    (games_dir / "aeb12.json").write_text("{}")
    (games_dir / "readme.txt").write_text("nope")

    assert list_game_ids() == ["aeb1", "aeb12"]


def test_ids_sort_numerically(games_dir):
    for number in (10, 2, 100):
        (games_dir / f"aeb{number}_saveFile.json").write_text("{}")

    assert list_active_game_ids() == ["aeb2", "aeb10", "aeb100"]


def test_missing_save_folder_lists_nothing(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "gamestate_path", str(tmp_path / "missing"))

    assert list_game_ids() == []
    assert list_active_game_ids() == []
