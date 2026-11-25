"""The Horde: Built for War, Raid, Call To Arms, Battle Focus and initiative."""

import discord
from unittest.mock import AsyncMock

from Buttons.DiscoveryTile import DiscoveryTileButtons
from Buttons.Research import ResearchButtons
from Buttons.Upgrade import UpgradeButtons
from helpers import FactionData
from helpers.CombatHelper import Combat
from helpers.DrawHelper import DrawHelper
from helpers.PlayerHelper import PlayerHelper
from tests.fakes import FakeInteraction, buttons, player_helper, player_stats, reload


def _combat_game(make_game, blue_parts, red_parts=None):
    blue = player_stats("hor", color="blue", cruiser_parts=blue_parts)
    red = player_stats("hyd", color="red", name="Hydran Progress",
                       cruiser_parts=red_parts or ["ioc", "nus", "nud", "hul", "hul"])
    return make_game({
        "advanced_ai": 0, "wa_ai": 0, "player_count": 2,
        "players": {"1": blue, "2": red},
        "board": {"101": {"owner": 0, "sector": 101, "disctile": 0,
                          "player_ships": ["blue-cru", "red-cru"],
                          "attacker": "red", "defender": "blue"}},
    }, game_id="aeb1")


def test_built_for_war_adds_one_damage_on_a_natural_six(make_game, no_random, run):
    game = _combat_game(make_game, ["ioc", "nus", "nud", "elc", "hul"])
    no_random([6])
    run(Combat.rollDice(game, "rollDice_101_blue_1_deleteMsg", FakeInteraction()))
    assert game.gamestate["board"]["101"]["damage_tracker"]["red-cru"] == 2


def test_built_for_war_does_not_change_a_non_six(make_game, no_random, run):
    # No computer, so a natural 5 stays a miss and Built for War must not change it.
    game = _combat_game(make_game, ["ioc", "nus", "nud", "hul", "hul"])
    no_random([5])
    run(Combat.rollDice(game, "rollDice_101_blue_1_deleteMsg", FakeInteraction()))
    assert "damage_tracker" not in game.gamestate["board"]["101"]


class _ResearchGame:
    def get_player_from_color(self, color):
        return "1"

    def preGameTasks(self):
        return []


def test_a_full_tech_tray_is_refused(run):
    player = player_stats("hor", science=20, military_tech=["neb", "a", "b", "c"])
    interaction = FakeInteraction()
    run(ResearchButtons.getTech(_ResearchGame(), player, PlayerHelper("1", player), interaction,
                                "getTech_neb_military"))
    assert player["military_tech"] == ["neb", "a", "b", "c"]
    assert any("full" in str(content).lower() for content, _ in interaction.followup.sent)


def test_a_free_tech_cannot_overflow_the_four_slot_track(make_game, run):
    player = player_stats("hor", color="blue", military_tech=["neb", "plc", "stb", "phs"])
    game = make_game({"players": {"1": player}})
    interaction = FakeInteraction()
    run(DiscoveryTileButtons.getFreeTech(game, interaction, "getFreeTech_plc_military", player))
    assert player["military_tech"] == ["neb", "plc", "stb", "phs"]
    assert any("full" in str(content).lower() for content, _ in interaction.channel.sent)


def test_battle_focus_rejects_a_stale_same_class_upgrade(start_game, run):
    game, channel = start_game(factions=["hor", "eri"])
    player = game.get_player(1)
    player["battleFocusUsed"] = ["interceptor"]
    game.update()

    interaction = FakeInteraction(channel)
    run(UpgradeButtons.chooseUpgrade(game, player, interaction,
                                     "chooseUpgrade_1_interceptor_ioc_hul_0_dummy",
                                     player_helper(game, "blue")))

    assert player["battleFocusUsed"] == ["interceptor"]
    assert any("already used" in str(content).lower() for content, _ in interaction.followup.sent)


def test_horde_ship_part_editor_ignores_battle_focus(start_game, run):
    game, channel = start_game(factions=["hor", "eri"])
    player = game.get_player(1)
    player["battleFocusUsed"] = ["interceptor"]
    game.update()

    run(UpgradeButtons.chooseUpgrade(game, player, FakeInteraction(channel),
                                     "chooseUpgrade_1_interceptor_ioc_hul_0_free",
                                     player_helper(game, "blue")))

    menu = buttons(channel)
    assert "FCIDblue_deleteMsg" in menu
    assert any(cid.startswith("FCIDblue_upgradeShip_1_") and cid.endswith("_free") for cid in menu)


def test_raid_reuses_the_move_build_activation(start_game, press):
    assert FactionData.has(player_stats("hor"), "raid")
    assert DrawHelper.action_annotation(player_stats("hor"), "move") == "+1 BUI"
    _game, channel = start_game(factions=["hor", "eri"])
    press(channel, 1, "FCIDblue_startMove")
    assert any(cid.startswith("FCIDblue_herRaidBuild_") for cid in buttons(channel))


