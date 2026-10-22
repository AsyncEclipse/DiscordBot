import pytest

from Buttons.Explore import ExploreButtons
from Buttons.Influence import InfluenceButtons
from tests.fakes import board_tile, player_stats


def test_draco_can_influence_two_ancients_from_interceptor_pinned_by_gcds(make_game):
    player = player_stats("dra")
    game = make_game({
        "players": {"1": player},
        "board": {
            "000": board_tile(
                ["blue-int", "ai-gcds"], sector=0, orientation=0,
                wormholes=[0, 1, 2, 3, 4, 5], gcds=1,
            )["0"],
            "101": board_tile(
                ["ai-anc", "ai-anc"], sector=101, orientation=0,
                wormholes=[1, 2, 3, 4, 5], ancient=2,
            )["101"],
        },
    })

    assert not ExploreButtons.doesPlayerHaveUnpinnedShips(
        player, game.gamestate["board"]["000"]["player_ships"], game, "000",
    )
    # Influence (p. 14) requires an adjacent Ship, without Explore's Unpinned restriction.
    assert InfluenceButtons.getTilesToInfluence(game, player) == ["101"]

@pytest.mark.parametrize("target, warp", [("101", 0), ("301", 1)], ids=["wormhole", "warp"])
@pytest.mark.parametrize("faction, ships, expected", [
    ("dra", ["ai-anc", "ai-anc"], True),
    ("hyd", ["ai-anc", "ai-anc"], False),
    ("dra", ["ai-grd"], False),
    ("dra", ["ai-gcds"], False),
    ("dra", ["ai-anc", "red-int"], False),
])
def test_ancient_exception_preserves_hostile_ship_checks(make_game, target, warp, faction, ships, expected):
    player = player_stats(faction)
    game = make_game({
        "players": {"1": player, "2": player_stats("hyd", color="red")},
        "board": {
            "000": {
                "owner": 0, "player_ships": ["blue-int", "ai-gcds"],
                "orientation": 0, "wormholes": [0, 1, 2, 3, 4, 5], "warp": warp,
            },
            target: {
                "owner": 0, "player_ships": ships,
                "orientation": 0, "wormholes": [0, 1, 2, 3, 4, 5], "warp": warp,
            },
        },
    })

    assert (target in InfluenceButtons.getTilesToInfluence(game, player)) is expected
