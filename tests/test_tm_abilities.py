"""Techno-Mages species rules: Limited Manufacturing, Technology finds a Way, Techno-Magic.

All three were read off the faction's printed card: one Build activation and one colony ship
per Influence action, two colony ships reaching an Advanced planet the techs do not unlock,
and one temporary Upgrade 1 per ship blueprint at the start of each combat.
"""
import pytest

from Buttons.Build import BuildButtons
from helpers.CombatHelper import Combat
from tests.fakes import FakeInteraction, buttons, reload


# A ring 1 sector with an advanced science square (data/sectors.json), free in a two player start.
ADVANCED_SECTOR = "104"


def place_advanced_square(game):
    game.add_tile("205", 0, ADVANCED_SECTOR)
    game.gamestate["board"]["205"]["owner"] = "blue"
    game.get_player(1)["owned_tiles"].append("205")
    game.update()


def install_part(press, channel, pos="201", part="hul"):
    """Techno-Magic on the interceptor's empty slot; returns the part choices offered."""
    inter = press(channel, 1, f"FCIDblue_technoMagic_{pos}_interceptor")
    slot = next(c.custom_id for c in inter.message.edited["view"].children if c.custom_id.endswith(f"_tm{pos}_3"))
    inter = press(channel, 1, slot)
    choices = {c.custom_id for c in inter.message.edited["view"].children
               if c.custom_id.startswith("FCIDblue_chooseUpgrade_")}
    press(channel, 1, next(cid for cid in choices if cid.endswith(f"_{part}_3_tm{pos}")))
    return choices


# --- Limited Manufacturing ---------------------------------------------------

@pytest.mark.parametrize("faction, refused", [("tm", True), ("eri", False)])
def test_only_one_unit_per_build_action(start_game, run, faction, refused):
    game, channel = start_game(factions=[faction, "hyd"])
    inter = FakeInteraction(channel)
    run(BuildButtons.buildShip(game, game.get_player(1), inter, "buildShip_int_3_201_Cruiser"))

    refused_message = "cannot build any more units" in inter.message.edited["content"]
    assert refused_message == refused


def test_the_build_menu_offers_one_activation(start_game, press):
    game, channel = start_game(factions=["tm", "eri"])

    press(channel, 1, "FCIDblue_startBuild")
    press(channel, 1, "FCIDblue_buildIn_201")

    assert any("up to 1 units" in content for content, _ in channel.sent)


# --- Limited Manufacturing: the Influence action ------------------------------

# --- Technology finds a Way ---------------------------------------------------

def test_two_colony_ships_reach_an_advanced_planet_the_techs_do_not_unlock(start_game, press):
    game, channel = start_game(factions=["tm", "eri"])
    place_advanced_square(game)
    ships = game.get_player(1)["colony_ships"]

    press(channel, 1, "FCIDblue_startPopDrop")
    assert "FCIDblue_fillPopulation_205_scienceadv_0" in buttons(channel)
    press(channel, 1, "FCIDblue_fillPopulation_205_scienceadv_0")

    state = reload(game)
    assert state.gamestate["board"]["205"]["scienceadv_pop"] == [1]
    # The cube is of the correct type: it comes off the science track.
    assert state.get_player(1)["science_pop_cubes"] == 9
    # Two colony ships went into it.
    assert state.get_player(1)["colony_ships"] == ships - 2


def test_the_advanced_planet_costs_one_ship_once_the_tech_is_researched(start_game, press):
    game, channel = start_game(factions=["tm", "eri"])
    place_advanced_square(game)
    game.get_player(1)["nano_tech"].append("adl")
    game.update()

    press(channel, 1, "FCIDblue_startPopDrop")
    press(channel, 1, "FCIDblue_fillPopulation_205_scienceadv_0")

    state = reload(game)
    assert state.gamestate["board"]["205"]["scienceadv_pop"] == [1]
    assert state.get_player(1)["colony_ships"] == 2


def test_other_factions_do_not_reach_the_advanced_planet(start_game, press):
    # Remnants of Ra start with no technologies, so nothing unlocks the square for them.
    game, channel = start_game(factions=["ra", "eri"])
    place_advanced_square(game)

    press(channel, 1, "FCIDblue_startPopDrop")

    assert not [cid for cid in buttons(channel) if "scienceadv" in cid]


