"""Heralds of Ragnarok species rules: Raid, Regroup, the alternate blueprints and the
starting cruiser.

Raid reuses the existing Build flow from a Move action; Regroup reuses the existing
Move flow from a Build action. Both are one extra activation of the other type, once
per action, and never a second influence disc.
"""
from Buttons.Move import MoveButtons
from helpers.DrawHelper import DrawHelper
from helpers.ShipHelper import PlayerShip
from tests.fakes import FakeInteraction, buttons, player_stats, reload


def setup_game(start_game):
    game, channel = start_game(factions=["her", "eri"])
    # Two free ring-1 sectors, both valid destinations from the home sector.
    for tile, orientation in (("301", 0), ("302", 60)):
        game.add_tile(tile, orientation, "202")
    game.get_player(1)["materials"] = 8
    game.update()
    return game, channel


def edited_menu(interaction):
    return {child.custom_id: child.label for child in interaction.message.edited["view"].children}


def press_edited(press, channel, interaction, prefix):
    custom_id = next(cid for cid in edited_menu(interaction) if cid.startswith(prefix))
    return press(channel, 1, custom_id, interaction.message)


def move_cruiser(press, channel, origin="201", destination="301", move_count="1", suffix=""):
    press(channel, 1, next(cid for cid in buttons(channel)
                           if cid.startswith(f"FCIDblue_moveFrom_{origin}_{move_count}") and suffix in cid))
    press(channel, 1, next(cid for cid in buttons(channel)
                           if "moveThisShip" in cid and "cruiser" in cid and suffix in cid))
    return press(channel, 1, next(cid for cid in buttons(channel)
                                  if f"moveTo_{origin}_cruiser_{destination}_{move_count}" in cid
                                  and suffix in cid))


def finish_raid_build(press, channel, move_count=1):
    press(channel, 1, f"FCIDblue_herRaidBuild_{move_count}")
    press(channel, 1, f"FCIDblue_buildIn_201_herRaid_{move_count}")
    inter = press(channel, 1, next(cid for cid in buttons(channel)
                                   if cid.startswith("FCIDblue_buildShip_") and "Interceptor" in cid))
    inter = press_edited(press, channel, inter, "FCIDblue_finishBuild_")
    spend = buttons(channel)
    inter = press(channel, 1, next(cid for cid in spend if cid.startswith("FCIDblue_spendMaterial_")))
    inter = press_edited(press, channel, inter, "FCIDblue_finishSpendForBuild_")
    return inter


def finish_standard_build(press, channel, ship="Interceptor"):
    press(channel, 1, "FCIDblue_buildIn_201")
    inter = press(channel, 1, next(cid for cid in buttons(channel)
                                   if cid.startswith("FCIDblue_buildShip_") and ship in cid))
    inter = press_edited(press, channel, inter, "FCIDblue_finishBuild_")
    spend = buttons(channel)
    inter = press(channel, 1, next(cid for cid in spend if cid.startswith("FCIDblue_spendMaterial_")))
    return press_edited(press, channel, inter, "FCIDblue_finishSpendForBuild_")


# --- Raid --------------------------------------------------------------------

def test_back_from_raid_after_last_move_cannot_start_a_third_move(start_game, press, run):
    game, channel = setup_game(start_game)
    player = game.get_player(1)
    player["move_apt"] = 2
    game.update()
    run(MoveButtons.sendMoveContinuation(player, FakeInteraction(channel), 2))
    press(channel, 1, "FCIDblue_herRaidBuild_3")
    press(channel, 1, "FCIDblue_herBackToMove_3")

    choices = buttons(channel)
    assert "FCIDblue_finishAction" in choices
    assert not any("moveFrom" in cid or "startMove" in cid for cid in choices)


def test_the_player_area_prints_the_raid_and_regroup_annotations():
    """The info sheet prints +1 MOV under the build count and +1 BUI under the move count."""
    heralds = player_stats("her", color="red")
    assert DrawHelper.action_annotation(heralds, "build") == "+1 MOV"
    assert DrawHelper.action_annotation(heralds, "move") == "+1 BUI"
    assert DrawHelper.action_annotation(heralds, "influence") is None

    other = player_stats("hyd", color="blue")
    assert DrawHelper.action_annotation(other, "build") is None
    assert DrawHelper.action_annotation(other, "move") is None


