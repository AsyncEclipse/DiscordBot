from discord.ui import View

from Buttons.Explore import ExploreButtons
from Buttons.Harvester import HarvesterButtons
from Buttons.Move import MoveButtons
from Buttons.Population import PopulationButtons
from Buttons.Upgrade import UpgradeButtons
from helpers.CombatHelper import Combat
from helpers.Turtugan import Harvester
from helpers.PlayerHelper import PlayerHelper
from helpers.ShipHelper import PlayerShip
from tests.fakes import (FakeChannel, FakeInteraction, board_tile, buttons, player_helper,
                         player_stats, reload)


def test_harvester_is_a_valid_starbase_but_a_normal_one_is_not():
    assert PlayerShip(player_stats("tur", color="teal"), "starbase").check_valid_ship()
    normal = player_stats("hyd", color="blue", starbase_parts=["hul", "nus", "nud"])
    assert not PlayerShip(normal, "starbase").check_valid_ship()


def test_only_turtugan_is_offered_the_starbase_in_a_move(start_game, press):
    game, channel = start_game(factions=["tur", "eri"])
    press(channel, 1, "FCIDblue_startMove")
    press(channel, 1, "FCIDblue_moveFrom_201_1")
    assert "Starbase (Range: 1)" in buttons(channel).values()

    game, channel = start_game(factions=["eri", "hyd"])
    press(channel, 1, "FCIDblue_startMove")
    press(channel, 1, "FCIDblue_moveFrom_201_1")
    assert "Starbase (Range: 1)" not in buttons(channel).values()


def test_turtugan_can_move_the_harvester_and_spends_influence(start_game, press):
    game, channel = start_game(factions=["tur", "eri"])
    game.add_tile("301", 0, "102")
    influence = game.get_player(1)["influence_discs"]
    press(channel, 1, "FCIDblue_startMove")
    press(channel, 1, "FCIDblue_moveFrom_201_1")
    press(channel, 1, "FCIDblue_moveThisShip_201_starbase_1_all")
    destination = next(cid for cid in buttons(channel) if cid.startswith("FCIDblue_moveTo_201_starbase_"))
    press(channel, 1, destination)

    state = reload(game)
    moved_to = destination.split("_")[4]
    assert "blue-sb" in state.gamestate["board"][moved_to]["player_ships"]
    assert "blue-sb" not in state.gamestate["board"]["201"]["player_ships"]
    assert state.get_player(1)["influence_discs"] == influence - 1
    assert state.get_player(1)["move_action_counters"] == 1


def test_free_harvester_move_only_offers_the_harvester(start_game, run, press):
    game, channel = start_game(factions=["tur", "eri"])
    game.add_tile("301", 0, "102")
    game.gamestate["board"]["201"]["player_ships"].append("blue-cru")
    game.update()
    view = View()
    ExploreButtons.addHarvesterMoveButton(game, game.get_player(1), view)
    run(channel.send("free move", view=view))

    press(channel, 1, "FCIDblue_startMoveHarvester")
    press(channel, 1, "FCIDblue_moveFrom_201_0_sb")

    labels = buttons(channel).values()
    assert "Starbase (Range: 1)" in labels
    assert "Cruiser (Range: 1)" not in labels


def test_pinned_harvester_does_not_consume_the_free_move(start_game, run):
    game, channel = start_game(factions=["tur", "eri"])
    game.gamestate["board"]["201"]["player_ships"].append("red-int")
    game.update()
    interaction = FakeInteraction(channel)

    run(MoveButtons.startHarvesterMove(game, game.get_player(1), interaction))

    assert "harvester_free_move_used" not in reload(game).get_player(1)
    assert "pinned" in interaction.followup.sent[0][0]


def test_the_explore_free_move_is_once_per_action(start_game, run, press):
    game, channel = start_game(factions=["tur", "eri"])
    game.add_tile("301", 0, "102")
    run(ExploreButtons.startExplore(game, game.get_player(1), player_helper(game, "blue"),
                                    FakeInteraction(channel), "startExplore"))
    influence = reload(game).get_player(1)["influence_discs"]
    view = View()
    ExploreButtons.addHarvesterMoveButton(game, reload(game).get_player(1), view)
    run(channel.send("free move", view=view))

    press(channel, 1, "FCIDblue_startMoveHarvester")
    press(channel, 1, "FCIDblue_moveFrom_201_0_sb")
    press(channel, 1, "FCIDblue_moveThisShip_201_starbase_0_sb")
    destination = next(cid for cid in buttons(channel) if cid.startswith("FCIDblue_moveTo_201_starbase_"))
    press(channel, 1, destination)

    state = reload(game)
    assert state.get_player(1)["influence_discs"] == influence
    assert state.get_player(1)["harvester_free_move_used"] is True

    view = View()
    ExploreButtons.addHarvesterMoveButton(game, reload(game).get_player(1), view)
    assert len(view.children) == 0
    from discord.ui import Button
    view = View()
    view.add_item(Button(label="Move Harvester (free)", custom_id="FCIDblue_startMoveHarvester"))
    run(channel.send("stale free move", view=view))
    press(channel, 1, "FCIDblue_startMoveHarvester")


