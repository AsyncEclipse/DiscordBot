from helpers.GameIds import GameIds


def test_lists_active_save_files_only(tmp_path):
    (tmp_path / "aeb1.json").write_text("{}")
    (tmp_path / "aeb1_saveFile.json").write_text("{}")
    (tmp_path / "aeb2000_saveFile.json").write_text("{}")
    (tmp_path / "test0.json").write_text("{}")
    (tmp_path / "aeb2_saveFile.json.bak").write_text("{}")
    (tmp_path / "not_a_game.json").write_text("{}")

    assert GameIds.list_active_game_ids(gamestate_path=str(tmp_path)) == ["aeb1", "aeb2000"]


def test_lists_all_game_json_files(tmp_path):
    (tmp_path / "aeb1.json").write_text("{}")
    (tmp_path / "aeb1_saveFile.json").write_text("{}")
    (tmp_path / "aeb12.json").write_text("{}")
    (tmp_path / "test0.json").write_text("{}")
    (tmp_path / "readme.txt").write_text("nope")

    assert GameIds.list_game_ids(gamestate_path=str(tmp_path)) == ["aeb1", "aeb12"]


def test_sorts_active_ids_numerically(tmp_path):
    (tmp_path / "aeb10_saveFile.json").write_text("{}")
    (tmp_path / "aeb2_saveFile.json").write_text("{}")
    (tmp_path / "aeb100_saveFile.json").write_text("{}")

    assert GameIds.list_active_game_ids(gamestate_path=str(tmp_path)) == [
        "aeb2",
        "aeb10",
        "aeb100",
    ]


def test_missing_directory_returns_empty(tmp_path):
    missing = str(tmp_path / "missing")
    assert GameIds.list_game_ids(gamestate_path=missing) == []
    assert GameIds.list_active_game_ids(gamestate_path=missing) == []
