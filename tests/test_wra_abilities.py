"""The Wraith species rules: Phase Technology, Ghosts and the Phase Module.

Values come from the printed card and board: two Build activations may become one Build plus
one Upgrade, a retreat happens before the ship fires, and the Phase Module declaration is made
per blueprint before initiative is prompted. Soul-Hunters has its own test file.
"""
import pytest

from Buttons.Build import BuildButtons
from Buttons.Explore import ExploreButtons
from Buttons.Upgrade import UpgradeButtons
from helpers.CombatHelper import Combat
from helpers.PlayerHelper import PlayerHelper
from helpers.ShipHelper import PlayerShip
from tests.fakes import FakeInteraction, FakeMessage, board_tile, buttons, player_stats, reload


def view_ids(inter):
    return {child.custom_id: child.label for child in inter.message.edited["view"].children}


def start_build(press, channel, color="blue", first=True):
    if first:
        press(channel, 1, f"FCID{color}_startBuild")
    else:
        press(channel, 1, "startBuild2_deleteMsg")
    press(channel, 1, f"FCID{color}_buildIn_201")


def finish_build(press, channel, color="blue"):
    inter = press(channel, 1, next(cid for cid in buttons(channel) if cid.endswith("_201_Interceptor")))
    inter = press(channel, 1, next(cid for cid in view_ids(inter) if cid.startswith(f"FCID{color}_finishBuild_")))
    inter = press(channel, 1, next(cid for cid in buttons(channel) if cid.startswith(f"FCID{color}_spendMaterial_")))
    return press(channel, 1, next(cid for cid in view_ids(inter)
                                  if cid.startswith(f"FCID{color}_finishSpendForBuild_")))


def build_one_unit(press, channel, color="blue", first=True):
    start_build(press, channel, color, first)
    return finish_build(press, channel, color)


# --- Phase Technology --------------------------------------------------------

def test_phase_technology_swaps_the_second_build_activation_for_one_upgrade(start_game, press):
    game, channel = start_game(factions=["wra", "eri"])

    inter = build_one_unit(press, channel)
    assert "FCIDblue_phaseTechUpgrade" in buttons(channel)

    press(channel, 1, "FCIDblue_phaseTechUpgrade")
    assert "FCIDblue_upgradeShip_1_interceptor_phase" in buttons(channel)
    inter = press(channel, 1, "FCIDblue_upgradeShip_1_interceptor_phase")
    parts_menu = view_ids(inter)
    assert not [cid for cid in parts_menu
                if cid.startswith("FCIDblue_selectOldPart_") and "_empty_" in cid]
    inter = press(channel, 1, next(cid for cid in parts_menu
                                   if cid.startswith("FCIDblue_selectOldPart_") and "_ioc_" in cid))
    replacement = next(cid for cid in view_ids(inter)
                       if cid.startswith("FCIDblue_chooseUpgrade_") and "_hul_" in cid)
    press(channel, 1, replacement)

    state = reload(game).get_player(1)
    assert state["interceptor_parts"] == ["hul", "nus", "empty", "nud"]
    assert state["influence_discs"] == 11          # the Build action's disc only
    assert state["upgrade_action_counters"] == 0   # the swap is not an Upgrade action
    assert state["phaseSwappedThisAction"] is True


def test_phase_technology_keeps_the_build_activation_it_did_not_spend(start_game, press):
    game, channel = start_game(factions=["wra", "eri"])
    player = game.get_player(1)
    player["build_apt"] = 3
    player["materials"] = 8
    game.update()

    build_one_unit(press, channel)
    press(channel, 1, "FCIDblue_phaseTechUpgrade")
    inter = press(channel, 1, "FCIDblue_upgradeShip_1_interceptor_phase")
    parts_menu = view_ids(inter)
    inter = press(channel, 1, next(cid for cid in parts_menu
                                   if cid.startswith("FCIDblue_selectOldPart_") and "_ioc_" in cid))
    replacement = next(cid for cid in view_ids(inter)
                       if cid.startswith("FCIDblue_chooseUpgrade_") and "_hul_" in cid)
    press(channel, 1, replacement)

    # One of the three activations is still a build, so it must still be offered.
    assert "FCIDblue_phaseTechResume" in buttons(channel)
    press(channel, 1, "FCIDblue_phaseTechResume")
    assert "FCIDblue_buildIn_201" in buttons(channel)
    press(channel, 1, "FCIDblue_buildIn_201")
    assert any("up to 1 units" in content for content, _kwargs in channel.sent if content)


def test_phase_technology_is_not_offered_after_two_builds(start_game, press):
    game, channel = start_game(factions=["wra", "eri"])
    game.get_player(1)["materials"] = 8
    game.update()

    build_one_unit(press, channel)
    assert "FCIDblue_phaseTechUpgrade" in buttons(channel)

    build_one_unit(press, channel, first=False)
    assert "FCIDblue_phaseTechUpgrade" not in buttons(channel)
    assert reload(game).get_player(1)["phaseBuildsThisAction"] == 2


