"""Discovery Tile ownership at the end of the Combat Phase (Eclipse FAQ).

The FAQ settles who takes a Discovery Tile when combat ends without a winner or
the Ancients die in a Descendants-controlled sector: the player who Controls the
Sector takes the tile at the end of the Combat Phase. If nobody Controls it, the
first player to place an Influence Disc there takes it immediately, and if no
disc is placed the first player with a Ship there takes it at the end of a later
Combat Phase.
"""
import pytest

from Buttons.DiscoveryTile import DiscoveryTileButtons
from Buttons.Influence import InfluenceButtons
from Buttons.Turn import TurnButtons
from helpers.CombatHelper import Combat
from tests.fakes import FakeChannel, FakeInteraction, POS, board_tile, buttons, offered_ids, players, reload


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


def _stub_upkeep(game, monkeypatch):
    """Keep upkeep off Discord and off the filesystem, recording whether it ran."""
    ran = []

    async def upkeep(*_args, **_kwargs):
        ran.append(True)

    async def noop(*_args, **_kwargs):
        return None

    monkeypatch.setattr(game, "upkeep", upkeep)
    monkeypatch.setattr(game, "showUpdate", noop)
    monkeypatch.setattr(game, "saveEndRound", lambda: None)
    return ran


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
        _stub_upkeep(game, monkeypatch)

        run(TurnButtons.runUpkeep(game, inter))

        assert _explore_offer("blue") in offered_ids(inter)


class TestUpkeepWaitsForDiscoveryTiles:
    """The round cannot end while a Discovery Tile is unclaimed or an Atlantians draw is
    unpicked, otherwise the draw would happen after the next round's techs are revealed."""

    def test_an_unclaimed_tile_blocks_upkeep(self, make_game, run, monkeypatch):
        game = _game(make_game, ("blue", "red"), [], owner="blue", extra={"disctile": 1})
        game.gamestate["roundNum"] = 9
        inter = FakeInteraction()
        ran = _stub_upkeep(game, monkeypatch)

        run(TurnButtons.runUpkeep(game, inter))

        assert "Discovery tiles still have to be claimed" in inter.channel.sent[-1][0]
        assert "Tile 101: blue" in inter.channel.sent[-1][0]
        assert ran == []

    def test_upkeep_waits_for_the_drawn_tile_to_be_resolved(self, make_game, run, monkeypatch):
        game = _game(make_game, ("blue", "red"), [], owner="blue", extra={"disctile": 1})
        game.gamestate["roundNum"] = 9
        blue = game.getPlayerObjectFromColor("blue")
        inter = FakeInteraction()
        ran = _stub_upkeep(game, monkeypatch)

        run(DiscoveryTileButtons.exploreDiscoveryTile(game, POS, inter, blue))
        run(TurnButtons.runUpkeep(game, inter))

        assert ran == []

    def test_an_unpicked_atlantians_draw_blocks_upkeep(self, make_game, run, monkeypatch):
        game = _game(make_game, ("blue", "red"), [], owner="blue", extra={"disctile": 1},
                     names={"blue": "Atlantians"})
        game.gamestate["roundNum"] = 9
        game.gamestate["discTiles"] = ["som", "jud"]
        blue = game.getPlayerObjectFromColor("blue")
        inter = FakeInteraction()
        ran = _stub_upkeep(game, monkeypatch)

        run(DiscoveryTileButtons.exploreDiscoveryTile(game, POS, inter, blue))
        run(TurnButtons.runUpkeep(game, inter))

        assert "the Atlantians still have to choose" in inter.channel.sent[-1][0]
        assert ran == []

        run(DiscoveryTileButtons.selectDiscTile(game, inter, "selectDiscTile_som_jud_101", blue))
        run(TurnButtons.runUpkeep(game, inter))

        assert ran == []


@pytest.mark.parametrize("faction, deck", [("hyd", ["som"]), ("atl", ["som", "jud"])])
def test_upkeep_reoffers_lost_discovery_choices_without_redrawing(start_game, run, press, faction, deck):
    game, channel = start_game(factions=[faction, "eri"])
    tile = "201"
    game.gamestate["discTiles"] = list(deck)
    game.addDiscTile(tile)
    run(DiscoveryTileButtons.exploreDiscoveryTile(game, tile, FakeInteraction(channel), game.get_player(1)))
    old_id = next(cid for cid in buttons(channel) if "keepDiscForPoints" in cid or "selectDiscTile" in cid)
    old_message = channel.message_with(old_id)
    state = reload(game)
    for player in state.gamestate["players"].values():
        player["passed"] = True
    state.update()
    remaining_deck = list(state.gamestate["discTiles"])

    press(channel, 1, "runUpkeep")

    assert channel.message_with(old_id).id != old_message.id
    assert reload(game).gamestate["discTiles"] == remaining_deck
    inter = press(channel, 1, old_id, message=old_message)
    assert "latest prompt" in inter.followup.sent[0][0]
    press(channel, 1, old_id)
    if faction == "atl":
        press(channel, 1, "FCIDblue_keepDiscForPoints_201")
    state = reload(game)
    assert state.get_player(1)["disc_tiles_for_points"] == 1
    assert not state.gamestate.get("pendingDiscoveryResolutions")
    assert not state.gamestate.get("pendingDiscoveryPrompts")


def test_upkeep_reoffers_an_unclaimed_tile_after_its_offer_was_lost(make_game, run):
    game = _game(make_game, ("blue", "red"), [], owner="blue", extra={"disctile": 1})
    original_channel = FakeChannel("t-old")
    run(Combat.settleDiscoveryTiles(game, original_channel))
    new_channel = FakeChannel("t-actions")

    run(TurnButtons.runUpkeep(game, FakeInteraction(new_channel)))

    assert _explore_offer("blue") in buttons(new_channel)
