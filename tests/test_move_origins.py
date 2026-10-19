import pytest

from Buttons.Move import MoveButtons
from tests.fakes import player_stats


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
        "board": {"102": {"owner": "blue", "sector": 102, "disctile": 0,
                          "player_ships": ships, "orbital_pop": [1]}},
    })

    assert MoveButtons.getListOfUnpinnedShipTiles(game, player) == expected
