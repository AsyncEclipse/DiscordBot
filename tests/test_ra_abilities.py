"""Remnants of Ra species rules: Power of the Ancients and Secrets of the Ancients.

Both were read off the faction's printed card and board: an extra population cube on the
influence disc of any sector they control with an artifact key (home sector included), one
more VP per such sector, and only one colony ship refreshed per Influence action.
"""
import pytest

from helpers.DrawHelper import DrawHelper
from tests.fakes import FakeMessage, buttons, player_stats, reload


@pytest.fixture(autouse=True)
def _no_tile_render(monkeypatch):
    """These tests cover cube bookkeeping, not rendering. The flows attach tile images, and
    rendering real art costs a one-time image-cache load the whole suite would pay for."""
    monkeypatch.setattr(DrawHelper, "board_tile_image_file", lambda self, position: None)
    monkeypatch.setattr(DrawHelper, "mergeLocationsFile", lambda self, positions: None)


# A ring 1 sector with an artifact key (data/sectors.json), free in a two player start.
ARTIFACT_SECTOR = "107"


def artifact_board():
    return {"board": {"201": {"owner": "blue", "vp": 2, "artifact": 0, "player_ships": []},
                      "107": {"owner": "blue", "vp": 1, "artifact": 1, "player_ships": []},
                      "109": {"owner": "red", "vp": 3, "artifact": 1, "player_ships": []}}}


def test_secrets_of_the_ancients_scores_controlled_artifact_sectors():
    drawing = DrawHelper(artifact_board())
    remnant = player_stats("ra", name="Remnants of Ra", color="blue")
    other = player_stats("hyd", name="Hydran Progress", color="blue")

    assert drawing.get_public_points(remnant, False) == 2 + 1 + 1
    assert drawing.get_public_points(other, False) == 2 + 1


def test_power_of_the_ancients_cube_comes_from_its_population_track(make_game):
    game = make_game({"board": {"107": {"artifact": 1, "player_ships": []}},
                      "players": {"1": {"color": "blue", "colony_ships": 1, "money_pop_cubes": 11,
                                        "science_pop_cubes": 12, "material_pop_cubes": 12}}})

    assert game.add_disc_pop("money", "107", "1") is True
    assert game.gamestate["board"]["107"]["disc_pop"] == [1]
    assert game.gamestate["players"]["1"]["money_pop_cubes"] == 10
    assert game.gamestate["players"]["1"]["colony_ships"] == 0
    # A disc holds one cube; the same sector is not offered twice.
    assert game.add_disc_pop("science", "107", "1") is False
    assert game.gamestate["players"]["1"]["science_pop_cubes"] == 12


def test_power_of_the_ancients_requires_a_colony_ship(make_game):
    game = make_game({"board": {"107": {"artifact": 1}},
                      "players": {"1": {"color": "blue", "colony_ships": 0, "money_pop_cubes": 11}}})

    assert game.add_disc_pop("money", "107", "1") is False
    assert "disc_pop" not in game.gamestate["board"]["107"]
    assert game.get_player(1)["money_pop_cubes"] == 11
    assert game.get_player(1)["colony_ships"] == 0


def test_taking_control_of_an_artifact_sector_offers_the_cube(start_game, press):
    game, channel = start_game(factions=["ra", "eri"])
    game.add_tile("205", 0, ARTIFACT_SECTOR)

    press(channel, 1, "FCIDblue_addInfluenceFinish_205")

    menu = buttons(channel)
    assert "FCIDblue_ancientsCube_money_205" in menu
    assert "FCIDblue_ancientsCube_science_205" in menu
    press(channel, 1, "FCIDblue_ancientsCube_science_205")

    state = reload(game)
    assert state.gamestate["board"]["205"]["disc_pop"] == [1]
    assert state.get_player(1)["science_pop_cubes"] == 11


def test_a_second_answer_on_the_cube_prompt_does_not_place_a_second_cube(start_game, press):
    game, channel = start_game(factions=["ra", "eri"])
    game.add_tile("205", 0, ARTIFACT_SECTOR)
    press(channel, 1, "FCIDblue_addInfluenceFinish_205")

    message = FakeMessage()
    press(channel, 1, "FCIDblue_ancientsCube_money_205", message)
    press(channel, 1, "FCIDblue_ancientsCube_science_205", message)

    player = reload(game).get_player(1)
    assert player["money_pop_cubes"] == 10
    assert player["science_pop_cubes"] == 12


def test_a_plain_sector_is_not_offered_the_cube(start_game, press):
    game, channel = start_game(factions=["ra", "eri"])
    game.add_tile("205", 0, "101")

    press(channel, 1, "FCIDblue_addInfluenceFinish_205")

    assert not [cid for cid in buttons(channel) if "ancientsCube" in cid]


def test_other_factions_are_not_offered_the_cube(start_game, press):
    game, channel = start_game(factions=["hyd", "eri"])
    game.add_tile("205", 0, ARTIFACT_SECTOR)

    press(channel, 1, "FCIDblue_addInfluenceFinish_205")

    assert not [cid for cid in buttons(channel) if "ancientsCube" in cid]


def test_cube_returns_to_a_track_when_the_sector_is_lost(start_game, press):
    game, channel = start_game(factions=["ra", "eri"])
    game.add_tile("205", 0, ARTIFACT_SECTOR)
    game.add_disc_pop("money", "205", "1")
    game.get_player(1)["owned_tiles"].append("205")
    game.gamestate["board"]["205"]["owner"] = "blue"
    game.update()

    press(channel, 1, "FCIDblue_removeInfluenceStart")
    press(channel, 1, "FCIDblue_removeInfluenceFinish_205_normal")
    state = reload(game)
    assert state.gamestate["board"]["205"]["disc_pop"][0] == 0
    assert state.get_player(1)["money_pop_cubes"] == 10

    # The cube is returned the same way a neutral cube is: the owner picks the track.
    assert "FCIDblue_addCubeToTrack_money" in buttons(channel)
    press(channel, 1, "FCIDblue_addCubeToTrack_money")
    assert reload(game).get_player(1)["money_pop_cubes"] == 11


@pytest.mark.parametrize("faction, refreshed", [("ra", 2), ("hyd", 3)])
def test_influence_refreshes_one_colony_ship_only_for_remnants(start_game, press, faction, refreshed):
    game, channel = start_game(factions=[faction, "eri"])
    game.get_player(1)["colony_ships"] = 1
    game.update()

    press(channel, 1, "FCIDblue_startInfluence")
    expected_label = "Refresh 1 Colony Ship" if faction == "ra" else "Refresh 2 Colony Ships"
    assert expected_label in buttons(channel).values()
    press(channel, 1, "FCIDblue_refreshPopShips")

    assert reload(game).get_player(1)["colony_ships"] == refreshed