def test_wraith_influence_action_uses_one_activation(start_game, press):
    game, channel = start_game(factions=["wra", "eri"])
    game.add_tile("301", 0, "102")
    game.add_tile("302", 0, "102")
    game.update()

    press(channel, 1, "FCIDblue_startInfluence")
    press(channel, 1, "FCIDblue_addInfluenceFinish_301")
    press(channel, 1, "FCIDblue_addInfluenceFinish_302")

    state = reload(game)
    assert state.gamestate["board"]["301"]["owner"] == "blue"
    assert state.gamestate["board"]["302"]["owner"] == 0
    assert state.get_player(1)["influence_discs"] == 11


def test_phase_technology_is_only_for_the_wraith(start_game, press):
    game, channel = start_game(factions=["hyd", "eri"])
    game.get_player(1)["materials"] = 4
    game.update()

    build_one_unit(press, channel)

    assert "FCIDblue_phaseTechUpgrade" not in buttons(channel)


def test_phase_technology_undo_restores_the_blueprint_without_spending_a_disc(start_game, press):
    game, channel = start_game(factions=["wra", "eri"])
    build_one_unit(press, channel)
    press(channel, 1, "FCIDblue_phaseTechUpgrade")
    inter = press(channel, 1, "FCIDblue_upgradeShip_1_interceptor_phase")
    inter = press(channel, 1, next(cid for cid in view_ids(inter)
                                   if cid.startswith("FCIDblue_selectOldPart_") and "_ioc_" in cid))
    press(channel, 1, next(cid for cid in view_ids(inter)
                           if cid.startswith("FCIDblue_chooseUpgrade_") and "_hul_" in cid))

    press(channel, 1, "FCIDblue_undoUpgrade_1_phase")

    state = reload(game).get_player(1)
    assert state["interceptor_parts"] == ["ioc", "nus", "empty", "nud"]
    assert state["influence_discs"] == 11
    assert "FCIDblue_upgradeShip_1_interceptor_phase" in buttons(channel)


def test_phase_technology_cannot_be_swapped_before_a_build(start_game, run):
    game, channel = start_game(factions=["wra", "eri"])
    inter = FakeInteraction(channel)

    run(BuildButtons.phaseTechUpgrade(game, game.get_player(1), inter, "phaseTechUpgrade",
                                      PlayerHelper(1, game.get_player(1))))

    assert "Phase Technology swaps a later Build activation" in inter.followup.sent[0][0]
    assert reload(game).get_player(1).get("phaseSwappedThisAction") is not True


def test_phase_technology_resets_at_the_next_build_action(start_game, run):
    game, channel = start_game(factions=["wra", "eri"])
    player = game.get_player(1)
    player["phaseBuildsThisAction"] = 2
    player["phaseSwappedThisAction"] = True
    game.update()

    run(BuildButtons.startBuild(game, player, FakeInteraction(channel), "startBuild",
                                PlayerHelper(1, player)))

    state = reload(game).get_player(1)
    assert state["phaseBuildsThisAction"] == 0
    assert state["phaseSwappedThisAction"] is False


# --- Ghosts ------------------------------------------------------------------

def wraith_combat(game, ships=("blue-int", "red-int"), owner="blue"):
    game.get_player(1)["owned_tiles"] = ["102"]
    game.gamestate["board"]["101"] = {
        "owner": owner, "sector": 101, "player_ships": list(ships),
        "wormholes": [0, 1, 3, 4], "type": "", "disctile": 0, "orientation": 120}
    game.gamestate["board"]["102"] = {
        "owner": "blue", "sector": 102, "player_ships": [],
        "wormholes": [0, 1, 3, 4], "type": "", "disctile": 0, "orientation": 60}
    game.setAttackerAndDefender(["red"], ["blue"], "101")
    game.gamestate["board"]["101"].pop("currentSpeed", None)
    game.gamestate["board"]["101"].pop("currentRoller", None)
    game.update()


def test_ghosts_retreats_before_the_ship_fires_and_applies_the_all_retreat_penalty(
        start_game, press, run, monkeypatch):
    game, channel = start_game(factions=["wra", "eri"])
    wraith_combat(game)
    declared = []

    async def declare(_game, _interaction, pos):
        declared.append(pos)

    monkeypatch.setattr(Combat, "declareAWinner", staticmethod(declare))
    run(Combat.promptNextSpeed(game, "101", channel, False))
    assert "FCIDblue_ghostsRetreat_101_blue_3" in buttons(channel)

    press(channel, 1, "FCIDblue_ghostsRetreat_101_blue_3")
    assert "FCIDblue_ghostsRetreatTo_101_blue_3_102" in buttons(channel)
    press(channel, 1, "FCIDblue_ghostsRetreatTo_101_blue_3_102")

    state = reload(game)
    assert state.gamestate["board"]["101"]["player_ships"] == ["red-int"]
    assert state.gamestate["board"]["102"]["player_ships"] == ["blue-int"]
    assert state.gamestate["board"]["101"]["retreatPenaltyblue"] is True
    assert declared == ["101"]