def test_raid_build_before_the_move_spends_one_disc_and_returns_to_move(start_game, press):
    game, channel = setup_game(start_game)
    press(channel, 1, "FCIDblue_startMove")
    assert "FCIDblue_herRaidBuild_1" in buttons(channel)
    assert any("Raid: this Move action also includes one Build activation" in content
               for content, _kwargs in channel.sent)

    press(channel, 1, "FCIDblue_herRaidBuild_1")
    chooser = buttons(channel)
    assert "FCIDblue_buildIn_201_herRaid_1" in chooser
    assert not [cid for cid in chooser if "herRegroupMove" in cid]

    press(channel, 1, "FCIDblue_buildIn_201_herRaid_1")
    assert any("up to 1 units" in content for content, _kwargs in channel.sent)

    finish_raid_build(press, channel)
    state = reload(game)
    player = state.get_player(1)
    assert player["materials"] == 4
    assert player["influence_discs"] == 11
    assert player["move_action_counters"] == 1
    assert player["build_action_counters"] == 0
    assert player["herCrossUsed"] is True
    assert player["herRaidCharged"] is True
    assert "blue-int" in state.gamestate["board"]["201"]["player_ships"]
    # Back on the Move chooser with the first move still available, and no second Raid build.
    menu = buttons(channel)
    assert "FCIDblue_moveFrom_201_1" in menu
    assert not [cid for cid in menu if "herRaidBuild" in cid]

    move_cruiser(press, channel)
    state = reload(game)
    player = state.get_player(1)
    assert player["influence_discs"] == 11
    assert player["move_action_counters"] == 1
    assert not player.get("herRaidCharged")
    assert "Moved a cruiser" in player["detailsOflastAction"]
    assert "Built" in player["detailsOflastAction"]


def test_raid_build_after_the_move_does_not_spend_a_second_disc(start_game, press):
    game, channel = setup_game(start_game)
    press(channel, 1, "FCIDblue_startMove")
    move_cruiser(press, channel)
    assert "FCIDblue_herRaidBuild_2" in buttons(channel)

    press(channel, 1, "FCIDblue_herRaidBuild_2")
    press(channel, 1, "FCIDblue_buildIn_201_herRaid_2")
    inter = press(channel, 1, next(cid for cid in buttons(channel)
                                   if cid.startswith("FCIDblue_buildShip_") and "Interceptor" in cid))
    inter = press_edited(press, channel, inter, "FCIDblue_finishBuild_")
    spend = buttons(channel)
    inter = press(channel, 1, next(cid for cid in spend if cid.startswith("FCIDblue_spendMaterial_")))
    press_edited(press, channel, inter, "FCIDblue_finishSpendForBuild_")

    state = reload(game)
    player = state.get_player(1)
    assert player["influence_discs"] == 11
    assert player["move_action_counters"] == 1
    assert player["build_action_counters"] == 0
    assert player["herCrossUsed"] is True
    assert "blue-int" in state.gamestate["board"]["201"]["player_ships"]
    # The second move is still available and Raid is used up.
    menu = buttons(channel)
    assert "FCIDblue_moveFrom_301_2" in menu
    assert "FCIDblue_finishAction" in menu
    assert not [cid for cid in menu if "herRaidBuild" in cid]
    view = next(kwargs["view"] for content, kwargs in reversed(channel.sent)
                if "Select the tile you would like to move from" in (content or ""))
    ids = [child.custom_id for child in view.children]
    assert ids.count("FCIDblue_finishAction") == 1
    assert len(ids) == len(set(ids))


def test_raid_nested_build_allows_only_one_unit(start_game, press):
    game, channel = setup_game(start_game)
    press(channel, 1, "FCIDblue_startMove")
    press(channel, 1, "FCIDblue_herRaidBuild_1")
    press(channel, 1, "FCIDblue_buildIn_201_herRaid_1")
    first = press(channel, 1, next(cid for cid in buttons(channel)
                                   if cid.startswith("FCIDblue_buildShip_") and "Interceptor" in cid))
    menu = edited_menu(first)
    second = press_edited(press, channel, first, "FCIDblue_buildShip_")
    assert "cannot build any more units" in second.message.edited["content"]
    assert "FCIDblue_finishBuild_blue-int_4_201_herRaid_1" in menu


def test_raid_double_press_builds_only_one_unit(start_game, press):
    game, channel = setup_game(start_game)
    press(channel, 1, "FCIDblue_startMove")
    press(channel, 1, "FCIDblue_herRaidBuild_1")
    press(channel, 1, "FCIDblue_buildIn_201_herRaid_1")
    inter = press(channel, 1, next(cid for cid in buttons(channel)
                                   if cid.startswith("FCIDblue_buildShip_") and "Interceptor" in cid))
    inter = press_edited(press, channel, inter, "FCIDblue_finishBuild_")
    spend = buttons(channel)
    inter = press(channel, 1, next(cid for cid in spend if cid.startswith("FCIDblue_spendMaterial_")))
    finish = next(cid for cid in edited_menu(inter) if cid.startswith("FCIDblue_finishSpendForBuild_"))
    message = inter.message
    press(channel, 1, finish, message)
    press(channel, 1, finish, message)

    state = reload(game)
    assert state.gamestate["board"]["201"]["player_ships"].count("blue-int") == 1
    assert state.get_player(1)["ship_stock"][0] == 7


