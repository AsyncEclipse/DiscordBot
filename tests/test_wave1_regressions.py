from Buttons.Population import PopulationButtons
from tests.fakes import FakeInteraction, buttons, player_stats, reload


def all_buttons(channel):
    return [c.custom_id for _content, kwargs in channel.sent
            for c in getattr(kwargs.get("view"), "children", [])]


def test_magellan_fourth_tech_ancient_labs_offers_both_discovery_tiles(start_game, press):
    game, channel = start_game(factions=["mag", "eri"])
    player = game.get_player(1)
    player["nano_tech"] = ["nar", "fud", "adr"]
    player["magDiscTileUsed"] = False
    player["science"] = 40
    game.gamestate["available_techs"] = ["anl"]
    game.update()
    home = game.getLocationFromID(player["home_planet"])

    press(channel, 1, "FCIDblue_startResearch")
    press(channel, 1, "FCIDblue_getTech_anl_nano")
    first = [c for c in all_buttons(channel) if "_keepDiscForPoints_" in c]
    assert first, "first discovery tile was not offered"
    press(channel, 1, first[-1])

    # Ancient Labs and the Magellan fourth-tech tile are two separate discovery tiles
    offers = [c for c in all_buttons(channel) if "_keepDiscForPoints_" in c]
    assert reload(game).gamestate["board"][home]["disctile"] == 0 or len(offers) > len(first), \
        "second discovery tile was left unresolved on the home sector"


def test_population_menu_with_25_empty_planets_does_not_overflow(run, monkeypatch):
    squares = [f"{300 + i}_money_0" for i in range(25)]
    monkeypatch.setattr(PopulationButtons, "findEmptyPopulation", staticmethod(lambda game, player: squares))
    interaction = FakeInteraction()

    run(PopulationButtons.startPopDrop(None, player_stats("hyd"), interaction))

    assert len(buttons(interaction.channel)) == 25