def test_removing_one_of_two_harvesters_keeps_a_single_placement(make_game):
    player = player_stats("tur", color="teal")
    player["harvester_placements"] = [
        {"position": "201", "square": "money", "index": 0, "resource": "money"}]
    game = make_game({
        "player_count": 2,
        "players": {"1": player},
        "board": {"201": {"sector": "253", "orientation": 0, "owner": "teal",
                          "player_ships": ["teal-sb", "teal-sb"], "money_pop": [0]}},
    })

    game.remove_units(["teal-sb"], "201")

    assert game.get_player(1)["harvester_placements"] == [
        {"position": "201", "square": "money", "index": 0, "resource": "money"}]


def test_harvester_money_counts_before_bankruptcy(make_game):
    player = player_stats("tur", color="teal")
    player.update({
        "money": 0,
        "money_pop_cubes": 13,
        "influence_discs": 10,
        "harvester_placements": [
            {"position": "201", "square": "money", "index": 0, "resource": "money"}],
    })
    game = make_game({
        "roundNum": 1,
        "player_count": 2,
        "players": {"1": player},
        "board": {"201": {"sector": "253", "orientation": 0, "owner": "teal",
                          "player_ships": ["teal-sb"], "money_pop": [0]}},
    })
    helper = PlayerHelper(1, game.get_player(1))
    assert helper.checkBankrupt() is True

    Harvester.produce(game, helper.stats)

    assert helper.checkBankrupt() is False


def test_harvester_placement_stores_the_planet_and_produces_at_upkeep(start_game, press):
    game, channel = start_game(factions=["tur", "eri"])
    for player in game.gamestate["players"].values():
        player["passed"] = True
    game.update()
    press(channel, 1, "runUpkeep")
    offered = {button.custom_id for _content, kwargs in channel.sent
               for button in getattr(kwargs.get("view"), "children", [])}
    assert "FCIDblue_harvesterSector_201" not in offered
    assert "FCIDblue_placeHarvester_201_scienceadv_0_science" in offered
    press(channel, 1, "FCIDblue_placeHarvester_201_scienceadv_0_science")

    state = reload(game)
    assert state.get_player(1)["harvester_placements"] == [
        {"position": "201", "square": "scienceadv", "index": 0, "resource": "science"}]
    assert state.gamestate["board"]["201"]["scienceadv_pop"] == [0]
    assert state.get_player(1)["science_pop_cubes"] == 12

    science_before = state.get_player(1)["science"]
    science_income = state.get_player(1)["population_track"][state.get_player(1)["science_pop_cubes"] - 1]
    game = reload(game)
    press(channel, 1, "runUpkeep")
    assert reload(game).get_player(1)["science"] == science_before + science_income + 1


def test_harvester_blocks_settling_its_planet(start_game, press):
    game, channel = start_game(factions=["tur", "eri"])
    for player in game.gamestate["players"].values():
        player["passed"] = True
    game.update()
    press(channel, 1, "runUpkeep")
    game = reload(game)  # the press wrote its upkeep state to disk; edit that copy
    game.get_player(1)["nano_tech"].append("adl")
    game.update()
    press(channel, 1, "FCIDblue_placeHarvester_201_scienceadv_0_science")
    state = reload(game)
    assert "201_scienceadv_0" not in PopulationButtons.findEmptyPopulation(state, state.get_player(1))


def test_elimination_clears_the_harvester_placements(start_game, run):
    from Buttons.Influence import InfluenceButtons
    game, channel = start_game(factions=["tur", "eri"])
    player = game.get_player(1)
    assert Harvester.record(game, player, "201", "scienceadv", 0, "science")
    run(InfluenceButtons.eliminatePlayer(game, player, FakeInteraction(channel),
                                         player_helper(game, "blue"), False))
    assert player["harvester_placements"] == []


def test_moving_or_destroying_the_harvester_clears_its_placement(start_game):
    game, _channel = start_game(factions=["tur", "eri"])
    player = game.get_player(1)
    assert Harvester.record(game, player, "201", "scienceadv", 0, "science")
    assert player["harvester_placements"]
    game.remove_units(["blue-sb"], "201")
    assert player["harvester_placements"] == []


