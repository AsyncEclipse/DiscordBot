from Buttons.Explore import ExploreButtons
from helpers.Turtugan import DeepSpace
from tests.fakes import FakeInteraction, buttons, player_stats, reload


def ring_three_position(game, player):
    return next(position for position in ExploreButtons.getTilesToExplore(game, player)
                if position.startswith("3"))


def offer_reserved_choice(press, channel, position):
    press(channel, 1, "FCIDblue_startExplore")
    press(channel, 1, f"FCIDblue_exploreTile_{position}")
    return next(cid for cid in buttons(channel)
                if cid.startswith(f"FCIDblue_reservedTile_{position}_")
                and "_random_" not in cid)


def test_setup_reserves_two_sectors_without_taking_them_from_the_deck(start_game):
    game, _channel = start_game(factions=["tur", "eri"])
    player = game.get_player(1)
    reserve = player["deep_space_sectors"]
    assert len(reserve) == 2
    # the sectors come from the ones the game did not deal into the deck
    assert not set(reserve) & set(game.gamestate["tile_deck_300"])
    assert not DeepSpace.has_reserve(game.get_player(2))


def test_setup_keeps_the_reserve_off_the_map(start_game):
    game, unused_channel = start_game(factions=["tur", "eri"])
    assert "deep_space_positions" not in game.get_player(1)
    assert all("deep_space" not in tile for tile in game.gamestate["board"].values())


def test_reserved_sector_is_offered_on_a_ring_three_position(start_game, press):
    game, channel = start_game(factions=["tur", "eri"])
    player = game.get_player(1)
    position = ring_three_position(game, player)

    press(channel, 1, "FCIDblue_startExplore")
    press(channel, 1, f"FCIDblue_exploreTile_{position}")
    ids = buttons(channel)
    assert any(cid.startswith(f"FCIDblue_reservedTile_{position}_") and "_random_" not in cid
               for cid in ids)
    assert any("_random_" in cid for cid in ids)
    assert list(ids.values()).count("Draw from Reserve") == 1
    assert any("Deep Space Explorers" in content and "2 in reserve" in content
               for content, _kwargs in channel.sent)
    assert all(tile not in " ".join(ids.values()) for tile in player["deep_space_sectors"])


def test_ring_one_and_two_positions_only_draw(start_game, press):
    game, channel = start_game(factions=["tur", "eri"])
    game.gamestate["tile_deck_100"] = ["102"]
    game.update()
    press(channel, 1, "FCIDblue_startExplore")
    press(channel, 1, "FCIDblue_exploreTile_101")
    assert not any("reservedTile" in cid for cid in buttons(channel))


def test_choosing_a_reserved_sector_places_it_without_drawing(start_game, press):
    game, channel = start_game(factions=["tur", "eri"])
    player = game.get_player(1)
    reserve_before = list(player["deep_space_sectors"])
    deck_before = list(game.gamestate["tile_deck_300"])
    position = ring_three_position(game, player)

    choice = offer_reserved_choice(press, channel, position)
    tile = game.get_player(1)["deep_space_sectors"][0]
    press(channel, 1, choice)
    assert any("Drawn from the Deep Space Explorers reserve" in content
               for content, _kwargs in channel.sent)
    state = reload(game)
    assert state.get_player(1)["deep_space_sectors"] == [x for x in reserve_before if x != tile]
    placement = next(cid for cid in buttons(channel)
                     if cid.startswith(f"FCIDblue_placeTile_{position}_{tile}_"))
    press(channel, 1, placement)

    state = reload(game)
    assert state.gamestate["board"][position]["sector"] == tile
    assert state.get_player(1)["deep_space_sectors"] == [x for x in reserve_before if x != tile]
    assert state.gamestate["tile_deck_300"] == deck_before


def test_a_deck_empty_outer_rim_still_offers_and_places_the_reserve(start_game, run, press):
    game, channel = start_game(factions=["tur", "eri"])
    player = game.get_player(1)
    game.gamestate["tile_deck_300"] = []
    game.gamestate["tile_discard_deck_300"] = []
    game.update()
    assert ring_three_position(game, player)

    choice = offer_reserved_choice(press, channel, "301")
    tile = game.get_player(1)["deep_space_sectors"][0]
    assert not any("_random_" in cid for cid in buttons(channel))
    press(channel, 1, choice)
    placement = next(cid for cid in buttons(channel)
                     if cid.startswith(f"FCIDblue_placeTile_301_{tile}_"))
    press(channel, 1, placement)
    state = reload(game)
    assert state.gamestate["board"]["301"]["sector"] == tile
    assert len(state.get_player(1)["deep_space_sectors"]) == 1
    # the cleanup keeps the remaining outer-rim positions alive for the held sector
    run(game.updateNamesAndOutRimTiles(FakeInteraction(channel)))
    assert reload(game).gamestate["board"]["303"]["sector"] == "sector3back"


def test_outer_rim_cleanup_can_run_once_the_reserve_is_empty(make_game):
    stats = {"name": "Turtugan", "artwork": "turtugan", "color": "blue",
             "home_planet": "253", "player_name": "blue", "deep_space_sectors": []}
    game = make_game({"players": {"1": stats},
                      "board": {"303": {"sector": "sector3back"}},
                      "tile_deck_300": [], "tile_discard_deck_300": []})
    assert not DeepSpace.keep_outer_rim(game)
    game.gamestate["players"]["1"]["deep_space_sectors"] = ["301"]
    assert DeepSpace.keep_outer_rim(game)