# --- Regroup -----------------------------------------------------------------

def test_regroup_move_before_building_spends_one_disc_and_returns_to_build(start_game, press):
    game, channel = setup_game(start_game)
    press(channel, 1, "FCIDblue_startBuild")
    assert "FCIDblue_herRegroupMove_before" in buttons(channel)
    assert any("Regroup: this Build action also includes one Move activation" in content
               for content, _kwargs in channel.sent)

    press(channel, 1, "FCIDblue_herRegroupMove_before")
    menu = buttons(channel)
    assert "FCIDblue_moveFrom_201_1_herRegroup_before" in menu
    assert not [cid for cid in menu if "herRaidBuild" in cid]
    assert "FCIDblue_herBackToBuild" in menu
    assert not any("startMove" in cid or "additional" in cid for cid in menu)

    move_cruiser(press, channel, suffix="_herRegroup_before")
    state = reload(game)
    player = state.get_player(1)
    assert player["influence_discs"] == 11
    assert player["build_action_counters"] == 1
    assert player["move_action_counters"] == 0
    assert player["herCrossUsed"] is True
    assert "blue-cru" in state.gamestate["board"]["301"]["player_ships"]
    # Back at the Build tile chooser, and the Regroup move is used up.
    menu = buttons(channel)
    assert "FCIDblue_buildIn_201" in menu
    assert not [cid for cid in menu if "herRegroupMove" in cid]

    finish_standard_build(press, channel)
    state = reload(game)
    player = state.get_player(1)
    assert player["influence_discs"] == 11
    assert player["build_action_counters"] == 1
    assert player["move_action_counters"] == 0
    assert "blue-int" in state.gamestate["board"]["201"]["player_ships"]


def test_regroup_move_never_announces_raid(start_game, press):
    game, channel = setup_game(start_game)
    press(channel, 1, "FCIDblue_startBuild")
    before = len(channel.sent)
    press(channel, 1, "FCIDblue_herRegroupMove_before")

    contents = [content for content, _kwargs in channel.sent[before:] if content]
    assert not any("Raid" in content for content in contents)
    assert "FCIDblue_moveFrom_201_1_herRegroup_before" in buttons(channel)


def test_regroup_move_after_building_returns_to_the_build_screen(start_game, press):
    game, channel = setup_game(start_game)
    press(channel, 1, "FCIDblue_startBuild")
    finish_standard_build(press, channel)
    menu = buttons(channel)
    assert "FCIDblue_herRegroupMove_after" in menu
    assert "FCIDblue_finishAction" in menu

    press(channel, 1, "FCIDblue_herRegroupMove_after")
    move_cruiser(press, channel, suffix="_herRegroup_after")
    state = reload(game)
    player = state.get_player(1)
    assert player["influence_discs"] == 11
    assert player["build_action_counters"] == 1
    assert player["move_action_counters"] == 0
    assert player["herCrossUsed"] is True
    # The move is an addition to the Build action, so its second activation is still there.
    menu = buttons(channel)
    assert "FCIDblue_buildIn_201" in menu
    assert "FCIDblue_finishAction" in menu
    assert not [cid for cid in menu if "herRegroupMove" in cid]

    finish_standard_build(press, channel)
    state = reload(game)
    player = state.get_player(1)
    assert player["materials"] == 0
    assert player["buildsThisAction"] == 2
    assert state.gamestate["board"]["201"]["player_ships"].count("blue-int") == 2
    assert "startBuild2_deleteMsg" not in buttons(channel)


def test_back_to_build_does_not_use_the_regroup_activation(start_game, press):
    game, channel = setup_game(start_game)
    press(channel, 1, "FCIDblue_startBuild")
    press(channel, 1, "FCIDblue_herRegroupMove_before")
    press(channel, 1, "FCIDblue_herBackToBuild")
    state = reload(game)
    player = state.get_player(1)
    assert player["influence_discs"] == 11
    assert player["build_action_counters"] == 1
    assert player["move_action_counters"] == 0
    assert player.get("herCrossUsed") is not True
    assert "FCIDblue_herRegroupMove_before" in buttons(channel)


# --- Reactions ---------------------------------------------------------------

def test_reactions_do_not_offer_the_other_activation(start_game, press):
    game, channel = setup_game(start_game)
    game.get_player(1)["passed"] = True
    game.update()

    press(channel, 1, "FCIDblue_startMove")
    assert not [cid for cid in buttons(channel) if "herRaidBuild" in cid]
    press(channel, 1, "FCIDblue_startBuild")
    assert "FCIDblue_herRegroupMove_before" not in buttons(channel)


# --- Influence and action summary ---------------------------------------------