def test_non_wraith_still_announces_a_retreat_and_waits_for_its_next_turn(start_game, press, run):
    game, channel = start_game(factions=["hyd", "eri"])
    wraith_combat(game)
    run(Combat.promptNextSpeed(game, "101", channel, False))

    assert "FCIDblue_startToRetreatUnits_101_blue_3" in buttons(channel)
    assert "FCIDblue_ghostsRetreat_101_blue_3" not in buttons(channel)
    press(channel, 1, "FCIDblue_startToRetreatUnits_101_blue_3")

    state = reload(game)
    assert state.gamestate["board"]["101"]["unitsToRetreat"] == [[3, "blue"]]
    assert "blue-int" in state.gamestate["board"]["101"]["player_ships"]


def test_ghosts_moves_a_phase_module_speed_boosted_ship(start_game, press, run, monkeypatch):
    game, channel = start_game(factions=["wra", "eri"])
    wraith_combat(game)
    game.gamestate["board"]["101"]["phaseModes"] = {"blue": {"interceptor": {
        "comp": 0, "shield": 0, "speed": 2, "planets": False, "ignore": False, "cost": 2}}}

    async def declare(_game, _interaction, _pos):
        return None

    monkeypatch.setattr(Combat, "declareAWinner", staticmethod(declare))
    run(Combat.promptNextSpeed(game, "101", channel, False))
    assert "FCIDblue_ghostsRetreat_101_blue_5" in buttons(channel)
    press(channel, 1, "FCIDblue_ghostsRetreat_101_blue_5")
    press(channel, 1, "FCIDblue_ghostsRetreatTo_101_blue_5_102")

    assert reload(game).gamestate["board"]["102"]["player_ships"] == ["blue-int"]


def test_ghosts_is_not_offered_without_a_legal_retreat_destination(start_game, run):
    game, channel = start_game(factions=["wra", "eri"])
    wraith_combat(game)
    game.get_player(1)["owned_tiles"] = []
    game.update()

    run(Combat.promptNextSpeed(game, "101", channel, False))

    assert not [cid for cid in buttons(channel) if "ghostsRetreat" in cid]
    assert not [cid for cid in buttons(channel) if "startToRetreatUnits" in cid]


# --- Phase Module ------------------------------------------------------------

def phase_combat(make_game, souls=0, blue_ships=("blue-int",), red_ships=("red-cru",),
                 red_parts=None, game_id="t"):
    blue = player_stats("wra", color="blue")
    blue["wraithSouls"] = souls
    red = player_stats("hyd", color="red")
    if red_parts:
        red["cruiser_parts"] = red_parts
    board = board_tile(list(blue_ships) + list(red_ships), owner="blue", sector=101)
    game = make_game({"player_count": 2, "players": {"1": blue, "2": red}, "board": board,
                      "advanced_ai": False, "wa_ai": False, "reputation_tiles": [1, 2, 3]},
                     game_id=game_id)
    game.setAttackerAndDefender(["red"], ["blue"], "101")
    return game


def offer_phase(game, channel, pos="101"):
    assert run_offer(game, channel, pos)
    return channel.message_with(f"FCIDblue_phaseModuleDone_{pos}_blue")


def run_offer(game, channel, pos="101"):
    import asyncio
    return asyncio.run(Combat.offerPhaseModule(game, channel, pos))


def test_phase_module_is_offered_only_to_the_wraith_with_ships_in_the_tile(make_game):
    wraith = phase_combat(make_game)
    channel = FakeInteraction().channel
    assert run_offer(wraith, channel) is True
    assert "FCIDblue_phaseModuleShip_101_blue_interceptor" in buttons(channel)

    blue = player_stats("hyd", color="blue")
    red = player_stats("eri", color="red")
    hydran = make_game({"player_count": 2, "players": {"1": blue, "2": red},
                        "board": board_tile(["blue-int", "red-cru"], owner="blue", sector=101),
                        "advanced_ai": False, "wa_ai": False}, game_id="h")
    hydran.setAttackerAndDefender(["red"], ["blue"], "101")
    hydran_channel = FakeInteraction().channel
    assert run_offer(hydran, hydran_channel) is False
    assert not hydran_channel.sent


@pytest.mark.parametrize("pending", ["phase_module", "wolfPack", "pendingWolfPack", "ghostsRetreatPending"])
def test_combat_refresh_waits_for_faction_choices(make_game, run, pending):
    game = phase_combat(make_game)
    channel = FakeInteraction().channel
    tile = game.gamestate["board"]["101"]
    if pending == "phase_module":
        run_offer(game, channel)
    else:
        tile[pending] = "blue" if pending == "ghostsRetreatPending" else {"color": "blue"}
    current_turn = (tile.get("currentSpeed"), tile.get("currentRoller"))

    run(Combat.refreshCombatPrompt(game, "101", channel))

    assert "pending faction ability choices" in channel.sent[-1][0]
    assert (tile.get("currentSpeed"), tile.get("currentRoller")) == current_turn


