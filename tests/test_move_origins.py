import pytest

from Buttons.Explore import ExploreButtons
from Buttons.Move import MoveButtons
from tests.fakes import POS, board_tile, player_stats


@pytest.mark.parametrize("ships, expected", [
    (["blue-orb"], []),
    (["blue-sb"], []),
    (["blue-orb", "red-int"], []),
    (["blue-orb", "blue-int"], ["102"]),
    (["blue-cru"], ["102"]),
    (["blue-drd"], ["102"]),
    (["blue-orb", "blue-int", "red-int"], ["102"]),
    (["blue-orb", "blue-int", "red-int", "red-cru"], []),
])
def test_move_origins_require_a_mobile_unpinned_ship(make_game, ships, expected):
    player = player_stats("exl")
    game = make_game({
        "players": {"1": player},
        "board": board_tile(ships, owner="blue", sector=102, orbital_pop=[1]),
    })

    assert MoveButtons.getListOfUnpinnedShipTiles(game, player) == expected


@pytest.mark.parametrize("faction, opponent, expected", [
    ("hyd", "ai-anc", False),
    ("dra", "ai-anc", True),
    ("hyd", "ai-grd", False),
    ("dra", "ai-grd", False),
    ("hyd", "ai-gcds", False),
    ("dra", "ai-gcds", False),
])
def test_only_draco_is_unpinned_by_ancients(make_game, faction, opponent, expected):
    player = player_stats(faction, color="blue")
    ships = ["blue-int", opponent]
    game = make_game({
        "players": {"1": player},
        "board": board_tile(ships),
    })

    assert ExploreButtons.doesPlayerHaveUnpinnedShips(player, ships, game, POS) is expected
