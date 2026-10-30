"""Diplomatic relations: forming them, and the Alliance option they unlock."""
from Buttons.DiplomaticRelations import DiplomaticRelationsButtons
from tests.fakes import FakeInteraction, offered_ids, player_stats


def _player(color):
    return player_stats("hyd", color=color)


def _game(make_game, active="blue"):
    return make_game({
        "alliances": True,
        "player_count": 4,
        "roundNum": 3,
        "activePlayerColor": [active],
        "reputation_tiles": [],
        "players": {str(i): _player(color)
                    for i, color in enumerate(["blue", "red", "green", "yellow"], 1)},
    })


def test_accepting_relations_offers_the_active_ally_the_alliance_button(make_game, run):
    game = _game(make_game)
    blue = game.getPlayerObjectFromColor("blue")
    inter = FakeInteraction()

    run(DiplomaticRelationsButtons.acceptRelationsWith(game, blue, inter, "acceptRelationsWith_red"))

    assert "FCIDblue_startAlliance" in offered_ids(inter)


def test_accepting_relations_offers_nothing_when_neither_ally_is_on_turn(make_game, run):
    game = _game(make_game, active="green")
    blue = game.getPlayerObjectFromColor("blue")
    inter = FakeInteraction()

    run(DiplomaticRelationsButtons.acceptRelationsWith(game, blue, inter, "acceptRelationsWith_red"))

    assert not any(custom_id.endswith("_startAlliance") for custom_id in offered_ids(inter))


def test_a_fourth_ambassador_trade_is_refused(make_game, run):
    game = _game(make_game)
    game.gamestate["players"]["5"] = _player("white")
    blue = game.getPlayerObjectFromColor("blue")
    white = game.getPlayerObjectFromColor("white")
    # blue has spent all three of its ambassador tiles on red, green and yellow
    blue["reputation_track"] = ["amb-hydran-red", "amb-hydran-green", "amb-hydran-yellow", "mixed"]
    for color in ("red", "green", "yellow"):
        game.getPlayerObjectFromColor(color)["reputation_track"][0] = "amb-hydran-blue"
    before = list(white["reputation_track"])
    inter = FakeInteraction()

    run(DiplomaticRelationsButtons.acceptRelationsWith(game, blue, inter, "acceptRelationsWith_white"))

    assert white["reputation_track"] == before
    assert inter.followup.sent


def test_initiating_relations_with_nobody_says_so(make_game, run):
    game = _game(make_game)
    blue = game.getPlayerObjectFromColor("blue")
    inter = FakeInteraction()

    run(DiplomaticRelationsButtons.startDiplomaticRelations(game, blue, inter))

    content, kwargs = inter.channel.sent[-1]
    assert "nobody" in content
    assert kwargs.get("view") is None