def test_phase_module_menu_lists_only_the_blueprints_in_the_tile(make_game):
    game = phase_combat(make_game, blue_ships=("blue-int", "blue-cru"))
    channel = FakeInteraction().channel
    run_offer(game, channel)

    labels = [cid for cid in buttons(channel) if "phaseModuleShip" in cid]
    assert any(cid.endswith("_interceptor") for cid in labels)
    assert any(cid.endswith("_cruiser") for cid in labels)
    assert not any(cid.endswith("_starbase") for cid in labels)


def test_stock_interceptor_uses_its_one_unused_energy(make_game):
    game = phase_combat(make_game, souls=0)
    channel = FakeInteraction().channel
    message = offer_phase(game, channel)

    speed = FakeInteraction(channel, message=message)
    import asyncio
    asyncio.run(Combat.phaseModuleOption(game, "phaseModuleOption_101_blue_interceptor_speed", speed))
    assert "Not enough power" in speed.followup.sent[0][0]
    assert not game.gamestate["board"]["101"].get("phaseModes", {}).get("blue")

    comp = FakeInteraction(channel, message=message)
    asyncio.run(Combat.phaseModuleOption(game, "phaseModuleOption_101_blue_interceptor_comp", comp))
    assert not comp.followup.sent
    assert Combat.phase_mode(game, "blue", "101", "interceptor")["comp"] == 1


def test_offboard_power_applies_to_each_blueprint_and_reset_only_clears_options(make_game):
    game = phase_combat(make_game, souls=2, blue_ships=("blue-int", "blue-cru"))
    player = game.get_player(1)
    for ship in ("interceptor", "cruiser"):
        player[f"base_{ship}_nrg"] += 2 - PlayerShip(player, ship).energy
    channel = FakeInteraction().channel
    message = offer_phase(game, channel)

    import asyncio
    spd = FakeInteraction(channel, message=message)
    asyncio.run(Combat.phaseModuleOption(game, "phaseModuleOption_101_blue_interceptor_speed", spd))
    assert "speed" in game.gamestate["board"]["101"]["phaseModes"]["blue"]["interceptor"]

    cruiser = FakeInteraction(channel, message=message)
    asyncio.run(Combat.phaseModuleOption(game, "phaseModuleOption_101_blue_cruiser_speed", cruiser))
    assert not cruiser.followup.sent
    assert Combat.phase_mode(game, "blue", "101", "cruiser")["speed"] == 2

    reset = FakeInteraction(channel, message=message)
    asyncio.run(Combat.phaseModuleReset(game, "phaseModuleReset_101_blue_interceptor", reset))
    assert "interceptor" not in game.gamestate["board"]["101"].get("phaseModes", {}).get("blue", {})

    assert Combat.phase_mode(game, "blue", "101", "cruiser")["speed"] == 2
    assert game.get_player(1)["wraithSouls"] == 2


def test_phase_module_done_starts_combat_once(make_game, monkeypatch):
    import asyncio
    game = phase_combat(make_game)
    channel = FakeInteraction().channel
    message = offer_phase(game, channel)
    prompted = []

    async def prompt(_game, pos, _channel, _update):
        prompted.append(pos)

    monkeypatch.setattr(Combat, "promptNextSpeed", prompt)
    asyncio.run(Combat.phaseModuleDone(game, "phaseModuleDone_101_blue",
                                       FakeInteraction(channel, message=message)))
    asyncio.run(Combat.phaseModuleDone(game, "phaseModuleDone_101_blue",
                                       FakeInteraction(channel, message=FakeMessage(channel))))

    assert prompted == ["101"]


def test_phase_module_clear_all_refunds_and_starts_combat(make_game, monkeypatch):
    import asyncio
    game = phase_combat(make_game, souls=2)
    channel = FakeInteraction().channel
    message = offer_phase(game, channel)
    asyncio.run(Combat.phaseModuleOption(game, "phaseModuleOption_101_blue_interceptor_comp",
                                         FakeInteraction(channel, message=message)))
    prompted = []

    async def prompt(_game, pos, _channel, _update):
        prompted.append(pos)

    monkeypatch.setattr(Combat, "promptNextSpeed", prompt)
    asyncio.run(Combat.phaseModuleDone(game, "phaseModuleNone_101_blue",
                                       FakeInteraction(channel, message=message), clear=True))

    assert prompted == ["101"]
    assert "blue" not in game.gamestate["board"]["101"].get("phaseModes", {})