def test_a_second_placement_replaces_the_first_in_the_same_sector(start_game):
    game, _channel = start_game(factions=["tur", "eri"])
    player = game.get_player(1)
    assert Harvester.record(game, player, "201", "scienceadv", 0, "science")
    assert Harvester.record(game, player, "201", "materialadv", 0, "material")
    assert len(player["harvester_placements"]) == 1
    assert player["harvester_placements"][0]["square"] == "materialadv"


def test_a_grey_planet_asks_for_the_resource(make_game, run):
    stats = player_stats("tur", color="blue")
    stats["harvester_upkeep_started_round"] = 0  # this test skips upkeep, so its allocation is current
    game = make_game({"players": {"1": stats},
                      "board": {"202": dict(board_tile(["blue-sb"], sector=202)["202"],
                                            neutraladv_pop=[0])}})
    player = game.get_player(1)
    channel = FakeChannel("t-actions")
    interaction = FakeInteraction(channel)
    run(HarvesterButtons.place(game, player, interaction, "placeHarvester_202_neutraladv_0"))
    assert any(cid.endswith("_material") for cid in buttons(channel))
    choice = next(cid for cid in buttons(channel) if cid.endswith("_material"))
    handler_id = choice.replace("FCIDblue_", "")
    run(HarvesterButtons.placeResource(game, player, FakeInteraction(channel, custom_id=handler_id), handler_id))
    assert reload(game).get_player(1)["harvester_placements"][0]["resource"] == "material"


def test_a_lone_harvester_placement_is_resolved_without_a_prompt(make_game, run):
    stats = player_stats("tur", color="blue")
    stats["harvester_upkeep_started_round"] = 0  # this test skips upkeep, so its allocation is current
    game = make_game({"players": {"1": stats},
                      "board": {"202": dict(board_tile(["blue-sb"], sector=202)["202"],
                                            money_pop=[0])}})
    channel = FakeChannel("t-actions")
    run(HarvesterButtons.startPlace(game, game.get_player(1), FakeInteraction(channel)))

    assert all(kwargs.get("view") is None for _content, kwargs in channel.sent)
    player = reload(game).get_player(1)
    assert player["harvester_placements"] == [
        {"position": "202", "square": "money", "index": 0, "resource": "money"}]
    assert player["harvester_upkeep_allocated_round"] == 0


def test_harvester_can_replace_its_drive_with_another_drive(start_game, press):
    game, channel = start_game(factions=["tur", "eri"])
    game.get_player(1)["grid_tech"].append("tad")
    game.update()

    press(channel, 1, "FCIDblue_startUpgrade")
    press(channel, 1, "FCIDblue_upgradeShip_2_starbase_dummy")
    inter = press(channel, 1, "FCIDblue_selectOldPart_2_starbase_nud_dummy_2")

    labels = {child.label for child in inter.message.edited["view"].children}
    assert "Nuclear Drive" in labels
    assert "Tachyon Drive" in labels
    assert "Hull" not in labels and "Empty" not in labels

    press(channel, 1, "FCIDblue_chooseUpgrade_2_starbase_nud_tad_2_dummy")
    assert reload(game).get_player(1)["starbase_parts"][2] == "tad"


def test_forged_drive_removal_is_refused(start_game, run):
    game, _channel = start_game(factions=["tur", "eri"])
    interaction = FakeInteraction()
    run(UpgradeButtons.chooseUpgrade(game, game.get_player(1), interaction,
                                     "chooseUpgrade_2_starbase_nud_empty_2_dummy",
                                     player_helper(game, "blue")))
    assert "must keep a Drive" in interaction.followup.sent[0][0]


def test_a_weaponless_harvester_is_not_in_the_roll_order(make_game):
    stats = player_stats("tur", color="teal")
    other = player_stats("eri", color="red")
    game = make_game({"players": {"1": stats, "2": other},
                      "board": {"202": dict(board_tile(["teal-sb", "red-int"], sector=202)["202"],
                                            attacker=["teal"], defender=["red"])}})
    speeds = Combat.getBothCombatantShipsBySpeed(game, ["red"], ["teal"],
                                                 game.gamestate["board"]["202"]["player_ships"], "202")
    assert all(owner != "teal" for _speed, owner in speeds)
    assert any(ship[1] == "sb" for ship in Combat.getCombatantShipsBySpeed(
        game, "teal", game.gamestate["board"]["202"]["player_ships"], "202"))