def test_one_colony_ship_is_not_enough(start_game, press):
    game, channel = start_game(factions=["tm", "eri"])
    place_advanced_square(game)
    game.get_player(1)["colony_ships"] = 1
    game.update()

    press(channel, 1, "FCIDblue_startPopDrop")

    assert not [cid for cid in buttons(channel) if "scienceadv" in cid]


# --- Techno-Magic -------------------------------------------------------------

def test_techno_magic_offers_one_upgrade_per_ship_blueprint(start_game, run):
    game, channel = start_game(factions=["tm", "eri"])
    game.gamestate["board"]["201"]["player_ships"] = ["blue-int", "blue-cru", "red-int"]
    game.gamestate["board"]["201"]["attacker"] = "red"
    game.gamestate["board"]["201"]["defender"] = "blue"
    game.update()

    run(Combat.offerTechnoMagic(game, channel, "201"))

    menu = buttons(channel)
    for ship in ("interceptor", "cruiser"):
        assert f"FCIDblue_technoMagic_201_{ship}" in menu
    assert not [cid for cid in menu if cid.startswith("FCIDred_")]
    assert not [cid for cid in menu if cid.endswith(("_dread", "_starbase"))]


def test_techno_magic_is_not_offered_to_other_factions(start_game, run):
    game, channel = start_game(factions=["hyd", "eri"])
    game.gamestate["board"]["201"]["player_ships"] = ["blue-int", "red-int"]
    game.update()

    run(Combat.offerTechnoMagic(game, channel, "201"))

    assert not [cid for cid in buttons(channel) if "technoMagic" in cid]


def test_techno_magic_installs_a_part_without_spending_a_disc(start_game, press):
    game, channel = start_game(factions=["tm", "eri"])
    discs = game.get_player(1)["influence_discs"]

    choices = install_part(press, channel)

    # no 'empty' (ship parts may not be removed) and no discovery part (no Ancient ship parts)
    assert {cid.split("_")[5] for cid in choices} == {"ioc", "elc", "nud", "hul", "nus"}

    state = reload(game)
    assert state.get_player(1)["interceptor_parts"] == ["ioc", "nus", "nud", "hul"]
    assert state.get_player(1)["influence_discs"] == discs
    record = state.gamestate["board"]["201"]["tmParts"]["blue"]["interceptor"]
    assert record["base"] == ["ioc", "nus", "nud", "empty"]
    # the record survives the save-file round trip, so tuples come back as lists
    assert record["install"] == [3, "empty", "hul"]
    # once per blueprint per combat
    inter = press(channel, 1, "FCIDblue_technoMagic_201_interceptor")
    assert any("already upgraded" in str(item) for item in inter.followup.sent)


def test_techno_magic_parts_come_off_when_the_combat_ends(start_game, press, run):
    game, channel = start_game(factions=["tm", "eri"])
    install_part(press, channel)
    assert reload(game).get_player(1)["interceptor_parts"] == ["ioc", "nus", "nud", "hul"]

    # the presses run on their own gamestate instances; declareAWinner sees the saved one
    game = reload(game)
    run(Combat.revertTechnoMagic(game, channel, "201"))

    state = reload(game)
    assert state.get_player(1)["interceptor_parts"] == ["ioc", "nus", "nud", "empty"]
    assert "tmParts" not in state.gamestate["board"]["201"]


def test_a_new_pairing_on_the_tile_is_a_new_techno_magic_combat(start_game, press, run):
    """startCombat reruns when a player leaves a multi-player tile: last pairing's part comes off
    and the upgrade is offered again."""
    game, channel = start_game(factions=["tm", "eri"])
    game.gamestate["board"]["201"]["player_ships"] = ["blue-int", "red-int"]
    game.update()
    install_part(press, channel)

    game = reload(game)
    run(Combat.startCombat(game, channel, "201"))

    state = reload(game)
    assert state.get_player(1)["interceptor_parts"] == ["ioc", "nus", "nud", "empty"]
    assert any(button.custom_id == "FCIDblue_technoMagic_201_interceptor"
               for content, kwargs in channel.sent for button in getattr(kwargs.get("view"), "children", []))