def test_a_new_pairing_clears_the_previous_declaration(make_game, run):
    game = phase_combat(make_game)
    tile = game.gamestate["board"]["101"]
    tile["phaseModes"] = {"blue": {"interceptor": {
        "comp": 1, "shield": 0, "speed": 0, "planets": False, "ignore": False, "cost": 1}}}
    channel = FakeInteraction().channel

    run(Combat.startCombat(game, channel, "101"))

    assert "blue" not in game.gamestate["board"]["101"].get("phaseModes", {})


def test_phase_module_speed_changes_initiative(make_game):
    game = phase_combat(make_game)
    game.gamestate["board"]["101"]["phaseModes"] = {"blue": {"interceptor": {
        "comp": 0, "shield": 0, "speed": 2, "planets": False, "ignore": False, "cost": 2}}}

    assert Combat.getCombatantShipsBySpeed(
        game, "blue", game.gamestate["board"]["101"]["player_ships"], "101") == [(5, "int", 1)]
    assert Combat.getBothCombatantShipsBySpeed(
        game, ["blue"], ["red"], game.gamestate["board"]["101"]["player_ships"], "101")[0] == (5, "blue")
    game.gamestate["board"]["102"] = {"owner": "blue", "sector": 102, "player_ships": ["blue-int"],
                                      "wormholes": [0, 1, 3, 4], "type": "", "disctile": 0}
    assert Combat.getCombatantShipsBySpeed(game, "blue", ["blue-int"], "102") == [(3, "int", 1)]


def test_phase_module_shield_applies_to_the_target(make_game):
    game = phase_combat(make_game)
    ships = game.gamestate["board"]["101"]["player_ships"]

    assert Combat.getOpponentUnitsThatCanBeHit(game, "red", ships, 5, 1, "101", 3) == ["blue-int"]
    game.gamestate["board"]["101"]["phaseModes"] = {"blue": {"interceptor": {
        "comp": 0, "shield": 1, "speed": 0, "planets": False, "ignore": False, "cost": 1}}}
    assert Combat.getOpponentUnitsThatCanBeHit(game, "red", ships, 5, 1, "101", 3) == []


def test_phase_module_ignore_shields_lets_a_computer_hit_through(make_game):
    game = phase_combat(make_game, souls=3, red_parts=["elc", "ioc", "gas", "nus", "hul", "nud"])
    ships = game.gamestate["board"]["101"]["player_ships"]
    game.gamestate["board"]["101"]["phaseModes"] = {"blue": {"interceptor": {
        "comp": 1, "shield": 0, "speed": 0, "planets": False, "ignore": True, "cost": 4}}}

    assert Combat.getOpponentUnitsThatCanBeHit(game, "blue", ships, 5, 1, "101", 3) == []
    assert Combat.getOpponentUnitsThatCanBeHit(
        game, "blue", ships, 5, 1, "101", 3, ignore_shields=True) == ["red-cru"]


def test_phase_module_offboard_power_defaults_to_zero_for_old_saves(make_game):
    game = phase_combat(make_game)
    del game.gamestate["players"]["1"]["wraithSouls"]

    assert PlayerShip(game.get_player(1), "interceptor").energy == 1


def winning_wraith_game(make_game, planets):
    blue = player_stats("wra", color="blue")
    blue["military_tech"] = ["phm", "neb"]
    red = player_stats("hyd", color="red")
    red["owned_tiles"] = ["101"]
    game = make_game({"player_count": 2, "players": {"1": blue, "2": red},
                      "board": board_tile(["blue-int"], owner="red", sector=101,
                                          money_pop=[1], science_pop=[1], material_pop=[1]),
                      "advanced_ai": False, "wa_ai": False, "reputation_tiles": [1, 2, 3]})
    game.setAttackerAndDefender(["blue"], ["red"], "101")
    game.gamestate["board"]["101"]["phaseModes"] = {"blue": {"interceptor": {
        "comp": 0, "shield": 0, "speed": 0, "planets": planets,
        "ignore": False, "cost": 2 if planets else 0}}}
    return game


def test_phase_module_planets_is_required_before_the_auto_destroy(make_game, run):
    from tests.fakes import offered_labels
    no_planets = winning_wraith_game(make_game, False)
    channel = FakeInteraction().channel
    run(Combat.declareAWinner(no_planets, FakeInteraction(channel), "101"))
    assert "Roll to Destroy Population" in offered_labels(FakeInteraction(channel))
    assert "phaseModes" not in no_planets.gamestate["board"]["101"]

    planets = winning_wraith_game(make_game, True)
    channel = FakeInteraction().channel
    run(Combat.declareAWinner(planets, FakeInteraction(channel), "101"))
    labels = [button.label for _content, kwargs in channel.sent
              for button in getattr(kwargs.get("view"), "children", [])]
    assert "Destroy All Population" in labels
    assert "phaseModes" not in planets.gamestate["board"]["101"]


