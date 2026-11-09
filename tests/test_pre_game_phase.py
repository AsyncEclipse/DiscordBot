"""The pre-game phase: the factions that have something to do before the game starts
do it now, and the first turn waits for them.
"""
import json
import random
from types import SimpleNamespace

import pytest

from Buttons.Draft import DraftButtons
from Buttons.PreGame import PreGameButtons
from commands.game_commands import GameCommands
from commands.player_commands import PlayerCommands
from helpers.GamestateHelper import GamestateHelper
from setup.GameInit import GameInit
from tests.fakes import FakeChannel, FakeInteraction, buttons, player_stats, reload


def find_button(channel, prefix):
    return next(
        button.custom_id
        for content, kwargs in reversed(channel.sent)
        for button in getattr(kwargs.get("view"), "children", [])
        if button.custom_id.startswith(prefix)
    )


def test_turtugan_harvester_is_not_a_pre_game_task():
    assert "harvester" not in PreGameButtons.tasksForPlayer(player_stats("tur"))


def start_pre_game(games_dir, run, discovery_tiles=None):
    """A four player game with the four factions that act before the game starts."""
    random.seed(0)

    GameInit("Pre game phase", [[1, "<@1>"], [2, "<@2>"], [3, "<@3>"], [4, "<@4>"]],
             "def", True, True, False, False, community_factions=True).create_game()
    game = GamestateHelper(None, "aeb1")
    game.setup_techs_and_outer_rim(4, False, False)
    game.gamestate["discTiles"] = (discovery_tiles if discovery_tiles is not None
                                   else ["mog", "sci", "mat", "cru", "mog", "sci"])
    game.gamestate["tile_deck_100"] = ["102", "103", "106", "108"]
    game.update()
    channel = FakeChannel("aeb1-actions")
    interaction = FakeInteraction(channel, role_names=["aeb1"])
    run(DraftButtons.generalSetup(interaction, game, [1, 2, 3, 4], ["exl", "atl", "ra", "tm"]))
    return game, channel


def test_the_first_turn_waits_for_every_pre_game_action(games_dir, run, press):
    game, channel = start_pre_game(games_dir, run)

    state = reload(game).gamestate
    assert state["pre_game"]["tasks"] == [["1", "orbital_pop"], ["2", "discovery_tile"],
                                          ["3", "artifact_cube"], ["4", "setup_tech"]]
    # nobody has taken a turn yet
    assert "activePlayerColor" not in state

    # The Exiles put a population cube on the Orbital in their starting sector.
    press(channel, 1, find_button(channel, "FCIDteal_preGameOrbital_"))
    state = reload(game).gamestate
    assert state["board"]["201"]["orbital_pop"] == [1]
    assert state["players"]["1"]["colony_ships"] == 3
    assert state["pre_game"]["tasks"] == [["2", "discovery_tile"], ["3", "artifact_cube"],
                                          ["4", "setup_tech"]]
    assert "activePlayerColor" not in state

    # Remnants of Ra put a cube on the disc of their artifact sector.
    press(channel, 3, find_button(channel, "FCIDyellow_ancientsCube_"))
    assert reload(game).gamestate["board"]["207"]["disc_pop"] == [1]
    assert "activePlayerColor" not in reload(game).gamestate

    # The Atlantians resolve one of the two discovery tiles they drew.
    press(channel, 2, find_button(channel, "FCIDblue_selectDiscTile_"))
    press(channel, 2, find_button(channel, "FCIDblue_keepDiscForPoints"))
    assert reload(game).get_player(2)["disc_tiles_for_points"] == 1
    assert "activePlayerColor" not in reload(game).gamestate

    # The Techno-Mages may pass on their technology, which lets the game start.
    press(channel, 4, find_button(channel, "FCIDpurple_declineSetupTech"))
    state = reload(game).gamestate
    assert state["pre_game"]["tasks"] == []
    assert state["activePlayerColor"] == ["teal"]


