from helpers.CombatHelper import Combat
from helpers.Turtugan import Carapace
from tests.fakes import (FakeChannel, FakeInteraction, buttons, offered_ids, player_stats, reload)


def combat_game(make_game, tur_parts=None, tur_ships=("teal-int",), red_ships=("red-cru",)):
    tur = player_stats("tur", color="teal")
    if tur_parts:
        tur["interceptor_parts"] = tur_parts
    red = player_stats("eri", color="red")
    tile = {"sector": 202, "orientation": 0, "wormholes": [0, 1, 3, 4], "owner": "red",
            "player_ships": list(tur_ships) + list(red_ships),
            "attacker": ["teal"], "defender": ["red"], "disctile": 0}
    return make_game({"players": {"1": tur, "2": red}, "board": {"202": tile}})


def channel():
    return FakeChannel("t-actions")


def engage(game, ship_class, color="teal"):
    tile = game.gamestate["board"]["202"]
    state = tile.setdefault("carapaceShields", {}).setdefault(color, {})
    state[ship_class] = True
    state["token"] = state.get("token", 0) + 1
    state["done"] = True
    game.update()


def test_offer_only_lists_classes_the_turtugan_has_in_the_battle(make_game, run):
    game = combat_game(make_game)
    ch = channel()
    run(Carapace.offer(game, ch, "202"))
    ids = buttons(ch)
    assert any(cid.startswith("FCIDteal_carapaceToggle_202_interceptor_") for cid in ids)
    assert not any("_cruiser_" in cid or "_dread_" in cid or "_starbase_" in cid for cid in ids)
    assert any(cid.startswith("FCIDteal_carapaceDone_202_") for cid in ids)


def test_toggle_done_and_stale_prompt(make_game, run, press):
    game = combat_game(make_game)
    ch = channel()
    run(Carapace.offer(game, ch, "202"))
    toggle_id = next(cid for cid in buttons(ch) if "carapaceToggle_202_interceptor" in cid)
    done_id = next(cid for cid in buttons(ch) if "carapaceDone_202" in cid)

    inter = press(ch, 1, toggle_id)
    assert reload(game).gamestate["board"]["202"]["carapaceShields"]["teal"]["interceptor"] is True
    labels = [child.label for child in inter.message.edited["view"].children]
    assert "Interceptor: ON" in labels

    toggle_message = inter.message
    press(ch, 1, done_id, message=toggle_message)
    state = reload(game).gamestate["board"]["202"]["carapaceShields"]["teal"]
    assert state["done"] is True
    assert state["interceptor"] is True

    inter2 = FakeInteraction(ch, custom_id=toggle_id)
    state = reload(game)
    run(Carapace.toggle(state, state.get_player(1), inter2, toggle_id))
    assert "no longer current" in inter2.followup.sent[0][0]
    assert reload(game).gamestate["board"]["202"]["carapaceShields"]["teal"]["interceptor"] is True


def test_weapon_damage_is_reduced_by_one_to_zero(make_game, run, no_random):
    game = combat_game(make_game)
    engage(game, "interceptor")
    ch = channel()
    no_random([6])
    inter = FakeInteraction(ch, custom_id="rollDice_202_teal_1_attacker")
    run(Combat.rollDice(game, inter.data["custom_id"], inter))
    assert reload(game).gamestate["board"]["202"]["damage_tracker"]["red-cru"] == 0


def test_two_damage_weapon_becomes_one(make_game, run, no_random):
    game = combat_game(make_game, tur_parts=["plc", "nus", "nud"])
    engage(game, "interceptor")
    ch = channel()
    no_random([6])
    inter = FakeInteraction(ch, custom_id="rollDice_202_teal_1_attacker")
    run(Combat.rollDice(game, inter.data["custom_id"], inter))
    assert reload(game).gamestate["board"]["202"]["damage_tracker"]["red-cru"] == 1


