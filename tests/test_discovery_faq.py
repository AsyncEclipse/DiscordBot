"""Discovery Tile ownership at the end of the Combat Phase (Eclipse FAQ).

The FAQ settles who takes a Discovery Tile when combat ends without a winner or
the Ancients die in a Descendants-controlled sector: the player who Controls the
Sector takes the tile at the end of the Combat Phase. If nobody Controls it, the
first player to place an Influence Disc there takes it immediately, and if no
disc is placed the first player with a Ship there takes it at the end of a later
Combat Phase.
"""
import pytest

from Buttons.Influence import InfluenceButtons
from Buttons.Turn import TurnButtons
from helpers.CombatHelper import Combat
from tests.fakes import FakeInteraction, POS, board_tile, offered_ids, players


def _game(make_game, colors, ships, owner=0, extra=None, names=None):
    game_players = players(*colors)
    for stats in game_players.values():
        if names and stats["color"] in names:
            stats["name"] = names[stats["color"]]
    board = board_tile(ships, owner)
    if extra:
        board[POS].update(extra)
    return make_game({"player_count": len(colors), "players": game_players, "board": board,
                      "advanced_ai": False, "wa_ai": False, "discTiles": ["socha"], "roundNum": 1})


def _explore_offer(color):
    return f"FCID{color}_exploreDiscoveryTile_{POS}_deleteMsg"


class TestNoShipsRemain:
    """FAQ: no Ships left at the end of the Combat Phase."""

    def test_the_controller_takes_the_tile(self, make_game, run):
        game = _game(make_game, ("blue", "red"), [], owner="blue", extra={"disctile": 1})
        inter = FakeInteraction()

        run(Combat.settleDiscoveryTiles(game, inter.channel))

        assert _explore_offer("blue") in offered_ids(inter)

    def test_without_a_controller_nobody_takes_it_yet(self, make_game, run):
        game = _game(make_game, ("blue", "red"), [], owner=0, extra={"disctile": 1})
        inter = FakeInteraction()

        run(Combat.settleDiscoveryTiles(game, inter.channel))

        assert not any("exploreDiscoveryTile" in button_id for button_id in offered_ids(inter))


class TestDracoKeepsTheTile:
    """FAQ: Ancients destroyed from a Descendants-Controlled Sector."""

    @pytest.mark.parametrize("ships", [[], ["blue-cru"], ["red-cru"]],
                             ids=["no_ships", "draco_ships", "enemy_ships"])
    def test_the_controller_takes_the_tile(self, make_game, run, ships):
        game = _game(make_game, ("blue", "red"), ships, owner="blue",
                     extra={"disctile": 1, "money_pop": [1]},
                     names={"blue": "Descendants of Draco"})
        inter = FakeInteraction()

        run(Combat.settleDiscoveryTiles(game, inter.channel))

        assert _explore_offer("blue") in offered_ids(inter)

    def test_ancients_still_guard_the_tile(self, make_game, run):
        game = _game(make_game, ("blue", "red"), ["blue-cru", "ai-anc"], owner="blue",
                     extra={"disctile": 1}, names={"blue": "Descendants of Draco"})
        inter = FakeInteraction()

        run(Combat.settleDiscoveryTiles(game, inter.channel))

        assert not any("exploreDiscoveryTile" in button_id for button_id in offered_ids(inter))


class TestInfluenceDisc:
    """FAQ: the first player to place an Influence Disc takes the tile at once."""

    def test_the_first_disc_takes_the_tile_immediately(self, make_game, run):
        game = _game(make_game, ("blue", "red"), [], owner=0, extra={"disctile": 1})
        blue = game.getPlayerObjectFromColor("blue")
        inter = FakeInteraction()

        run(InfluenceButtons.addInfluenceFinish(game, blue, inter, f"addInfluenceFinish_{POS}"))

        assert game.gamestate["board"][POS]["owner"] == "blue"
        assert game.gamestate["board"][POS]["disctile"] == 0
        assert any("usedDiscForAbility" in button_id for button_id in offered_ids(inter))

    def test_a_tile_already_taken_is_not_offered_again(self, make_game, run):
        game = _game(make_game, ("blue", "red"), [], owner=0, extra={"disctile": 0})
        blue = game.getPlayerObjectFromColor("blue")
        inter = FakeInteraction()

        run(InfluenceButtons.addInfluenceFinish(game, blue, inter, f"addInfluenceFinish_{POS}"))

        assert game.gamestate["board"][POS]["owner"] == "blue"
        assert not any("usedDiscForAbility" in button_id for button_id in offered_ids(inter))


class TestFirstShipInALaterPhase:
    """FAQ: with no disc placed, the first player with a Ship takes the tile."""

    def test_the_first_player_with_a_ship_takes_the_tile(self, make_game, run):
        game = _game(make_game, ("blue", "red"), ["blue-cru"], owner=0, extra={"disctile": 1})
        inter = FakeInteraction()

        run(Combat.settleDiscoveryTiles(game, inter.channel))

        assert _explore_offer("blue") in offered_ids(inter)

    def test_allies_are_offered_in_entry_order(self, make_game, run):
        game = _game(make_game, ("blue", "red"), ["blue-cru", "red-cru"], owner=0,
                     extra={"disctile": 1, "entryOrder": ["red", "blue"]})
        game.formAlliance("nova", ["blue", "red"])
        inter = FakeInteraction()

        run(Combat.settleDiscoveryTiles(game, inter.channel))

        ids = offered_ids(inter)
        assert _explore_offer("red") in ids
        assert _explore_offer("blue") not in ids


class TestRunUpkeepWiring:
    def test_upkeep_settles_the_tiles(self, make_game, run, monkeypatch):
        game = _game(make_game, ("blue", "red"), [], owner="blue", extra={"disctile": 1})
        game.gamestate["roundNum"] = 9
        inter = FakeInteraction()

        async def noop(*_args, **_kwargs):
            return None

        monkeypatch.setattr(game, "upkeep", noop)
        monkeypatch.setattr(game, "showUpdate", noop)
        monkeypatch.setattr(game, "saveEndRound", lambda: None)

        run(TurnButtons.runUpkeep(game, inter))

        assert _explore_offer("blue") in offered_ids(inter)
