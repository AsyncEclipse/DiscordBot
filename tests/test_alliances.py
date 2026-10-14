"""Alliance state and the rule that allied ships never pin each other."""
import pytest

from Buttons.Explore import ExploreButtons
from Buttons.Influence import InfluenceButtons
from tests.fakes import POS, board_tile, players


def _alliance_game(make_game, colors=("blue", "red", "green"), player_count=4, ships=(), owner=0):
    return make_game({
        "player_count": player_count,
        "players": players(*colors),
        "board": board_tile(ships, owner),
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

    def test_a_lone_remaining_member_can_still_leave_and_then_join_elsewhere(self, make_game):
        """When one Ally leaves, the other keeps their faceup tile but is not
        stuck: they may also flip to Betrayer later, and only then join a
        different Alliance."""
        game = _alliance_game(make_game)
        game.formAlliance("nova", ["blue", "red"])
        game.betrayAlliance("nova", "blue")
        red = game.getPlayerObjectFromColor("red")

        assert game.getAllianceMembers("nova") == ["red"]
        assert game.isInAlliance(red)
        with pytest.raises(ValueError, match="more than one alliance"):
            game.formAlliance("flare", ["red", "green"])

        game.betrayAlliance("nova", "red")
        red = game.getPlayerObjectFromColor("red")

        assert not game.isInAlliance(red)
        assert game.getAllianceMembers("nova") == []
        game.formAlliance("flare", ["red", "green"])
        assert game.areAllied("red", "green")

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

    def test_refounding_a_dissolved_tile_preserves_the_betrayer_record(self, make_game):
        game = _alliance_game(make_game)
        game.formAlliance("nova", ["blue", "red"])
        game.betrayAlliance("nova", "blue")
        game.betrayAlliance("nova", "red")

        game.formAlliance("nova", ["green"])

        blue = game.getPlayerObjectFromColor("blue")
        green = game.getPlayerObjectFromColor("green")
        assert blue["alliances"]["nova"] is True
        assert green["alliances"]["nova"] is False

    def test_forming_cannot_add_a_member_past_the_player_count_limit(self, make_game):
        game = _alliance_game(make_game, player_count=4)
        game.formAlliance("nova", ["blue", "red"])

        with pytest.raises(ValueError, match="maximum size"):
            game.formAlliance("nova", ["green"])

        assert game.getAllianceMembers("nova") == ["blue", "red"]

    @pytest.mark.parametrize("player_count,expected", [(2, 2), (4, 2), (5, 2), (6, 3), (9, 3)])
    def test_max_size_follows_the_player_count(self, make_game, player_count, expected):
        game = _alliance_game(make_game, player_count=player_count)
        assert game.getMaxAllianceSize() == expected


class TestAlliancePinning:
    def _unpinned(self, game, color):
        player = game.getPlayerObjectFromColor(color)
        ships = game.gamestate["board"][POS]["player_ships"]
        return ExploreButtons.doesPlayerHaveUnpinnedShips(player, ships, game, POS)

    @pytest.mark.parametrize(("setup", "color", "unpinned"), [
        # 2 friendly against 2 enemy is not enough to move...
        ("no_alliance", "blue", False),
        # ...until an alliance lets the 2+2 count together, for both members.
        ("alliance", "blue", True),
        ("alliance", "red", True),
        # A betrayal splits them again.
        ("betrayed", "blue", False),
    ], ids=["solo", "allied_blue", "allied_red", "betrayed"])
    def test_allied_ships_count_together_instead_of_pinning_each_other(self, make_game, setup, color, unpinned):
        ships = ["blue-int", "blue-int", "red-int", "red-int"]
        game = _alliance_game(make_game, ships=ships)
        if setup != "no_alliance":
            game.formAlliance("nova", ["blue", "red"])
        if setup == "betrayed":
            game.betrayAlliance("nova", "red")

        assert self._unpinned(game, color) is unpinned

    def test_an_allys_ships_alone_are_not_yours(self, make_game):
        game = _alliance_game(make_game, ships=["red-int", "red-int"])
        game.formAlliance("nova", ["blue", "red"])

        assert self._unpinned(game, "blue") is False

    @pytest.mark.parametrize("ships", [
        # 2 allied against 3 enemies.
        ["blue-int", "red-int", "green-int", "green-int", "green-int"],
        # A GCDS is hostile to everyone, allies included.
        ["blue-int", "red-int", "ai-gcds"],
    ])
    def test_an_alliance_still_pins_against_a_larger_or_hostile_opponent(self, make_game, ships):
        game = _alliance_game(make_game, ships=ships)
        game.formAlliance("nova", ["blue", "red"])

        assert not self._unpinned(game, "blue")


class TestAllianceInfluence:
    def test_an_allys_ships_do_not_block_influence_into_a_shared_sector(self, make_game, monkeypatch):
        """Allies are not opponents, so a sector holding only you and your Ally
        is still a legal Influence target through a Wormhole Connection."""
        game = _alliance_game(make_game, colors=("blue", "red"), owner="blue")
        game.gamestate["board"]["102"] = {
            "owner": 0, "sector": 102, "disctile": 0, "player_ships": ["blue-int", "red-int"],
        }
        game.formAlliance("nova", ["blue", "red"])
        monkeypatch.setattr(InfluenceButtons, "areTwoTilesAdjacent", staticmethod(lambda *_a: True))
        blue = game.getPlayerObjectFromColor("blue")

        assert "102" in InfluenceButtons.getTilesToInfluence(game, blue)

    def test_an_opponent_alongside_an_ally_still_blocks_influence(self, make_game, monkeypatch):
        """An Ally's presence does not make a Sector safe to Influence if a
        third, non-Allied player also has Ships there."""
        game = _alliance_game(make_game, owner="blue")
        game.gamestate["board"]["102"] = {
            "owner": 0, "sector": 102, "disctile": 0,
            "player_ships": ["red-int", "green-int"],
        }
        game.formAlliance("nova", ["blue", "red"])
        monkeypatch.setattr(InfluenceButtons, "areTwoTilesAdjacent", staticmethod(lambda *_a: True))
        blue = game.getPlayerObjectFromColor("blue")

        assert "102" not in InfluenceButtons.getTilesToInfluence(game, blue)