def test_one_damage_dice_are_reduced_one_by_one_not_pooled(make_game, run, no_random):
    game = combat_game(make_game, tur_parts=["iot", "nud"])  # two ion dice, 1 damage each
    engage(game, "interceptor")
    ch = channel()
    no_random([6, 6])
    inter = FakeInteraction(ch, custom_id="rollDice_202_teal_1_attacker")
    run(Combat.rollDice(game, inter.data["custom_id"], inter))
    assert reload(game).gamestate["board"]["202"]["damage_tracker"]["red-cru"] == 0


def test_antimatter_die_is_reduced_before_it_splits(make_game, run, no_random):
    game = combat_game(make_game, tur_parts=["anc", "nud"], red_ships=("red-drd",))
    game.gamestate["players"]["1"]["military_tech"] = ["ans"]  # Antimatter Split
    game.gamestate["players"]["2"]["dread_parts"] = ["hul", "hul", "hul", "hul"]  # survives 3 hits
    game.update()
    engage(game, "interceptor")
    ch = channel()
    no_random([6])
    inter = FakeInteraction(ch, custom_id="rollDice_202_teal_1_attacker")
    run(Combat.rollDice(game, inter.data["custom_id"], inter))
    # the 4 damage die becomes 3, then splits into three 1 damage hits
    assert reload(game).gamestate["board"]["202"]["damage_tracker"]["red-drd"] == 3


def test_unengaged_class_keeps_its_damage(make_game, run, no_random):
    game = combat_game(make_game, tur_parts=["plc", "nus", "nud"], red_ships=("red-drd",))
    engage(game, "cruiser")
    ch = channel()
    no_random([6])
    inter = FakeInteraction(ch, custom_id="rollDice_202_teal_1_attacker")
    run(Combat.rollDice(game, inter.data["custom_id"], inter))
    assert reload(game).gamestate["board"]["202"]["damage_tracker"]["red-drd"] == 2


def test_incoming_damage_is_reduced_but_never_below_one(make_game, run):
    game = combat_game(make_game, tur_ships=("teal-cru",), red_ships=("red-cru",))
    engage(game, "cruiser")
    ch = channel()

    run(Combat.assignHitTo(game, "assignHitTo_202_red_teal-cru_6_3", FakeInteraction(ch), False))
    assert reload(game).gamestate["board"]["202"]["damage_tracker"]["teal-cru"] == 2

    game = combat_game(make_game, tur_ships=("teal-cru",), red_ships=("red-cru",))
    engage(game, "cruiser")
    run(Combat.assignHitTo(game, "assignHitTo_202_red_teal-cru_6_1", FakeInteraction(ch), False))
    assert reload(game).gamestate["board"]["202"]["damage_tracker"]["teal-cru"] == 1


def test_carapace_does_not_apply_to_another_faction(make_game, run):
    game = combat_game(make_game, red_ships=("red-cru",))
    game.gamestate["board"]["202"]["player_ships"] = ["blue-drd", "red-cru"]
    blue = player_stats("hyd", color="blue")
    game.gamestate["players"]["1"] = blue
    game.gamestate["board"]["202"]["carapaceShields"] = {"blue": {"dread": True, "token": 1, "done": True}}
    game.update()
    ch = channel()
    run(Combat.assignHitTo(game, "assignHitTo_202_red_blue-drd_6_2", FakeInteraction(ch), False))
    assert reload(game).gamestate["board"]["202"]["damage_tracker"]["blue-drd"] == 2


def missile_game(make_game):
    game = combat_game(make_game, tur_ships=("teal-cru",), red_ships=("red-cru",))
    game.gamestate["players"]["2"]["cruiser_parts"] = ["elc", "ioc", "anm", "nus", "hul", "nud"]
    game.gamestate["players"]["1"]["cruiser_parts"] = ["hul", "hul", "hul", "hul"]  # survives a 4-damage die
    game.update()
    return game


