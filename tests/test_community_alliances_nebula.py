from helpers.CombatHelper import Combat
from tests.fakes import FakeInteraction, offered_buttons, reload


def test_community_alliance_fights_in_nebula(start_game, run, press):
    game, channel = start_game(4, factions=["tm", "atl", "ra", "hyd"])
    game.setAlliances(True)
    game.formAlliance("nova", ["blue", "red"])
    game.add_tile("202", 0, "295")
    game.add_units(["blue-int", "red-int", "yellow-int"], "202b")
    game.setCombatants(["blue", "red", "yellow"], "202b")
    game.gamestate["tilesToResolve"] = [295]
    game.gamestate["queuedQuestions"] = []
    game.update()

    run(Combat.startCombat(game, channel, "202b"))
    assert "FCIDblue_technoMagic_202b_interceptor" in [
        button.custom_id for button in offered_buttons(FakeInteraction(channel))]
    assert Combat.findSidesInTile(game, "202b") == [["blue", "red"], ["yellow"]]

    inter = press(channel, 1, "FCIDblue_technoMagic_202b_interceptor")
    slot = next(c.custom_id for c in inter.message.edited["view"].children if c.custom_id.endswith("_tm202b_3"))
    inter = press(channel, 1, slot)
    part = next(c.custom_id for c in inter.message.edited["view"].children if c.custom_id.endswith("_hul_3_tm202b"))
    press(channel, 1, part)
    game = reload(game)
    assert game.get_player(1)["interceptor_parts"][-1] == "hul"

    game.destroy_ship("yellow-int", "202b", "blue")
    run(Combat.declareAWinner(game, FakeInteraction(channel), "202b"))
    assert game.get_player(1)["interceptor_parts"][-1] == "empty"
    assert not any("addInfluenceFinish" in button.custom_id for button in offered_buttons(FakeInteraction(channel)))
    assert "202b" not in [pos for sector, pos in Combat.findUnownedTilesToTakeOver(game)]

    run(Combat.settleDiscoveryTiles(game, channel))
    claims = [button.custom_id for button in offered_buttons(FakeInteraction(channel))
              if "exploreDiscoveryTile" in button.custom_id]
    assert claims == ["FCIDblue_exploreDiscoveryTile_202b_deleteMsg"]