def test_undo_frees_the_blueprint_for_another_techno_magic_part(start_game, press):
    game, channel = start_game(factions=["tm", "eri"])
    install_part(press, channel)

    press(channel, 1, "FCIDblue_undoUpgrade_1_tm201_interceptor")

    state = reload(game)
    assert state.get_player(1)["interceptor_parts"] == ["ioc", "nus", "nud", "empty"]
    assert "install" not in state.gamestate["board"]["201"]["tmParts"]["blue"]["interceptor"]


def test_undo_buttons_posted_before_the_mode_was_added_still_work(start_game, press):
    game, channel = start_game(factions=["eri", "hyd"])
    game.get_player(1)["upgradeUndo"] = dict(game.get_player(1))
    game.update()

    press(channel, 1, "FCIDblue_undoUpgrade_2")

    assert any("undid their last part swap" in content for content, _ in channel.sent)


def test_two_pending_combats_do_not_strip_each_others_parts(start_game, press, run):
    """A blueprint upgraded for two simultaneous fights keeps the other fight's part
    until that fight resolves too, and ends back at the pre-combat blueprint."""
    game, channel = start_game(factions=["tm", "eri"])
    game.add_tile("205", 0, "104")
    for pos in ("201", "205"):
        game.gamestate["board"][pos]["player_ships"] = ["blue-int", "red-int"]
    game.update()

    for pos, part in (("201", "hul"), ("205", "elc")):
        install_part(press, channel, pos, part)

    assert reload(game).get_player(1)["interceptor_parts"] == ["ioc", "nus", "nud", "elc"]
    # each revert runs on the gamestate as it is on disk at that moment
    game = reload(game)
    run(Combat.revertTechnoMagic(game, channel, "201"))
    # 205's temporary part must survive 201's combat ending
    assert reload(game).get_player(1)["interceptor_parts"] == ["ioc", "nus", "nud", "elc"]
    game = reload(game)
    run(Combat.revertTechnoMagic(game, channel, "205"))
    assert reload(game).get_player(1)["interceptor_parts"] == ["ioc", "nus", "nud", "empty"]
    assert "tmParts" not in reload(game).gamestate["board"]["201"]


def test_flux_missile_fires_before_the_ancient_it_tied_with(start_game, press, run):
    """A Techno-Magic part can raise initiative or add missiles, so initiative waits for it."""
    game, channel = start_game(factions=["tm", "eri"])
    game.get_player(1)["military_tech"].append("flm")
    tile = game.gamestate["board"]["201"]
    tile.update({"owner": 0, "player_ships": ["ai-anc", "blue-int"]})
    # A WA Ancient has initiative 3, tying the unupgraded interceptor; the defender wins
    # that tie, so the Ancients would fire first without the Flux Missile.
    game.gamestate.update({"advanced_ai": False, "wa_ai": False, "anc_type": "wa"})
    game.setAttackerAndDefender(["blue"], ["ai"], "201")
    tile["firstShotSide"] = []
    tile["firstShotPhase"] = None
    game.update()

    run(Combat.startCombat(game, channel, "201"))
    assert not any("rollDice" in cid for cid in buttons(channel))

    inter = press(channel, 1, "FCIDblue_technoMagic_201_interceptor")
    slot = next(c.custom_id for c in inter.message.edited["view"].children if c.custom_id.endswith("_tm201_3"))
    inter = press(channel, 1, slot)
    part = next(c.custom_id for c in inter.message.edited["view"].children
                if c.custom_id.endswith("_flm_3_tm201"))
    press(channel, 1, part)
    press(channel, 1, "FCIDblue_finishTechnoMagic_201")

    state = reload(game)
    assert (state.gamestate["board"]["201"]["currentSpeed"],
            state.gamestate["board"]["201"]["currentRoller"]) == (103, "blue")


@pytest.mark.parametrize("first", ["techno_magic", "phase_module"])
def test_initiative_waits_for_both_techno_magic_and_phase_module(start_game, run, first):
    game, channel = start_game(factions=["tm", "wra"])
    tile = game.gamestate["board"]["201"]
    tile["player_ships"] = ["blue-int", "red-int"]
    tile["attacker"], tile["defender"] = "blue", "red"
    game.update()
    run(Combat.startCombat(game, channel, "201"))

    def finish(ability):
        interaction = FakeInteraction(channel)
        if ability == "techno_magic":
            run(Combat.technoMagicDone(game, "finishTechnoMagic_201", game.get_player(1), interaction))
        else:
            run(Combat.phaseModuleDone(game, "phaseModuleDone_201_red", interaction))

    finish(first)
    assert "currentSpeed" not in tile
    assert not any("rollDice" in cid for cid in buttons(channel))

    finish("phase_module" if first == "techno_magic" else "techno_magic")
    assert (tile["currentSpeed"], tile["currentRoller"]) == (3, "blue")