def test_double_press_does_not_remove_two_reserved_sectors(make_game, run, monkeypatch):

    async def no_placement(*args, **kwargs):
        return None

    monkeypatch.setattr(ExploreButtons, "showExploredTile", no_placement)
    stats = {"name": "Turtugan", "artwork": "turtugan", "color": "blue", "home_planet": "253",
             "player_name": "blue", "deep_space_sectors": ["301", "302"],
             "deep_space_choice": None, "deep_space_choice_token": 0,
             "owned_tiles": ["201"]}
    game = make_game({"players": {"1": stats},
                      "board": {"201": {"sector": "253", "orientation": 0, "player_ships": [],
                                        "owner": "blue", "wormholes": [0, 1, 3, 4]},
                                "301": {"sector": "sector3back", "orientation": 0, "player_ships": []}},
                      "tile_deck_300": ["303"], "player_count": 2})
    player = game.get_player(1)
    channel = FakeInteraction().channel
    run(DeepSpace.offer(game, player, FakeInteraction(channel), "301"))
    choice = next(cid for cid in buttons(channel) if "reservedTile_301_reserve_" in cid)
    handler_id = choice.replace("FCIDblue_", "")
    run(ExploreButtons.reservedTile(game, player, FakeInteraction(channel, custom_id=handler_id), handler_id))
    run(ExploreButtons.reservedTile(game, reload(game).get_player(1),
                                    FakeInteraction(channel, custom_id=handler_id), handler_id))
    assert reload(game).get_player(1)["deep_space_sectors"] == ["302"]


def test_a_short_deck_takes_what_is_available(make_game):
    stats = {"name": "Turtugan", "artwork": "turtugan", "color": "blue", "home_planet": "253",
             "player_name": "blue"}
    game = make_game({"players": {"1": stats},
                      "board": {"201": {"sector": "253", "orientation": 0, "player_ships": []}},
                      "tile_deck_300": ["301"], "sector3_spare": ["302"]})
    game.setup_finished()
    assert game.get_player(1)["deep_space_sectors"] == ["302"]


def test_reserve_can_reach_and_explore_505_after_the_normal_supply_runs_out(start_game, run, press):
    game, channel = start_game(factions=["tur", "eri"])
    player = game.get_player(1)
    reserve = list(player["deep_space_sectors"])
    game.gamestate["tile_deck_300"] = []
    game.gamestate["tile_discard_deck_300"] = []
    game.add_tile("404", 0, "301", "blue")
    game.gamestate["board"]["404"]["wormholes"] = list(range(6))
    game.update()
    run(game.updateNamesAndOutRimTiles(FakeInteraction(channel)))
    assert "505" in ExploreButtons.getTilesToExplore(game, game.get_player(1))
    assert "505" not in ExploreButtons.getTilesToExplore(game, game.get_player(2))

    choice = offer_reserved_choice(press, channel, "505")
    tile = game.get_player(1)["deep_space_sectors"][0]
    assert not any("_random_" in cid for cid in buttons(channel))
    press(channel, 1, choice)
    placement = next(cid for cid in buttons(channel)
                     if cid.startswith(f"FCIDblue_placeTile_505_{tile}_"))
    press(channel, 1, placement)
    state = reload(game)
    assert state.gamestate["board"]["505"]["sector"] == tile
    assert state.get_player(1)["deep_space_sectors"] == [value for value in reserve if value != tile]
    assert state.gamestate["board"]["605"]["sector"] == "sector3back"
    assert state.gamestate["tile_deck_300"] == []


def test_drawing_from_the_normal_stack_keeps_the_reserve(start_game, press):
    game, channel = start_game(factions=["tur", "eri"])
    player = game.get_player(1)
    reserve = list(player["deep_space_sectors"])
    deck = list(game.gamestate["tile_deck_300"])
    position = ring_three_position(game, player)
    offer_reserved_choice(press, channel, position)
    choice = next(cid for cid in buttons(channel) if "_random_" in cid)
    press(channel, 1, choice)
    assert any("Drawn from the Deep Space Explorers reserve" in content
               for content, _kwargs in channel.sent)
    state = reload(game)
    assert state.get_player(1)["deep_space_sectors"] == reserve
    assert len(state.gamestate["tile_deck_300"]) == len(deck) - 1


def test_empty_random_draw_keeps_reserve_choice_available(make_game):
    player = {"deep_space_choice": "301", "deep_space_choice_token": 1,
              "deep_space_sectors": ["302"]}
    game = make_game({"players": {"1": player}, "tile_deck_300": [],
                      "tile_discard_deck_300": []})
    player = game.get_player(1)
    assert DeepSpace.take(game, player, "301", "random", 1) == (None, "empty")
    assert DeepSpace.take(game, player, "301", "reserve", 1) == ("302", None)


def test_legacy_save_can_supply_deep_space_reserve(make_game):
    game = make_game({"players": {"1": player_stats("tur")},
                      "tile_deck_300": ["301"], "tile_discard_deck_300": []})
    DeepSpace.draw_reserve(game, game.get_player(1))
    assert DeepSpace.has_reserve(game.get_player(1))
    assert "301" not in game.get_player(1)["deep_space_sectors"]
    assert game.gamestate["tile_deck_300"] == ["301"]