def test_shielded_ships_own_missile_also_loses_one_damage(make_game, run, no_random):
    game = combat_game(make_game, tur_ships=("teal-cru",), red_ships=("red-sb",))
    game.gamestate["players"]["1"]["cruiser_parts"] = ["elc", "ioc", "anm", "nus", "hul", "nud"]
    game.gamestate["players"]["2"]["starbase_parts"] = ["elc", "ioc", "hul", "hul", "hul"]
    game.update()
    engage(game, "cruiser")
    ch = channel()
    no_random([6])
    inter = FakeInteraction(ch, custom_id="rollDice_202_teal_100_attacker")
    run(Combat.rollDice(game, inter.data["custom_id"], inter))

    assert reload(game).gamestate["board"]["202"]["damage_tracker"]["red-sb"] == 3


def test_missile_can_take_minus_one_to_hit(make_game, run, no_random, press):
    game = missile_game(make_game)
    engage(game, "cruiser")
    ch = channel()
    no_random([5])
    inter = FakeInteraction(ch, custom_id="rollDice_202_red_101_attacker")
    run(Combat.rollDice(game, inter.data["custom_id"], inter))
    assert any("FCIDred_carapaceMissile_202_damage_" in cid for cid in buttons(ch))
    hit_id = next(cid for cid in buttons(ch) if "FCIDred_carapaceMissile_202_hit_" in cid)
    press(ch, 2, hit_id)
    state = reload(game).gamestate["board"]["202"]
    assert state.get("carapacePendingMissiles") in ([], None)
    assert state.get("damage_tracker", {}).get("teal-cru", 0) == 0


def test_missile_can_take_minus_one_damage(make_game, run, no_random, press):
    game = missile_game(make_game)
    engage(game, "cruiser")
    ch = channel()
    no_random([6])
    inter = FakeInteraction(ch, custom_id="rollDice_202_red_101_attacker")
    run(Combat.rollDice(game, inter.data["custom_id"], inter))
    damage_id = next(cid for cid in buttons(ch) if "FCIDred_carapaceMissile_202_damage_" in cid)
    press(ch, 2, damage_id)
    assert reload(game).gamestate["board"]["202"]["damage_tracker"]["teal-cru"] == 3


def test_missile_minus_one_to_hit_keeps_full_damage(make_game, run, no_random, press):
    game = missile_game(make_game)
    engage(game, "cruiser")
    ch = channel()
    no_random([6])
    inter = FakeInteraction(ch, custom_id="rollDice_202_red_101_attacker")
    run(Combat.rollDice(game, inter.data["custom_id"], inter))
    press(ch, 2, next(cid for cid in buttons(ch) if "FCIDred_carapaceMissile_202_hit_" in cid))
    assert reload(game).gamestate["board"]["202"]["damage_tracker"]["teal-cru"] == 4


def test_a_double_pressed_missile_choice_applies_once(make_game, run, no_random, press):
    game = missile_game(make_game)
    engage(game, "cruiser")
    ch = channel()
    no_random([6])
    inter = FakeInteraction(ch, custom_id="rollDice_202_red_101_attacker")
    run(Combat.rollDice(game, inter.data["custom_id"], inter))
    damage_id = next(cid for cid in buttons(ch) if "FCIDred_carapaceMissile_202_damage_" in cid)
    inter = press(ch, 2, damage_id)
    handler_id = damage_id.replace("FCIDred_", "")
    inter2 = FakeInteraction(ch, custom_id=handler_id)
    state = reload(game)
    run(Carapace.resolve_missile(state, state.get_player(2), inter2, handler_id))
    assert reload(game).gamestate["board"]["202"]["damage_tracker"]["teal-cru"] == 3
    assert "already resolved" in inter2.followup.sent[0][0]


