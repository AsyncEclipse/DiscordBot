"""Alliance state and the rule that allied ships never pin each other."""
import pytest

from Buttons.Explore import ExploreButtons
from tests.fakes import player_stats

POS = "101"


def _players(*colors):
    return {str(i): player_stats("hyd", color=color) for i, color in enumerate(colors, 1)}


def _board(ships, owner=0):
    return {POS: {"owner": owner, "sector": 101, "player_ships": list(ships)}}


def _alliance_game(make_game, colors=("blue", "red", "green"), player_count=4, ships=(), owner=0):
    return make_game({
        "player_count": player_count,
        "players": _players(*colors),
        "board": _board(ships, owner),
    })


class TestAllianceState:
    def test_form_places_a_faceup_tile_for_every_member(self, make_game):
        game = _alliance_game(make_game)
        game.formAlliance("nova", ["blue", "red"])

        assert game.gamestate["players"][game.get_player_from_color("blue")]["alliances"] == {"nova": False}
        assert game.areAllied("blue", "red")
        assert game.getAllianceMembers("nova") == ["blue", "red"]

    def test_strangers_and_self_are_not_allied(self, make_game):
        game = _alliance_game(make_game)
        game.formAlliance("nova", ["blue", "red"])

        assert not game.areAllied("blue", "green")
        assert not game.areAllied("blue", "blue")

    def test_betraying_ends_the_alliance_but_keeps_the_tile(self, make_game):
        game = _alliance_game(make_game)
        game.formAlliance("nova", ["blue", "red"])
        game.betrayAlliance("nova", "blue")

        assert not game.areAllied("blue", "red")
        assert game.getAllianceMembers("nova") == ["red"]
        assert game.gamestate["players"][game.get_player_from_color("blue")]["alliances"] == {"nova": True}

    def test_a_betrayer_cannot_rejoin_but_may_join_a_different_alliance(self, make_game):
        game = _alliance_game(make_game)
        game.formAlliance("nova", ["blue", "red"])
        game.betrayAlliance("nova", "blue")
        blue = game.getPlayerObjectFromColor("blue")

        assert "nova" not in game.getJoinableAllianceTiles(blue)
        assert "flare" in game.getJoinableAllianceTiles(blue)

        game.formAlliance("flare", ["blue", "green"])
        assert game.areAllied("blue", "green")
        assert not game.areAllied("blue", "red")

    def test_only_unfounded_tiles_can_start_an_alliance(self, make_game):
        game = _alliance_game(make_game)
        game.formAlliance("nova", ["blue", "red"])

        assert "nova" not in game.getUnfoundedAllianceTiles()
        assert game.getUnfoundedAllianceTiles() == ["flare", "vortex"]

    def test_draw_uses_an_unfounded_tile(self, make_game):
        game = _alliance_game(make_game)
        tile = game.drawAllianceTile(["blue", "red"])

        assert tile in ["nova", "flare", "vortex"]
        assert game.areAllied("blue", "red")

    def test_draw_returns_none_when_every_tile_is_founded(self, make_game):
        game = _alliance_game(make_game, colors=("blue", "red", "green", "yellow", "purple", "white"))
        for tile, pair in zip(["nova", "flare", "vortex"],
                              [("blue", "red"), ("green", "yellow"), ("purple", "white")]):
            game.formAlliance(tile, list(pair))

        assert game.drawAllianceTile(["blue", "red"]) is None

    @pytest.mark.parametrize("player_count,expected", [(2, 2), (4, 2), (5, 2), (6, 3), (9, 3)])
    def test_max_size_follows_the_player_count(self, make_game, player_count, expected):
        game = _alliance_game(make_game, player_count=player_count)
        assert game.getMaxAllianceSize() == expected


class TestAlliancePinning:
    def _unpinned(self, game, color):
        player = game.getPlayerObjectFromColor(color)
        ships = game.gamestate["board"][POS]["player_ships"]
        return ExploreButtons.doesPlayerHaveUnpinnedShips(player, ships, game, POS)

    def test_allied_ships_count_together_instead_of_pinning_each_other(self, make_game):
        # Two ships each, both sides equal strength: only an alliance breaks the tie.
        ships = ["blue-int", "blue-int", "red-int", "red-int"]
        game = _alliance_game(make_game, ships=ships)
        game.formAlliance("nova", ["blue", "red"])

        assert self._unpinned(game, "blue")
        assert self._unpinned(game, "red")

    def test_without_the_alliance_the_same_ships_pin(self, make_game):
        ships = ["blue-int", "blue-int", "red-int", "red-int"]
        game = _alliance_game(make_game, ships=ships)

        # 2 friendly against 2 enemy is not enough to move.
        assert not self._unpinned(game, "blue")

    def test_an_alliance_still_pins_against_a_larger_opponent(self, make_game):
        ships = ["blue-int", "red-int", "green-int", "green-int", "green-int"]
        game = _alliance_game(make_game, ships=ships)
        game.formAlliance("nova", ["blue", "red"])

        # 2 allied against 3 enemies.
        assert not self._unpinned(game, "blue")

    def test_a_betrayer_pins_their_former_ally_again(self, make_game):
        ships = ["blue-int", "blue-int", "red-int", "red-int"]
        game = _alliance_game(make_game, ships=ships)
        game.formAlliance("nova", ["blue", "red"])
        game.betrayAlliance("nova", "red")

        assert not self._unpinned(game, "blue")

    def test_gcds_still_pins_an_alliance(self, make_game):
        ships = ["blue-int", "red-int", "ai-gcds"]
        game = _alliance_game(make_game, ships=ships)
        game.formAlliance("nova", ["blue", "red"])

        # A GCDS is hostile to everyone, allies included.
        assert not self._unpinned(game, "blue")