def test_the_attacker_is_offered_the_upgrade_first(start_game, run):
    """Where timing matters, the defender chooses last."""
    game, channel = start_game(factions=["tm", "tm"])
    game.gamestate["board"]["201"]["player_ships"] = ["blue-int", "red-int"]
    game.gamestate["board"]["201"]["attacker"] = "red"
    game.gamestate["board"]["201"]["defender"] = "blue"
    game.update()

    run(Combat.offerTechnoMagic(game, channel, "201"))

    offers = [kwargs.get("view") for content, kwargs in channel.sent
              if any("technoMagic" in getattr(b, "custom_id", "")
                     for b in getattr(kwargs.get("view"), "children", []))]
    assert all(b.custom_id.startswith("FCIDred_") for b in offers[0].children)
    assert all(b.custom_id.startswith("FCIDblue_") for b in offers[1].children)


def test_grey_advanced_squares_take_any_cube_for_two_ships(start_game, press):
    # Technology finds a Way reaches a grey Advanced square too; any cube type fits it
    game, channel = start_game(factions=["tm", "eri"])
    place_advanced_square(game)
    game.gamestate["board"]["205"]["neutraladv_pop"] = [0]
    game.update()
    ships = game.get_player(1)["colony_ships"]

    press(channel, 1, "FCIDblue_startPopDrop")
    assert "FCIDblue_fillPopulation_205_neutraladv_0" in buttons(channel)
    press(channel, 1, "FCIDblue_fillPopulation_205_neutraladv_0")
    assert {"FCIDblue_fillPopulation_205_neutraladv_0_money", "FCIDblue_fillPopulation_205_neutraladv_0_science",
            "FCIDblue_fillPopulation_205_neutraladv_0_material"} <= set(buttons(channel))
    press(channel, 1, "FCIDblue_fillPopulation_205_neutraladv_0_money")

    state = reload(game)
    assert state.gamestate["board"]["205"]["neutraladv_pop"] == [1]
    assert state.get_player(1)["colony_ships"] == ships - 2


def test_techno_magic_keeps_other_combat_blueprints_available(start_game, press, run):
    game, channel = start_game(factions=["tm", "eri"])
    tile = game.gamestate["board"]["201"]
    tile["player_ships"] = ["blue-int", "blue-cru", "red-drd"]
    tile["attacker"], tile["defender"] = "red", "blue"
    game.update()
    run(Combat.offerTechnoMagic(game, channel, "201"))

    inter = press(channel, 1, "FCIDblue_technoMagic_201_cruiser")
    slot = next(c.custom_id for c in inter.message.edited["view"].children
                if "_selectOldPart_" in c.custom_id and "_empty_" in c.custom_id)
    inter = press(channel, 1, slot)
    choice = next(c.custom_id for c in inter.message.edited["view"].children
                  if "_chooseUpgrade_" in c.custom_id and "_hul_" in c.custom_id)
    press(channel, 1, choice)

    menu = channel.sent[-1][1]["view"]
    assert {c.custom_id for c in menu.children} == {
        "FCIDblue_technoMagic_201_interceptor", "FCIDblue_undoUpgrade_1_tm201_cruiser",
        "FCIDblue_finishTechnoMagic_201",
        "FCIDblue_restartTechnoMagic_201", "FCIDblue_refreshCombatPrompt_201"}
    install_part(press, channel)
    state = reload(game)
    assert set(state.gamestate["board"]["201"]["tmParts"]["blue"]) == {"cruiser", "interceptor"}
    run(Combat.revertTechnoMagic(state, channel, "201"))
    assert reload(game).get_player(1)["cruiser_parts"] == game.get_player(1)["cruiser_parts"]
    assert reload(game).get_player(1)["interceptor_parts"] == game.get_player(1)["interceptor_parts"]