def test_the_techno_mages_may_buy_their_technology_before_the_game_starts(games_dir, run, press):
    game, channel = start_pre_game(games_dir, run)

    press(channel, 4, "FCIDpurple_setupTech")
    press(channel, 4, next(cid for cid in buttons(channel) if cid.startswith("FCIDpurple_getTech_")))
    # the technology is bought, but the game still waits for the other factions
    assert reload(game).get_player(4)["military_tech"]
    assert len(reload(game).gamestate["pre_game"]["tasks"]) == 3

    press(channel, 1, find_button(channel, "FCIDteal_preGameOrbital_"))
    press(channel, 3, find_button(channel, "FCIDyellow_ancientsCube_"))
    press(channel, 2, find_button(channel, "FCIDblue_selectDiscTile_"))
    press(channel, 2, find_button(channel, "FCIDblue_keepDiscForPoints"))
    assert reload(game).gamestate["activePlayerColor"] == ["teal"]


def test_a_turn_cannot_be_restarted_before_the_game_starts(games_dir, run, press):
    """The turn menus offer a restart, but there is no turn to go back to yet."""
    game, channel = start_pre_game(games_dir, run)

    press(channel, 1, find_button(channel, "FCIDteal_preGameOrbital_"))
    press(channel, 1, "FCIDteal_restartTurn")

    state = reload(game).gamestate
    # the pre-game action is not rolled back and no turn has started
    assert state["board"]["201"]["orbital_pop"] == [1]
    assert len(state["pre_game"]["tasks"]) == 3
    assert "activePlayerColor" not in state


def test_start_turn_slash_command_is_blocked_during_pre_game(games_dir, run):
    game, channel = start_pre_game(games_dir, run)
    interaction = FakeInteraction(channel, user_id=1)

    run(PlayerCommands(None).start_turn.callback(PlayerCommands(None), interaction))

    assert "activePlayerColor" not in reload(game).gamestate
    assert interaction.response.sent[0][0] == "The game has not started yet."


def test_slash_undo_during_pre_game_does_not_consume_a_save(games_dir, run):
    game, channel = start_pre_game(games_dir, run)
    game.updateSaveFile()
    before = game.get_saveFile()
    interaction = FakeInteraction(channel)

    run(GameCommands(None).undo_to_last_turn_start.callback(GameCommands(None), interaction))

    assert game.get_saveFile() == before
    assert "activePlayerColor" not in reload(game).gamestate
    assert "has not started" in interaction.response.sent[0][0]


def test_a_game_without_pre_game_actions_starts_right_away(games_dir, run, press):
    random.seed(0)
    GameInit("No pre game actions", [[1, "<@1>"], [2, "<@2>"]],
             "def", True, True, False, False).create_game()
    game = GamestateHelper(None, "aeb1")
    game.setup_techs_and_outer_rim(2, False, False)
    game.update()
    channel = FakeChannel("aeb1-actions")
    interaction = FakeInteraction(channel, role_names=["aeb1"])
    run(DraftButtons.generalSetup(interaction, game, [1, 2], ["hyd", "eri"]))

    state = reload(game).gamestate
    assert state["pre_game"]["tasks"] == []
    assert state["activePlayerColor"] == ["blue"]


@pytest.mark.parametrize("player_id,button_prefix,task", [
    (1, "FCIDteal_preGameOrbital_", "orbital_pop"),
    (3, "FCIDyellow_ancientsCube_", "artifact_cube"),
])
def test_rejected_population_does_not_complete_setup(games_dir, run, press,
                                                     player_id, button_prefix, task):
    game, channel = start_pre_game(games_dir, run)
    game = reload(game)
    game.get_player(player_id)["colony_ships"] = 0
    game.update()

    press(channel, player_id, find_button(channel, button_prefix))

    state = reload(game).gamestate
    assert [str(player_id), task] in state["pre_game"]["tasks"]
    assert "activePlayerColor" not in state


