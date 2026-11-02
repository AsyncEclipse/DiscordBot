import json
from pathlib import Path

import pytest

from Buttons.Build import BuildButtons
from Buttons.Research import ResearchButtons
from helpers import FactionData
from helpers.CombatHelper import Combat
from helpers.DrawHelper import DrawHelper
from helpers.PlayerHelper import PlayerHelper
from tests.fakes import FakeInteraction, POS, player_stats


@pytest.mark.parametrize("alias, canonical", [
    ("Orian Hegemony", "Orion Hegemony"),
    ("Eridian Empire", "Eridani Empire"),
])
def test_old_faction_names_resolve_to_the_same_artwork_and_facts(alias, canonical):
    assert FactionData.artwork_name(alias) == FactionData.artwork_name(canonical)
    assert FactionData.of({"name": alias}) == {**FactionData.of({"name": canonical}), "name": alias}


def test_every_faction_row_carries_its_artwork_and_colour():
    """factions.json drives the emoji, board and setup colour lookups."""
    for key, faction in FactionData.FACTIONS.items():
        artwork = faction["artwork"]
        assert FactionData.artwork_name(faction["name"]) == artwork, key
        assert faction["setup_color"], key
        assert Path(f"images/resources/components/factions/{artwork}_board.png").exists(), key
        assert Path(f"images/resources/components/layouts/factionImages/{artwork}_image.png").exists(), key
        if faction.get("community"):
            assert Path(f"images/resources/components/factions/{artwork}_info.png").exists(), key


def test_all_starting_technologies_and_blueprint_parts_exist():
    with open("data/techs.json") as tech_file, open("data/parts.json") as part_file:
        techs, parts = json.load(tech_file), json.load(part_file)
    for key, faction in FactionData.FACTIONS.items():
        for track in ("military", "grid", "nano"):
            assert set(faction[f"{track}_tech"]) <= techs.keys(), key
        for ship in ("interceptor", "cruiser", "dread", "starbase"):
            if f"{ship}_parts" in faction:
                assert set(faction[f"{ship}_parts"]) <= parts.keys(), (key, ship)
        for ship, cells in faction.get("blueprint_slots", {}).items():
            assert len(cells) == len(faction[f"{ship}_parts"]), (key, ship)


def test_abilities_come_from_the_faction_data():
    assert FactionData.has(player_stats("tm"), "techno_magic")
    assert not FactionData.has(player_stats("hyd"), "techno_magic")
    # A faction that is not in the file at all falls back to its own fields.
    assert not FactionData.has({"name": "Homebrew", "color": "blue"}, "techno_magic")


def test_rho_trades_money_on_the_factions_own_ratio():
    player = player_stats("rho", science=0, money=6, materials=0)
    hyd = player_stats("hyd", science=0, money=6, materials=0)
    assert ResearchButtons.getPlayerTotalAvailableScience(player, None) == 4
    assert ResearchButtons.getPlayerTotalAvailableScience(hyd, None) == 2


def test_rho_pays_two_resources_for_one_money_trade(run):
    for faction, expected in (("rho", 2), ("hyd", 1)):
        interaction = FakeInteraction()
        run(BuildButtons.convertResource(None, player_stats(faction, color="blue", money=6), interaction,
                                         "convertResource_none_4_201_4_0_6_0_Money"))
        assert f"Resources spent: {expected}" in interaction.message.edited["content"]


def test_rho_has_two_ambassador_slots_and_three_reputation_only_slots():
    rho = FactionData.FACTIONS["rho"]
    assert rho["reputation_track"] == ["mixed", "mixed", "rep", "rep", "rep"]
    assert rho["reputation_only_slots"] == [2, 3, 4]
    player = player_stats("rho")
    assert [PlayerHelper.is_reputation_only_slot(player, index) for index in range(5)] == \
        [False, False, True, True, True]


def test_starting_ships_come_from_the_faction_data(make_game):
    def home_ships(faction):
        stats = player_stats(faction, color="blue")
        game = make_game({
            "players": {"1": stats},
            "board": {"201": {"sector": stats["home_planet"], "orientation": 0, "player_ships": []}},
        })
        game.setup_finished()
        return game.gamestate["board"]["201"]["player_ships"]

    assert home_ships("exl") == ["blue-orb", "blue-int"]
    assert home_ships("rho") == ["blue-int", "blue-int"]
    assert home_ships("her") == ["blue-cru"]
    assert home_ships("hyd") == ["blue-int"]
    assert home_ships("tur") == ["blue-sb"]
    assert home_ships("wul") == ["blue-cru"]


def _tile_game(make_game, faction, owner="blue", **tile):
    stats = player_stats(faction, color=owner)
    board_tile = {"owner": owner, "sector": 101, "disctile": 0, "player_ships": [],
                  "orbital_pop": [0]}
    board_tile.update(tile)
    return make_game({"players": {"1": stats}, "board": {POS: board_tile}})


def test_an_orbital_counts_as_a_ship_only_for_a_faction_that_says_so(make_game):
    assert Combat.exile_orbital_exists(
        _tile_game(make_game, "exl", player_ships=["blue-orb"], orbital_pop=[1]), POS)
    assert not Combat.exile_orbital_exists(
        _tile_game(make_game, "hyd", player_ships=["blue-orb"], orbital_pop=[1]), POS)


def test_only_the_draco_data_gives_a_pass_against_the_ancients(make_game):
    draco = _tile_game(make_game, "dra", player_ships=["blue-int", "ai-anc"])
    assert Combat.isDracoAgainstAncients(draco, POS)
    assert not Combat.isDracoAgainstAncients(
        _tile_game(make_game, "hyd", player_ships=["blue-int", "ai-anc"]), POS)


def test_end_game_points_come_from_the_faction_data(make_game):
    def points(faction, **tile):
        stats = player_stats(faction, color="blue")
        board_tile = {"sector": 101, "vp": 2, "owner": "blue", "artifact": 0, "player_ships": []}
        board_tile.update(tile)
        game = make_game({"players": {"1": stats}, "board": {POS: board_tile}})
        return DrawHelper(game.gamestate).get_public_points(stats, False)

    assert points("hyd") == 2
    assert points("pla") == 3
    assert points("ra", artifact=1) == 3
    assert points("exl", orbital_pop=[1]) == 3
    assert points("lyr", shrines=2) == 4
    assert points("dra", player_ships=["blue-int", "ai-anc"]) == 3