def test_start_combat_offers_and_a_new_round_reoffers(make_game, run):
    game = combat_game(make_game)
    ch = channel()
    run(Combat.startCombat(game, ch, "202"))
    state = reload(game).gamestate["board"]["202"]
    first_token = state["carapaceShields"]["teal"]["token"]
    assert any("carapaceToggle_202_interceptor" in cid for cid in offered_ids(FakeInteraction(ch)))

    game = reload(game)
    game.gamestate["board"]["202"]["currentSpeed"] = 0
    game.gamestate["board"]["202"]["currentRoller"] = ""
    game.update()
    run(Combat.promptNextSpeed(game, "202", ch, False))
    second_token = reload(game).gamestate["board"]["202"]["carapaceShields"]["teal"]["token"]
    assert second_token > first_token


def test_a_new_combat_does_not_accept_an_old_toggle(make_game, run):
    game = combat_game(make_game)
    ch = channel()
    run(Carapace.offer(game, ch, "202"))
    old_id = next(cid for cid in buttons(ch) if "carapaceToggle_202_interceptor" in cid)
    Carapace.clear(game, "202")
    run(Carapace.offer(reload(game), ch, "202"))
    inter = FakeInteraction(ch, custom_id=old_id.replace("FCIDteal_", ""))
    state = reload(game)
    run(Carapace.toggle(state, state.get_player(1), inter, inter.data["custom_id"]))
    assert "no longer current" in inter.followup.sent[0][0]
    assert reload(game).gamestate["board"]["202"]["carapaceShields"]["teal"]["interceptor"] is False


def test_clear_only_touches_one_tile(make_game):
    game = combat_game(make_game)
    engage(game, "interceptor")
    game.gamestate["board"]["203"] = {"sector": 203, "orientation": 0, "player_ships": [],
                                      "carapaceShields": {"teal": {"interceptor": True}}}
    game.update()
    Carapace.clear(game, "202")
    state = reload(game).gamestate["board"]
    assert "carapaceShields" not in state["202"]
    assert state["203"]["carapaceShields"]["teal"]["interceptor"] is True


def test_declaring_a_winner_clears_the_shields(make_game, run):
    game = combat_game(make_game, red_ships=())
    engage(game, "interceptor")
    ch = channel()
    run(Combat.declareAWinner(game, FakeInteraction(ch), "202"))
    assert "carapaceShields" not in reload(game).gamestate["board"]["202"]


def test_a_cleared_prompt_refuses_a_stale_toggle(make_game, run):
    game = combat_game(make_game)
    engage(game, "interceptor")
    ch = channel()
    Carapace.clear(game, "202")
    inter = FakeInteraction(ch, custom_id="carapaceToggle_202_interceptor_1")
    state = reload(game)
    run(Carapace.toggle(state, state.get_player(1), inter, "carapaceToggle_202_interceptor_1"))
    assert "no longer current" in inter.followup.sent[0][0]


def test_unfinished_carapace_menu_closes_when_firing_starts(make_game, run, no_random):
    game = combat_game(make_game)
    ch = channel()
    run(Carapace.offer(game, ch, "202"))
    toggle_id = next(cid for cid in buttons(ch) if "carapaceToggle_202_interceptor" in cid)
    no_random([1])
    run(Combat.rollDice(game, "rollDice_202_red_2_attacker", FakeInteraction(ch)))
    inter = FakeInteraction(ch)
    run(Carapace.toggle(game, game.get_player(1), inter, toggle_id))
    assert "no longer current" in inter.followup.sent[0][0]
    assert not Carapace.engaged(game, "202", "teal", "interceptor")

    run(Carapace.offer(game, ch, "202"))
    token = game.gamestate["board"]["202"]["carapaceShields"]["teal"]["token"]
    new_id = f"carapaceToggle_202_interceptor_{token}"
    run(Carapace.toggle(game, game.get_player(1), FakeInteraction(ch), new_id))
    assert Carapace.engaged(game, "202", "teal", "interceptor")