def finish_other_actions(channel, press):
    press(channel, 1, find_button(channel, "FCIDteal_preGameOrbital_"))
    press(channel, 3, find_button(channel, "FCIDyellow_ancientsCube_"))
    press(channel, 4, find_button(channel, "FCIDpurple_declineSetupTech"))


@pytest.mark.parametrize("discovery,follow_up", [
    ("mix", "FCIDblue_gain3resource_science"),
    ("mus", "FCIDblue_saveDiscoveryPart"),
    ("tec", "FCIDblue_getFreeTech_"),
])
def test_discovery_follow_up_must_finish_before_first_turn(games_dir, run, press,
                                                          discovery, follow_up):
    game, channel = start_pre_game(games_dir, run, [discovery, discovery])
    finish_other_actions(channel, press)
    if discovery == "tec":
        game = reload(game)
        game.gamestate["available_techs"] = ["neb", "gas"]
        game.update()
    press(channel, 2, find_button(channel, "FCIDblue_usedDiscForAbility_"))
    state = reload(game).gamestate
    assert len(state["pre_game"]["tasks"]) == 1
    assert "activePlayerColor" not in state

    press(channel, 2, find_button(channel, follow_up))

    assert reload(game).gamestate["pre_game"]["started"]
    assert reload(game).gamestate["activePlayerColor"] == ["teal"]


def test_discovery_part_can_be_installed_before_first_turn(games_dir, run, press):
    game, channel = start_pre_game(games_dir, run, ["mus", "mus"])
    finish_other_actions(channel, press)
    press(channel, 2, find_button(channel, "FCIDblue_usedDiscForAbility_"))
    press(channel, 2, find_button(channel, "FCIDblue_upgradeShip_1_interceptor_mus"))

    state = reload(game).gamestate
    assert state["players"]["2"]["interceptor_parts"][-1] == "mus"
    assert state["pre_game"]["tasks"] == []
    assert state["activePlayerColor"] == ["teal"]


@pytest.mark.parametrize("legacy_button", [False, True])
def test_upgrade_part_menu_save_button_completes_pre_game_discovery(
        games_dir, run, press, legacy_button):
    game, channel = start_pre_game(games_dir, run, ["anm", "anm"])
    finish_other_actions(channel, press)
    press(channel, 2, find_button(channel, "FCIDblue_usedDiscForAbility_"))
    upgrade_menu = press(channel, 2, find_button(channel, "FCIDblue_upgradeShip_1_interceptor_anm"))
    save_button = next(button.custom_id for button in upgrade_menu.message.edited["view"].children
                       if button.label == "Save For Future Upgrade Action")
    assert save_button == "FCIDblue_saveDiscoveryPart"
    if legacy_button:
        save_button = "FCIDblue_deleteMsg"
        for button in upgrade_menu.message.edited["view"].children:
            if button.label == "Save For Future Upgrade Action":
                button.custom_id = save_button
        upgrade_menu.message.components = [SimpleNamespace(children=upgrade_menu.message.edited["view"].children)]
    press(channel, 2, save_button, message=upgrade_menu.message)

    state = reload(game).gamestate
    assert state["pre_game"]["tasks"] == []
    assert state["activePlayerColor"] == ["teal"]


@pytest.mark.parametrize("undo_kind", ["slash", "button"])
@pytest.mark.parametrize("has_phase", [True, False])
def test_undo_does_not_restore_or_consume_pre_game_snapshot_after_start(
        games_dir, run, press, undo_kind, has_phase):
    game, channel = start_pre_game(games_dir, run)
    finish_other_actions(channel, press)
    press(channel, 2, find_button(channel, "FCIDblue_selectDiscTile_"))
    press(channel, 2, "FCIDblue_keepDiscForPoints")
    # Model the setup snapshot that can be left by setup tooling or other callers.
    setup_snapshot = reload(game).gamestate
    if has_phase:
        setup_snapshot["pre_game"]["started"] = False
    else:
        del setup_snapshot["pre_game"]
    save_file = game.get_saveFile()
    save_file["1"] = setup_snapshot
    save_file["newestSaveNum"] = 1
    with open(games_dir / f"{game.game_id}_saveFile.json", "w") as f:
        json.dump(save_file, f)
    before_save = reload(game).get_saveFile()

    if undo_kind == "slash":
        interaction = FakeInteraction(channel)
        run(GameCommands(None).undo_to_last_turn_start.callback(GameCommands(None), interaction))
        assert "setup" in interaction.response.sent[0][0]
    else:
        press(channel, 1, "FCIDteal_restartTurn")

    assert reload(game).gamestate["pre_game"]["started"]
    assert reload(game).gamestate["activePlayerColor"] == ["teal"]
    assert reload(game).get_saveFile() == before_save