def test_phase_module_always_cloaking_pins_like_the_cloaking_device(make_game):
    game = phase_combat(make_game)
    wraith = game.getPlayerObjectFromColor("blue")
    hydran = player_stats("hyd", color="red")

    assert ExploreButtons.doesPlayerHaveUnpinnedShips(wraith, ["blue-int", "red-int"], game, "101") is True
    assert ExploreButtons.doesPlayerHaveUnpinnedShips(wraith, ["blue-int", "red-int", "red-cru"],
                                                      game, "101") is False
    assert ExploreButtons.doesPlayerHaveUnpinnedShips(hydran, ["red-int", "blue-int"], game, "101") is False


@pytest.mark.parametrize("souls", [1, 2])
def test_phase_module_bombing_only_tile_offers_neutron_bombs_when_powered(make_game, run, souls):
    blue = player_stats("wra", color="blue")
    blue["military_tech"] = ["phm", "neb"]
    blue["wraithSouls"] = souls
    red = player_stats("hyd", color="red")
    game = make_game({"player_count": 2, "players": {"1": blue, "2": red},
                      "board": board_tile(["blue-int"], owner="red", sector=101,
                                          money_pop=[1], science_pop=[1], material_pop=[1]),
                      "advanced_ai": False, "wa_ai": False, "reputation_tiles": [1, 2, 3],
                      "game_id": "t", "roundNum": 1})
    channel = FakeInteraction(role_names=["t"]).channel
    run(Combat.startCombatThreads(game, FakeInteraction(channel, role_names=["t"])))

    bombing = channel.threads[0]
    labels = [button.label for _content, kwargs in bombing.sent
              for button in getattr(kwargs.get("view"), "children", [])]
    assert labels == ["Roll to Destroy Population", "Use Phase Module: Neutron Bombs (2 Power)"]
    assert any("use 2 blueprint Power" in content for content, _kwargs in bombing.sent)


@pytest.mark.parametrize("change", ["round", "fleet", "owner", "population", "combat"])
def test_phase_module_rejects_obsolete_bombing_prompt(make_game, run, press, change):
    blue = player_stats("wra", color="blue", military_tech=["phm", "neb"], wraithSouls=2)
    red = player_stats("hyd", color="red", owned_tiles=["101"])
    game = make_game({"player_count": 2, "players": {"1": blue, "2": red},
                      "board": board_tile(["blue-int"], owner="red", sector=101, money_pop=[1]),
                      "advanced_ai": False, "wa_ai": False, "reputation_tiles": [1, 2, 3],
                      "game_id": "t", "roundNum": 1})
    channel = FakeInteraction(role_names=["t"]).channel
    run(Combat.startCombatThreads(game, FakeInteraction(channel, role_names=["t"])))
    bombing = channel.threads[0]
    custom_id = "FCIDblue_phaseBombing_101_1"
    message = bombing.message_with(custom_id)
    assert message is not None
    tile = game.gamestate["board"]["101"]
    if change == "round":
        game.gamestate["roundNum"] = 2
    elif change == "fleet":
        tile["player_ships"] = []
    elif change == "owner":
        tile["owner"] = "blue"
    elif change == "population":
        tile["money_pop"] = [0]
    elif change == "combat":
        tile["player_ships"].append("red-int")
    game.update()

    interaction = press(bombing, 1, custom_id, message)

    state = reload(game)
    assert state.gamestate["board"]["101"] == tile
    assert state.get_player(1).get("wraithPowerSpent", 0) == 0
    assert state.get_player(1)["wraithSouls"] == 2
    assert "no longer current" in interaction.followup.sent[0][0]


def test_phase_module_bombing_only_tile_without_power_leaves_only_the_roll(make_game, run):
    blue = player_stats("wra", color="blue")
    blue["military_tech"] = ["phm", "neb"]
    blue["wraithSouls"] = 0
    red = player_stats("hyd", color="red")
    game = make_game({"player_count": 2, "players": {"1": blue, "2": red},
                      "board": board_tile(["blue-int"], owner="red", sector=101, money_pop=[1]),
                      "advanced_ai": False, "wa_ai": False, "reputation_tiles": [1, 2, 3],
                      "game_id": "t", "roundNum": 1})
    channel = FakeInteraction(role_names=["t"]).channel
    run(Combat.startCombatThreads(game, FakeInteraction(channel, role_names=["t"])))

    bombing = channel.threads[0]
    labels = [button.label for _content, kwargs in bombing.sent
              for button in getattr(kwargs.get("view"), "children", [])]
    assert labels == ["Roll to Destroy Population"]
    assert any("needs 2 Power" in content for content, _kwargs in bombing.sent)


