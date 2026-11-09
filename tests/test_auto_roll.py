"""Auto-roll: the bot rolls both sides of a fight against the AI to the end.

Covered here: the button only appears for a player-versus-AI pairing, the loop
rolls both sides without presses, and it ends with the salvo summary and the
board image of the survivors.
"""
from helpers.CombatHelper import Combat
from helpers.DrawHelper import DrawHelper
from tests.fakes import FakeChannel, POS, player_stats, reload


def _blue_cruiser():
    """A cruiser with one plasma die and enough hull to survive one AI salvo."""
    return player_stats("hyd", color="blue", cost_cruiser=5, base_cruiser_speed=1,
                        cruiser_parts=["plc", "shh"])


def _ai_game(make_game):
    return make_game({
        "advanced_ai": False,
        "wa_ai": False,
        "player_count": 1,
        "players": {"1": _blue_cruiser()},
        "board": {
            POS: {
                "owner": 0,
                "sector": 101,
                "disctile": 0,
                "player_ships": ["ai-anc", "blue-cru"],
                "attacker": ["blue"],
                "defender": ["ai"],
            }
        },
    })


def test_auto_roll_button_only_appears_against_the_ai(make_game):
    game = _ai_game(make_game)
    assert any(button.custom_id == f"autoRollCombat_{POS}"
               for button in Combat.getCombatButtons(game, POS).children)

    game.gamestate["players"]["2"] = player_stats("hyd", color="red")
    game.gamestate["board"][POS].update(player_ships=["blue-int", "red-int"],
                                        attacker=["blue"], defender=["red"])
    assert not any(button.custom_id == f"autoRollCombat_{POS}"
                   for button in Combat.getCombatButtons(game, POS).children)


def test_auto_roll_fires_both_sides_and_reports_survivors(make_game, no_random, press, run,
                                                        monkeypatch):
    game = _ai_game(make_game)
    monkeypatch.setattr(DrawHelper, "board_tile_image_file", lambda self, position: None)
    channel = FakeChannel("t-actions")
    run(channel.send("Combat will occur in this tile",
                     view=Combat.getCombatButtons(game, POS)))

    # The Ancestors fire first (speed 2) and hit twice; the cruiser then kills them.
    no_random([6, 6, 6])
    press(channel, 1, f"autoRollCombat_{POS}")

    texts = [content for content, _kwargs in channel.sent if content]
    summary = next(content for content in texts if "Auto-Roll Summary" in content)
    assert "The AI fired 1 salvo; the players fired 1 salvo." in summary
    assert "Remaining ships: blue: 1x cruiser" in summary
    assert "file" in channel.sent[-1][1]

    tile = reload(game).gamestate["board"][POS]
    assert "ai-anc" not in tile["player_ships"]
    assert "blue-cru" in tile["player_ships"]


def test_auto_roll_keeps_rolling_through_rounds_of_initiative(make_game, no_random, press, run,
                                                            monkeypatch):
    """A long fight wraps around the initiative order; auto-roll must keep
    rolling the next round rather than stop at the end of the first."""
    game = make_game({
        "advanced_ai": False,
        "wa_ai": False,
        "player_count": 1,
        "players": {"1": _blue_cruiser()},
        "board": {POS: {"owner": 0, "sector": 101, "disctile": 0,
                        "player_ships": ["ai-gcds", "blue-cru"],
                        "attacker": ["blue"], "defender": ["ai"]}},
    })
    monkeypatch.setattr(DrawHelper, "board_tile_image_file", lambda self, position: None)
    channel = FakeChannel("t-actions")
    run(channel.send("Combat will occur in this tile", view=Combat.getCombatButtons(game, POS)))

    # Four plasma hits (2 damage each) kill the 8-hp GCDS; its four dice miss.
    no_random([6] + [1] * 4 + [6] + [1] * 4 + [6] + [1] * 4 + [6])
    press(channel, 1, f"autoRollCombat_{POS}")

    summary = next(content for content, _kwargs in channel.sent
                   if content and "Auto-Roll Summary" in content)
    assert "The AI fired 3 salvos; the players fired 4 salvos." in summary
    assert "Remaining ships: blue: 1x cruiser" in summary
    assert "ai-gcds" not in reload(game).gamestate["board"][POS]["player_ships"]


def test_auto_roll_pools_the_players_salvo_like_the_ai(make_game):
    """Auto-roll uses the allocator the bot already uses for the AI, so a
    player's salvo is pooled to destroy a ship instead of spread."""
    game = make_game({
        "advanced_ai": False,
        "wa_ai": False,
        "players": {},
        "board": {POS: {"owner": 0, "sector": 101,
                        "player_ships": ["ai-grd", "ai-gcds", "blue-int"],
                        "attacker": ["blue"], "defender": ["ai"]}},
    })
    allocation = Combat.getAIHitAllocation(game, "blue", POS, 3, [[6, 1, "yellow"]] * 3, 0)
    assert allocation == ["ai-grd", "ai-grd", "ai-grd"]