def test_turn_actions_are_blocked_until_all_players_finish_setup(games_dir, run, press):
    game, channel = start_pre_game(games_dir, run)
    press(channel, 1, find_button(channel, "FCIDteal_preGameOrbital_"))
    before = reload(game).get_player(1).copy()

    press(channel, 1, "FCIDteal_startResearch")
    press(channel, 1, "FCIDteal_passForRound")
    press(channel, 1, "FCIDteal_runUpkeep")

    state = reload(game).gamestate
    assert state["players"]["1"] == before
    assert "activePlayerColor" not in state
    assert "roundNum" not in state


def test_setup_purchase_waits_for_wild_track_and_cannot_be_replayed(games_dir, run, press):
    game, channel = start_pre_game(games_dir, run)
    game = reload(game)
    game.gamestate["available_techs"] = ["abs"]
    game.get_player(4)["science"] = 10
    game.update()
    press(channel, 4, "FCIDpurple_setupTech")
    press(channel, 4, find_button(channel, "FCIDpurple_getTech_abs_any_setup"))
    assert ["4", "setup_tech"] in reload(game).preGameTasks()
    military = find_button(channel, "FCIDpurple_getTech_abs_military_setup")
    nano = find_button(channel, "FCIDpurple_getTech_abs_nano_setup")
    stale_message = channel.message_with(nano)
    press(channel, 4, military)
    assert ["4", "setup_tech"] not in reload(game).preGameTasks()
    before = reload(game).get_player(4).copy()
    press(channel, 4, nano, message=stale_message)
    assert reload(game).get_player(4) == before


@pytest.mark.parametrize("tech,follow_up", [("wap", "FCIDpurple_placeWarpPortal_"),
                                          ("ark", "FCIDpurple_finishSetupResources")])
def test_setup_research_waits_for_its_follow_up(games_dir, run, press, tech, follow_up):
    game, channel = start_pre_game(games_dir, run)
    game = reload(game)
    game.gamestate["available_techs"] = [tech]
    game.get_player(4)["science"] = 30
    game.update()
    press(channel, 4, "FCIDpurple_setupTech")
    press(channel, 4, find_button(channel, f"FCIDpurple_getTech_{tech}_"))
    if tech == "wap":
        press(channel, 4, find_button(channel, "FCIDpurple_getTech_wap_military_"))
    assert ["4", "setup_tech"] not in reload(game).preGameTasks()
    assert any(seat == "4" for seat, task in reload(game).preGameTasks())

    press(channel, 4, find_button(channel, follow_up))

    assert not any(seat == "4" for seat, task in reload(game).preGameTasks())


def test_unaffordable_setup_tech_does_not_spend_other_resources(games_dir, run, press):
    game, channel = start_pre_game(games_dir, run)
    game = reload(game)
    game.gamestate["available_techs"] = ["neb"]
    player = game.get_player(4)
    player["science"] = 0
    player["money"] = 30
    before = player.copy()
    game.update()

    press(channel, 4, "FCIDpurple_getTech_neb_military_setup")

    assert reload(game).get_player(4) == before
    assert ["4", "setup_tech"] in reload(game).preGameTasks()