def test_call_to_arms_pays_materials_for_ships_lost_outside_your_sector(make_game):
    for ship, gain in (("int", 1), ("cru", 2), ("drd", 3)):
        game = make_game({"players": {"1": player_stats("hor", color="blue")},
                          "board": {"101": {"owner": "red", "sector": 101, "disctile": 0,
                                            "player_ships": [f"blue-{ship}"]}}})
        before = game.get_player(1)["materials"]
        assert game.destroy_ship(f"blue-{ship}", "101", "red") == gain
        assert game.get_player(1)["materials"] == before + gain
        assert game.destroy_ship(f"blue-{ship}", "101", "red") == 0
        assert game.get_player(1)["materials"] == before + gain


def test_stale_hit_keeps_other_targets_without_paying_for_a_destroyed_ship(make_game, run):
    game = _combat_game(make_game, ["ioc", "nus", "nud", "hul", "hul"])
    tile = game.gamestate["board"]["101"]
    tile["player_ships"].append("blue-int")
    interaction = FakeInteraction()
    run(Combat.offerHitPrompt(game, interaction, "101", "red", ["blue-int", "blue-cru"], 6, 1))
    view = interaction.channel.sent[-1][1]["view"]
    interaction.message.components = [discord.components.ActionRow(row) for row in view.to_components()]
    game.destroy_ship("blue-int", "101", "red")
    before = game.get_player(1)["materials"]

    run(Combat.assignHitTo(game, "assignHitTo_101_red_blue-int_6_1", interaction, True))

    assert game.get_player(1)["materials"] == before
    assert tile["unresolvedHits"] == 1
    assert [item.custom_id for item in interaction.message.edited["view"].children] == [
        "FCIDred_assignHitTo_101_red_blue-cru_6_1"]


def test_stale_hit_with_no_targets_does_not_leave_combat_waiting(make_game, run, monkeypatch):
    game = _combat_game(make_game, ["ioc", "nus", "nud", "hul", "hul"])
    tile = game.gamestate["board"]["101"]
    tile["player_ships"].append("blue-int")
    interaction = FakeInteraction()
    run(Combat.offerHitPrompt(game, interaction, "101", "red", ["blue-int", "blue-int"], 6, 1))
    view = interaction.channel.sent[-1][1]["view"]
    interaction.message.components = [discord.components.ActionRow(row) for row in view.to_components()]
    game.destroy_ship("blue-int", "101", "red")
    before = game.get_player(1)["materials"]
    prompt = AsyncMock()
    monkeypatch.setattr(Combat, "promptNextSpeed", prompt)

    run(Combat.assignHitTo(game, "assignHitTo_101_red_blue-int_6_1", interaction, True))

    assert game.get_player(1)["materials"] == before
    assert tile["unresolvedHits"] == 0
    prompt.assert_awaited_once()


def test_call_to_arms_does_not_pay_in_a_sector_you_control(make_game):
    game = make_game({"players": {"1": player_stats("hor", color="blue")},
                      "board": {"101": {"owner": "blue", "sector": 101, "disctile": 0,
                                        "player_ships": ["blue-int"]}}})
    before = game.get_player(1)["materials"]
    assert game.destroy_ship("blue-int", "101", "red") == 0
    assert game.get_player(1)["materials"] == before


def test_battle_focus_hides_an_already_upgraded_class(start_game, press):
    game, channel = start_game(factions=["hor", "eri"])
    press(channel, 1, "FCIDblue_startUpgrade")
    inter = press(channel, 1, next(cid for cid in buttons(channel)
                                   if cid.startswith("FCIDblue_upgradeShip_")
                                   and "interceptor" in cid))
    old_part = next(cid for cid in inter.message.edited["view"].children
                    if cid.custom_id.startswith("FCIDblue_selectOldPart_")
                    and cid.custom_id.endswith("_dummy_0"))
    inter = press(channel, 1, old_part.custom_id, inter.message)
    new_part = next(cid for cid in inter.message.edited["view"].children
                    if cid.custom_id.startswith("FCIDblue_chooseUpgrade_")
                    and cid.custom_id.endswith("_hul_0_dummy"))
    press(channel, 1, new_part.custom_id, inter.message)

    assert reload(game).get_player(1)["battleFocusUsed"] == ["interceptor"]
    offered = buttons(channel)
    assert not any("interceptor" in cid for cid in offered if cid.startswith("FCIDblue_upgradeShip_"))
    assert any("cruiser" in cid for cid in offered if cid.startswith("FCIDblue_upgradeShip_"))


def test_free_discovery_tech_skips_a_full_tray(make_game, run):
    player = player_stats("hor")
    player["military_tech"] = ["stb"] * FactionData.tech_track_max(player)
    game = make_game({"players": {"1": player}, "available_techs": ["neb", "fus"],
                      "board": {"201": {}}})
    player = game.get_player(1)
    interaction = FakeInteraction()

    run(DiscoveryTileButtons.usedDiscForAbility(game, PlayerHelper("1", player), interaction,
                                                "usedDiscForAbility_tec_201", player))

    assert "fus" in reload(game).get_player(1)["grid_tech"]