def test_raid_uses_one_disc_and_upkeep_returns_it(start_game, press):
    game, channel = setup_game(start_game)
    press(channel, 1, "FCIDblue_startMove")
    finish_raid_build(press, channel)
    move_cruiser(press, channel)

    state = reload(game)
    player = state.get_player(1)
    assert player["influence_discs"] == 11
    assert player["lastAction"] == "move"
    assert "Built" in player["detailsOflastAction"]
    assert "Moved a cruiser" in player["detailsOflastAction"]

    from helpers.PlayerHelper import PlayerHelper
    helper = PlayerHelper(state.get_player_from_color("blue"), player)
    helper.upkeep()
    state.update_player(helper)
    player = reload(state).get_player(1)
    assert player["influence_discs"] == 12
    assert player["move_action_counters"] == 0
    assert player["build_action_counters"] == 0


# --- Blueprints ---------------------------------------------------------------

def test_blueprint_menus_offer_every_printed_slot(start_game, press):
    game, channel = setup_game(start_game)
    press(channel, 1, "FCIDblue_startUpgrade")
    inter = press(channel, 1, next(cid for cid in buttons(channel)
                                   if cid.startswith("FCIDblue_upgradeShip_") and "interceptor" in cid))
    assert len(inter.message.edited["view"].children) == 5 + 1  # five parts plus "Choose Different Ship"

    inter = press_edited(press, channel, inter, "FCIDblue_chooseDifferentShip_")
    inter = press(channel, 1, next(cid for cid in buttons(channel)
                                   if cid.startswith("FCIDblue_upgradeShip_") and "cruiser" in cid))
    assert len(inter.message.edited["view"].children) == 5 + 1


def test_the_extra_interceptor_hull_is_a_replaceable_slot(start_game, press):
    game, channel = setup_game(start_game)
    press(channel, 1, "FCIDblue_startUpgrade")
    inter = press(channel, 1, next(cid for cid in buttons(channel)
                                   if cid.startswith("FCIDblue_upgradeShip_") and "interceptor" in cid))
    inter = press(channel, 1, next(cid for cid in edited_menu(inter)
                                   if cid.startswith("FCIDblue_selectOldPart_2_interceptor_hul_")))
    part_buttons = edited_menu(inter)
    choice = next(cid for cid in part_buttons if "_interceptor_hul_elc_3_" in cid)
    press(channel, 1, choice, inter.message)

    player = reload(game).get_player(1)
    assert player["interceptor_parts"] == ["ioc", "nus", "nud", "elc", "empty"]
    model = PlayerShip(player, "interceptor")
    assert model.hull == 0 and model.computer == 1 and model.check_valid_ship()


def test_a_build_action_builds_at_most_its_two_activation_units(start_game, press):
    game, channel = setup_game(start_game)
    player = game.get_player(1)
    assert player["ship_stock"][1] == 3
    assert game.gamestate["board"]["201"]["player_ships"] == ["blue-cru"]
    player["materials"] = 100
    game.update()

    press(channel, 1, "FCIDblue_startBuild")
    # Two cruisers: both Build activations.
    press(channel, 1, "FCIDblue_buildIn_201")
    inter = press(channel, 1, next(cid for cid in buttons(channel)
                                   if cid.startswith("FCIDblue_buildShip_") and "Cruiser" in cid))
    second = next(cid for cid in edited_menu(inter)
                  if cid.startswith("FCIDblue_buildShip_") and "Cruiser" in cid)
    inter = press(channel, 1, second, inter.message)
    inter = press_edited(press, channel, inter, "FCIDblue_finishBuild_")
    spend = buttons(channel)
    inter = press(channel, 1, next(cid for cid in spend if cid.startswith("FCIDblue_spendMaterial_")))
    press_edited(press, channel, inter, "FCIDblue_finishSpendForBuild_")

    # No Build activation is left, so Build Somewhere Else cannot add a third unit.
    assert "startBuild2_deleteMsg" not in buttons(channel)
    state = reload(game)
    assert state.get_player(1)["buildsThisAction"] == 2
    assert state.get_player(1)["ship_stock"][1] == 1


def test_a_pulsar_move_does_not_offer_a_raid_build(start_game, run):
    game, channel = setup_game(start_game)
    player = game.get_player(1)
    player["pulsarMove"] = True
    game.update()

    run(MoveButtons.startMove(game, player, FakeInteraction(channel), "startMove_2", False))

    assert not [cid for cid in buttons(channel) if "herRaidBuild" in cid]


def test_a_normal_move_clears_the_pulsar_flag(start_game, press):
    game, channel = setup_game(start_game)
    game.get_player(1)["pulsarMove"] = True
    game.update()

    press(channel, 1, "FCIDblue_startMove")

    assert "FCIDblue_herRaidBuild_1" in buttons(channel)