def test_stale_setup_buttons_cannot_buy_again_after_game_starts(games_dir, run, press):
    game, channel = start_pre_game(games_dir, run)
    finish_other_actions(channel, press)
    press(channel, 2, find_button(channel, "FCIDblue_selectDiscTile_"))
    press(channel, 2, find_button(channel, "FCIDblue_keepDiscForPoints"))
    before = reload(game).get_player(4).copy()

    press(channel, 4, "FCIDpurple_setupTech")
    press(channel, 4, "FCIDpurple_getTech_neb_military_setup")

    assert reload(game).get_player(4) == before
    assert reload(game).gamestate["activePlayerColor"] == ["teal"]


def test_shared_undo_rejects_current_setup_without_consuming_save(games_dir, run):
    game, channel = start_pre_game(games_dir, run)
    game.updateSaveFile()
    before_state = reload(game).gamestate
    before_save = game.get_saveFile()

    assert not game.backUpToLastSaveFile()

    assert reload(game).gamestate == before_state
    assert game.get_saveFile() == before_save


def test_non_muon_discovery_part_install_finishes_setup(games_dir, run, press):
    game, channel = start_pre_game(games_dir, run, ["anm", "anm"])
    finish_other_actions(channel, press)
    press(channel, 2, find_button(channel, "FCIDblue_usedDiscForAbility_"))
    menu = press(channel, 2, find_button(channel, "FCIDblue_upgradeShip_1_interceptor_anm"))
    part_button = next(button.custom_id for button in menu.message.edited["view"].children
                       if button.custom_id.endswith("_anm_0"))

    press(channel, 2, part_button, message=menu.message)

    state = reload(game).gamestate
    assert state["players"]["2"]["interceptor_parts"][0] == "anm"
    assert state["pre_game"]["tasks"] == []
    assert state["pre_game"]["started"]


def test_discovery_change_ship_then_save_keeps_menu_usable(games_dir, run, press):
    game, channel = start_pre_game(games_dir, run, ["anm", "anm"])
    finish_other_actions(channel, press)
    press(channel, 2, find_button(channel, "FCIDblue_usedDiscForAbility_"))
    menu = press(channel, 2, find_button(channel, "FCIDblue_upgradeShip_1_interceptor_anm"))
    back = next(button.custom_id for button in menu.message.edited["view"].children
                if button.label == "Choose Different Ship")
    press(channel, 2, back, message=menu.message)
    press(channel, 2, find_button(channel, "FCIDblue_saveDiscoveryPart"))

    state = reload(game).gamestate
    assert "anm" in state["players"]["2"]["ancient_parts"]
    assert state["pre_game"]["started"]


@pytest.mark.parametrize("undo_kind", ["slash", "button"])
def test_mid_game_undo_preserves_completed_setup_and_restores_turn_menu(
        games_dir, run, press, undo_kind):
    game, channel = start_pre_game(games_dir, run)
    finish_other_actions(channel, press)
    press(channel, 2, find_button(channel, "FCIDblue_selectDiscTile_"))
    press(channel, 2, find_button(channel, "FCIDblue_keepDiscForPoints"))
    before = reload(game).get_player(1)
    press(channel, 1, "FCIDteal_startResearch")
    assert reload(game).get_player(1)["influence_discs"] == before["influence_discs"] - 1

    if undo_kind == "slash":
        interaction = FakeInteraction(channel, user_id=1)
        run(GameCommands(None).undo_to_last_turn_start.callback(GameCommands(None), interaction))
        run(PlayerCommands(None).start_turn.callback(PlayerCommands(None), interaction))
    else:
        press(channel, 1, "FCIDteal_restartTurn")

    state = reload(game).gamestate
    assert state["players"]["1"] == before
    assert state["pre_game"]["started"]
    assert state["pre_game"]["tasks"] == []
    assert state["activePlayerColor"] == ["teal"]
    assert "FCIDteal_startResearch" in buttons(channel)
    press(channel, 4, "FCIDpurple_setupTech")
    assert reload(game).gamestate["pre_game"]["started"]
    assert any("already finished" in content for content, kwargs in
               press(channel, 4, "FCIDpurple_getTech_neb_military_setup").followup.sent)