@pytest.mark.parametrize("energy", [2, 3, 4])
def test_phase_module_bombs_a_sector_without_consuming_power(make_game, run, energy):
    blue = player_stats("wra", color="blue")
    blue["military_tech"] = ["phm", "neb"]
    blue["wraithSouls"] = 4
    blue["base_interceptor_nrg"] += energy - PlayerShip(blue, "interceptor").energy
    red = player_stats("hyd", color="red")
    red["owned_tiles"] = ["101"]
    game = make_game({"player_count": 2, "players": {"1": blue, "2": red},
                      "board": board_tile(["blue-int"], owner="red", sector=101, money_pop=[1]),
                      "advanced_ai": False, "wa_ai": False, "reputation_tiles": [1, 2, 3],
                      "game_id": "t", "roundNum": 1})

    run(Combat.phaseBombing(game, blue, FakeInteraction(), "phaseBombing_101_1"))

    state = reload(game)
    assert state.gamestate["board"]["101"]["owner"] == 0
    assert state.get_player(1)["wraithSouls"] == 5
    assert state.get_player(1).get("wraithPowerSpent", 0) == 0
    assert PlayerShip(state.get_player(1), "interceptor").energy == energy + 1
    replay = FakeInteraction()
    run(Combat.phaseBombing(state, state.get_player(1), replay, "phaseBombing_101_1"))
    assert state.get_player(1).get("wraithPowerSpent", 0) == 0
    assert "no longer has an owner" in replay.followup.sent[0][0]


def test_rolling_is_refused_until_the_phase_module_declaration_is_done(make_game, monkeypatch):
    import asyncio
    game = phase_combat(make_game, souls=2)
    channel = FakeInteraction().channel
    message = offer_phase(game, channel)
    before = FakeInteraction(channel)

    asyncio.run(Combat.rollDice(game, "rollDice_101_blue_3_deleteMsg", before))
    assert "Declare Phase Module options before rolling initiative" in before.channel.sent[-1][0]
    assert "currentSpeed" not in game.gamestate["board"]["101"]

    asyncio.run(Combat.phaseModuleOption(game, "phaseModuleOption_101_blue_interceptor_speed",
                                         FakeInteraction(channel, message=message)))

    async def prompt(_game, _pos, _channel, _update):
        return None
    monkeypatch.setattr(Combat, "promptNextSpeed", prompt)
    asyncio.run(Combat.phaseModuleDone(game, "phaseModuleDone_101_blue",
                                       FakeInteraction(channel, message=message)))
    stale = FakeInteraction(channel)
    asyncio.run(Combat.rollDice(game, "rollDice_101_blue_3_deleteMsg", stale))
    assert "no longer valid" in stale.channel.sent[-1][0]


def test_ghosts_retreat_blocks_a_manual_roll_until_the_destination_is_chosen(
        start_game, press, run):
    import asyncio
    game, channel = start_game(factions=["wra", "eri"])
    wraith_combat(game)
    run(Combat.promptNextSpeed(game, "101", channel, False))
    press(channel, 1, "FCIDblue_ghostsRetreat_101_blue_3")

    stale = FakeInteraction(channel)
    state = reload(game)
    asyncio.run(Combat.rollDice(state, "rollDice_101_blue_3_deleteMsg", stale))
    assert "A retreat is being resolved" in stale.channel.sent[-1][0]
    assert state.gamestate["board"]["101"]["player_ships"] == ["blue-int", "red-int"]


def test_declared_power_is_not_consumed_and_survives_the_next_combat(make_game, run, monkeypatch):
    game = phase_combat(make_game, souls=2)
    channel = FakeInteraction().channel
    message = offer_phase(game, channel)

    async def prompt(game, pos, channel, update):
        return None

    monkeypatch.setattr(Combat, "promptNextSpeed", prompt)
    run(Combat.phaseModuleOption(game, "phaseModuleOption_101_blue_interceptor_speed",
                                 FakeInteraction(channel, message=message)))
    run(Combat.phaseModuleDone(game, "phaseModuleDone_101_blue",
                               FakeInteraction(channel, message=message)))
    run(Combat.phaseModuleDone(game, "phaseModuleDone_101_blue",
                               FakeInteraction(channel, message=message)))
    game = reload(game)
    assert game.get_player(1).get("wraithPowerSpent", 0) == 0
    assert game.get_player(1)["wraithSouls"] == 2
    assert PlayerShip(game.get_player(1), "interceptor").energy == 3
    Combat.clear_phase_module(game, "101")
    assert PlayerShip(reload(game).get_player(1), "interceptor").energy == 3


@pytest.mark.parametrize("energy, souls", [(3, 0), (1, 1), (0, 2)])
def test_phase_module_uses_permanent_blueprint_power(
        make_game, run, monkeypatch, energy, souls):
    game = phase_combat(make_game, souls=souls)
    player = game.get_player(1)
    player["base_interceptor_nrg"] += energy + souls - PlayerShip(player, "interceptor").energy
    channel = FakeInteraction().channel
    message = offer_phase(game, channel)

    async def prompt(game, pos, channel, update):
        return None

    monkeypatch.setattr(Combat, "promptNextSpeed", prompt)
    run(Combat.phaseModuleOption(game, "phaseModuleOption_101_blue_interceptor_speed",
                                FakeInteraction(channel, message=message)))
    assert Combat.phase_mode(game, "blue", "101", "interceptor")["speed"] == 2
    assert PlayerShip(player, "interceptor").energy == energy + souls
    run(Combat.phaseModuleDone(game, "phaseModuleDone_101_blue",
                              FakeInteraction(channel, message=message)))
    assert reload(game).get_player(1).get("wraithPowerSpent", 0) == 0


