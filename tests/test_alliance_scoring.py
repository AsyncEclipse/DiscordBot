"""Alliance scoring: tile VP, and the score allies win or lose with together."""
import pytest

from helpers.DrawHelper import DrawHelper
from tests.fakes import player_stats


def _players(spec):
    """spec: {color: (points_from_tiles, resources)} built as owned sectors."""
    players = {}
    for i, (color, tiles) in enumerate(spec.items(), 1):
        stats = player_stats("hyd", color=color)
        stats["owned_tiles"] = [f"1{i}{n}" for n in range(tiles)]
        stats["reputation_track"] = ["mixed"] * 4
        players[str(i)] = stats
    return players


def _board(players):
    board = {}
    for stats in players.values():
        for tile in stats["owned_tiles"]:
            board[tile] = {"owner": stats["color"], "sector": int(tile), "vp": 1, "artifact": 0}
    return board


def _game(make_game, spec, **extra):
    players = _players(spec)
    state = {
        "player_count": len(players),
        "players": players,
        "board": _board(players),
        "gameEnded": True,
    }
    state.update(extra)
    return make_game(state)


def _just_formed(game, _blue):
    game.formAlliance("nova", ["blue"])


def _betrayed(game, _blue):
    game.formAlliance("nova", ["blue"])
    game.betrayAlliance("nova", "blue")


def _betrayed_then_rejoined(game, _blue):
    game.formAlliance("nova", ["blue"])
    game.betrayAlliance("nova", "blue")
    game.formAlliance("flare", ["blue"])


class TestAllianceTilePoints:
    @pytest.mark.parametrize(("do", "expected_delta"), [
        (_just_formed, 2),
        (_betrayed, -3),
        (_betrayed_then_rejoined, -3 + 2),
    ], ids=["faceup_tile", "betrayer_tile", "betrayer_with_second_tile"])
    def test_tile_points(self, make_game, do, expected_delta):
        game = _game(make_game, {"blue": 3})
        blue = game.getPlayerObjectFromColor("blue")
        before = DrawHelper(game.gamestate).get_public_points(blue, False)

        do(game, blue)
        after = DrawHelper(game.gamestate).get_public_points(blue, False)

        assert after == before + expected_delta

    def test_rho_indi_gets_no_exemption_from_the_betrayer_penalty(self, make_game):
        game = _game(make_game, {"blue": 3})
        blue = game.getPlayerObjectFromColor("blue")
        blue["name"] = "Rho Indi Syndicate"
        before = DrawHelper(game.gamestate).get_public_points(blue, False)

        game.formAlliance("nova", ["blue"])
        game.betrayAlliance("nova", "blue")

        assert DrawHelper(game.gamestate).get_public_points(blue, False) == before - 3


class TestSharedScore:
    def test_an_alliance_averages_its_members_and_rounds_down(self, make_game):
        # blue: 1 sector + 2 for the faceup tile = 3. red: 2 sectors + 2 = 4.
        # (3 + 4) // 2 = 3, flooring the 3.5.
        game = _game(make_game, {"blue": 1, "red": 2})
        game.formAlliance("nova", ["blue", "red"])

        blue = game.getPlayerObjectFromColor("blue")
        red = game.getPlayerObjectFromColor("red")
        assert game.getUnitScore(blue) == 3
        assert game.getUnitScore(red) == 3

    def test_the_shared_score_can_exceed_both_members_own_scores(self, make_game):
        # blue 3 alone, red 8 alone, sharing (3 + 8) // 2 = 5 each.
        game = _game(make_game, {"blue": 1, "red": 6})
        blue = game.getPlayerObjectFromColor("blue")
        solo = DrawHelper(game.gamestate).get_public_points(blue, False)
        game.formAlliance("nova", ["blue", "red"])

        assert game.getUnitScore(blue) == 5
        assert game.getUnitScore(blue) > solo

    def test_an_alliance_wins_when_its_shared_score_leads(self, make_game):
        # allies share (3 + 4) // 2 = 3; green alone holds 2 sectors, so 2.
        game = _game(make_game, {"blue": 1, "red": 2, "green": 2})
        game.formAlliance("nova", ["blue", "red"])

        assert sorted(game.getScoringUnits()[0][0]) == ["blue", "red"]
        winner, score, _faction = game.getWinner()
        assert score == 3
        assert "blue" in winner and "red" in winner

    def test_a_betrayer_scores_alone(self, make_game):
        # After betraying, blue no longer shares red's 5.
        game = _game(make_game, {"blue": 2, "red": 5, "green": 4})
        game.formAlliance("nova", ["blue", "red"])
        game.betrayAlliance("nova", "blue")

        assert game.getScoringUnits()[0][0] == ["red"]
        assert game.getUnitScore(game.getPlayerObjectFromColor("blue")) < 3

    def test_without_alliances_every_player_scores_alone(self, make_game):
        game = _game(make_game, {"blue": 2, "red": 5})
        assert game.getScoringUnits()[0][0] == ["red"]
        assert game.getWinner()[1] == 5

    def test_a_tie_is_broken_by_the_shared_resource_total(self, make_game):
        game = _game(make_game, {"blue": 3, "red": 3})
        game.gamestate["players"][game.get_player_from_color("red")]["science"] = 9

        assert game.getScoringUnits()[0][0] == ["red"]

    def test_every_allies_tourney_division_lands_on_100(self, make_game):
        """search_commands divides each player's shared score by the winning shared
        score, so no member of a winning alliance can register above 100%."""
        game = _game(make_game, {"blue": 1, "red": 6, "green": 3})
        game.formAlliance("nova", ["blue", "red"])

        winners, winningScore, _resources = game.getScoringUnits()[0]

        assert sorted(winners) == ["blue", "red"]
        for color in winners:
            player = game.getPlayerObjectFromColor(color)
            assert int(100 * game.getUnitScore(player, True) / winningScore) == 100
