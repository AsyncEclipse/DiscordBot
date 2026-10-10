"""Headless dev harness: build a game, run pure setup, render PNGs. No Discord.

    python local_run.py        # set "dev_seed" in config.json for reproducible output

Skips the Discord layer (commands/buttons need a fake-interaction shim, not
built yet). Exercises the engine and renderers only.
"""
import os
import shutil
from types import SimpleNamespace

import config

OUT_DIR = "local_debug"


def build_game(player_count=4):
    from setup.GameInit import GameInit
    players = [[1000 + i, f"Player{i}"] for i in range(1, player_count + 1)]
    GameInit("DevGame", players, "def", True, True, False, False).create_game()
    return players


def save_render(discord_file, path):
    with open(path, "wb") as f:
        f.write(discord_file.fp.read())
    size = os.path.getsize(path)
    assert size > 0, f"empty render: {path}"
    return size


def main():
    gs_dir = os.path.join(OUT_DIR, "gamestates")
    if os.path.exists(OUT_DIR):
        shutil.rmtree(OUT_DIR)
    os.makedirs(gs_dir, exist_ok=True)
    config.gamestate_path = gs_dir
    config.game_number = 900

    config_backup = open("config.json", "rb").read()
    try:
        players = build_game()
        game_id = f"aeb{config.game_number}"

        from helpers.GamestateHelper import GamestateHelper
        from helpers.DrawHelper import DrawHelper

        game = GamestateHelper(None, game_id)
        game.setup_techs_and_outer_rim(len(players), False, False)

        fake = SimpleNamespace(guild=SimpleNamespace(roles=[], get_member=lambda _id: None))
        for (pid, _name), faction, color in zip(players, ["hyd", "eri", "ori", "dra"],
                                                ["blue", "red", "green", "yellow"]):
            game.player_setup(pid, faction, color, fake)

        for pid, _name in players:
            assert game.get_player(pid)["color"], f"player {pid} not set up"

        drawing = DrawHelper(game.gamestate)
        renders = {
            "available_techs.webp": drawing.show_available_techs(),
            "minor_species.webp": drawing.show_minor_species(),
            "ai_stats.webp": drawing.show_AI_stats(),
        }
        for name, f in renders.items():
            size = save_render(f, os.path.join(OUT_DIR, name))
            print(f"  {name}: {size} bytes")

        print(f"OK: {len(players)}p game '{game_id}' rendered to {OUT_DIR}/")
    finally:
        with open("config.json", "wb") as f:
            f.write(config_backup)


if __name__ == "__main__":
    main()