def test_blueprint_energy_is_not_shared_or_multiplied_by_ship_count(make_game, run):
    game = phase_combat(make_game, blue_ships=("blue-int", "blue-int", "blue-cru"))
    player = game.get_player(1)
    player["base_interceptor_nrg"] += 1 - PlayerShip(player, "interceptor").energy
    player["base_cruiser_nrg"] -= PlayerShip(player, "cruiser").energy
    channel = FakeInteraction().channel
    message = offer_phase(game, channel)
    for ship, option in [("interceptor", "speed"), ("cruiser", "comp")]:
        interaction = FakeInteraction(channel, message=message)
        run(Combat.phaseModuleOption(game, f"phaseModuleOption_101_blue_{ship}_{option}", interaction))
        assert "Not enough power" in interaction.followup.sent[0][0]


def test_phase_options_share_the_same_blueprint_energy(make_game, run):
    game = phase_combat(make_game)
    channel = FakeInteraction().channel
    message = offer_phase(game, channel)
    first = FakeInteraction(channel, message=message)
    run(Combat.phaseModuleOption(game, "phaseModuleOption_101_blue_interceptor_comp", first))
    second = FakeInteraction(channel, message=message)
    run(Combat.phaseModuleOption(game, "phaseModuleOption_101_blue_interceptor_shield", second))
    assert "Not enough power" in second.followup.sent[0][0]
    mode = Combat.phase_mode(game, "blue", "101", "interceptor")
    assert mode["comp"] == 1
    assert not mode["shield"]


def test_unused_blueprint_energy_is_available_again_next_combat(make_game, run, monkeypatch):
    game = phase_combat(make_game)
    player = game.get_player(1)
    energy = PlayerShip(player, "interceptor").energy

    async def prompt(game, pos, channel, update):
        return None

    monkeypatch.setattr(Combat, "promptNextSpeed", prompt)
    for _ in range(2):
        channel = FakeInteraction().channel
        message = offer_phase(game, channel)
        run(Combat.phaseModuleOption(game, "phaseModuleOption_101_blue_interceptor_comp",
                                    FakeInteraction(channel, message=message)))
        assert Combat.phase_mode(game, "blue", "101", "interceptor")["comp"] == 1
        run(Combat.phaseModuleDone(game, "phaseModuleDone_101_blue",
                                  FakeInteraction(channel, message=message)))
        game = reload(game)
        assert PlayerShip(game.get_player(1), "interceptor").energy == energy
        assert game.get_player(1).get("wraithPowerSpent", 0) == 0
        Combat.clear_phase_module(game, "101")


@pytest.mark.parametrize("souls, is_valid", [(0, False), (1, False), (2, True), (3, True)])
def test_upgrade_uses_permanent_soul_power(start_game, run, souls, is_valid):
    game, channel = start_game(factions=["wra", "eri"])
    player = game.get_player(1)
    player["wraithSouls"] = souls
    player["wraithPowerSpent"] = 9  # Older saves must not lose their permanent bonus.
    game.update()
    interaction = FakeInteraction(channel)
    run(UpgradeButtons.chooseUpgrade(game, player, interaction,
                                     "chooseUpgrade_2_interceptor_nus_hul_1_dummy",
                                     PlayerHelper("1", player)))

    player = reload(game).get_player(1)
    assert (player["interceptor_parts"][1] == "hul") is is_valid
    assert player["wraithSouls"] == souls
    if is_valid:
        ship = PlayerShip(player, "interceptor")
        assert ship.energy == souls - 2
        assert ship.total_energy == souls
    else:
        assert "not valid" in interaction.followup.sent[0][0]


def test_neutron_bombs_and_initiative_share_one_two_power_purchase(make_game, run):
    game = phase_combat(make_game)
    player = game.get_player(1)
    player["military_tech"] = ["phm", "neb"]
    player["base_interceptor_nrg"] += 2  # three power available
    game.update()
    channel = FakeInteraction().channel
    message = offer_phase(game, channel)

    assert any("Ignore Shields (3)" in content for content, _kwargs in channel.sent)
    for option in ("speed", "planets"):
        inter = FakeInteraction(channel, message=message)
        run(Combat.phaseModuleOption(game, f"phaseModuleOption_101_blue_interceptor_{option}", inter))
        assert not inter.followup.sent

    mode = Combat.phase_mode(game, "blue", "101", "interceptor")
    assert mode["speed"] and mode["planets"]
    assert mode["cost"] == 2
