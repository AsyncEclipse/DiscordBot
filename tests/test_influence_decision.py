"""An influence disc offered at the end of the Combat Phase must be answered: place it or
decline it. Ignoring it is not an answer, so a player cannot ready up or keep the disc
available for a later turn."""
from Buttons.Influence import InfluenceButtons
from helpers.DrawHelper import DrawHelper
from tests.fakes import buttons, reload

P1, P2 = 1, 2
POS = "202"


def _no_images(monkeypatch):
    for name in ("mergeLocationsFile", "board_tile_image_file", "player_area",
                 "show_player_ship_area", "show_AI_stats", "show_map", "show_game"):
        monkeypatch.setattr(DrawHelper, name, lambda *a, **k: None)


def _end_of_round_with_an_unowned_sector(start_game, press, monkeypatch):
    _no_images(monkeypatch)
    game, ch = start_game()
    game.add_tile(POS, 0, "001")
    # blue parked a ship in the empty sector earlier in the round
    game.gamestate["board"][POS]["player_ships"] = ["blue-cru"]
    game.update()
    press(ch, P1, "FCIDblue_passForRound")
    press(ch, P2, "FCIDred_passForRound")
    thread = next(t for t in ch.threads if "Influence" in t.name)
    return game, ch, thread


def test_ready_for_upkeep_waits_for_the_influence_decision(start_game, press, monkeypatch):
    game, ch, thread = _end_of_round_with_an_unowned_sector(start_game, press, monkeypatch)
    assert reload(game).gamestate["influenceOffers"][POS]["colors"] == ["blue"]

    press(ch, P1, "readyForUpkeep")
    state = reload(game).gamestate
    assert state["peopleToCheckWith"] == ["blue"]
    assert "must first place or decline the influence disc in 202" in ch.sent[-1][0]
    assert "runUpkeep" not in buttons(ch)

    press(thread, P1, f"FCIDblue_declineInfluence_{POS}")

    state = reload(game).gamestate
    assert POS not in state.get("influenceOffers", {})
    prompt = thread.message_with(f"FCIDblue_addInfluenceFinish_{POS}")
    assert prompt.id in thread.deleted

    press(ch, P1, "readyForUpkeep")
    assert "Everyone is now ready for upkeep" in ch.sent[-1][0]
    assert "runUpkeep" in buttons(ch)


def test_placing_the_disc_answers_the_offer(start_game, press, monkeypatch):
    game, ch, thread = _end_of_round_with_an_unowned_sector(start_game, press, monkeypatch)

    press(thread, P1, f"FCIDblue_addInfluenceFinish_{POS}")

    state = reload(game).gamestate
    assert state["board"][POS]["owner"] == "blue"
    assert POS not in state.get("influenceOffers", {})
    press(ch, P1, "readyForUpkeep")
    assert "runUpkeep" in buttons(ch)


def test_upkeep_waits_for_an_offer_that_arrived_after_readying_up(start_game, press, run, monkeypatch):
    game, ch, thread = _end_of_round_with_an_unowned_sector(start_game, press, monkeypatch)
    press(thread, P1, f"FCIDblue_declineInfluence_{POS}")
    press(ch, P1, "readyForUpkeep")
    press(ch, P2, "readyForUpkeep")
    # blue readied up before this offer appeared, as when a battle resolves late
    run(InfluenceButtons.offerInfluenceDisc(reload(game), ch, "204", ["blue"], "blue, place or decline."))

    press(ch, P1, "runUpkeep")

    assert "Some influence discs still have to be placed or declined" in ch.sent[-1][0]
    assert not any("Start of round" in content for content, _ in ch.sent)


def test_ending_the_turn_declines_an_unanswered_offer(start_game, press, run):
    game, ch = start_game()
    game.add_tile(POS, 0, "001")
    run(InfluenceButtons.offerInfluenceDisc(game, ch, POS, ["blue"], "blue, place or decline."))
    prompt = ch.message_with(f"FCIDblue_addInfluenceFinish_{POS}")

    press(ch, P1, "FCIDblue_finishAction")
    press(ch, P1, "FCIDblue_endTurn")

    state = reload(game).gamestate
    assert POS not in state.get("influenceOffers", {})
    assert prompt.id in ch.deleted
    assert any("declined the influence disc in 202" in content for content, _ in ch.sent)
