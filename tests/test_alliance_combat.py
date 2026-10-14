"""Combat pairs SIDES, not colours: allies fight together and never each other."""
import asyncio

import pytest

from helpers.CombatHelper import Combat
from tests.fakes import FakeInteraction, POS, board_tile, offered_ids, offered_labels, player_stats, players


def _game(make_game, colors, ships, attacker=None, defender=None, owner=0, entry=None):
    board = board_tile(ships, owner)
    if attacker is not None:
        board[POS]["attacker"] = attacker
    if defender is not None:
        board[POS]["defender"] = defender
    if entry is not None:
        board[POS]["entryOrder"] = list(entry)
    return make_game({"player_count": len(colors), "players": players(*colors), "board": board})


def _sides(game):
    return Combat.findSidesInTile(game, POS)


def _reputation_colors(interaction):
    """Colours asked to draw reputation, in the order the prompts were sent."""
    return [button_id.split("_")[0][4:] for button_id in offered_ids(interaction)
            if "drawReputation" in button_id]


async def _pair(game):
    """Run the pairing step, which records the combatants and attacker/defender."""
    Combat.getCombatButtons(game, POS)


async def _noop(*_args, **_kwargs):
    return None


def _record_declared_winners(monkeypatch):
    declared = []

    async def declare_winner(_game, _interaction, pos):
        declared.append(pos)

    monkeypatch.setattr(Combat, "declareAWinner", staticmethod(declare_winner))
    return declared


class TestSidesInTile:
    def test_unallied_players_are_each_their_own_side(self, make_game):
        game = _game(make_game, ("blue", "red", "green"), ["blue-cru", "red-cru", "green-cru"])
        assert _sides(game) == [["blue"], ["red"], ["green"]]

    def test_allies_alone_are_not_flagged_as_a_conflict(self, make_game):
        game = _game(make_game, ("blue", "red"), ["blue-cru", "red-cru"])
        game.formAlliance("nova", ["blue", "red"])

        assert Combat.findTilesInConflict(game) == []

    def test_an_alliance_is_one_side_for_contention_and_unowned_takeover(self, make_game):
        game = _game(make_game, ("blue", "red", "green"), ["blue-cru", "red-cru"], owner="green")
        game.formAlliance("nova", ["blue", "red"])

        assert Combat.findTilesInContention(game) == [(101, POS)]
        unowned = _game(make_game, ("blue", "red", "green"), ["blue-cru", "red-cru"])
        unowned.formAlliance("nova", ["blue", "red"])
        assert Combat.findUnownedTilesToTakeOver(unowned) == [(101, POS)]

    def test_an_ally_is_not_offered_to_bomb_its_allys_sector(self, make_game):
        game = _game(make_game, ("blue", "red"), ["blue-cru"], owner="red")
        game.formAlliance("nova", ["blue", "red"])

        assert Combat.findTilesInContention(game) == []

    @pytest.mark.parametrize("ship_order", [("blue", "red", "green"), ("blue", "green", "red")])
    def test_an_alliance_is_one_side_wherever_its_members_sit_in_the_ship_list(self, make_game, ship_order):
        game = _game(make_game, ship_order, [f"{color}-cru" for color in ship_order])
        game.formAlliance("nova", ["blue", "red"])
        assert _sides(game) == [["blue", "red"], ["green"]]

    def test_two_alliances_are_two_sides(self, make_game):
        game = _game(make_game, ("blue", "red", "green", "yellow"),
                     ["blue-cru", "red-cru", "green-cru", "yellow-cru"])
        game.formAlliance("nova", ["blue", "red"])
        game.formAlliance("flare", ["green", "yellow"])
        assert _sides(game) == [["blue", "red"], ["green", "yellow"]]

    def test_the_ai_is_always_its_own_side(self, make_game):
        game = _game(make_game, ("blue", "red"), ["ai-anc", "blue-cru", "red-cru"])
        game.formAlliance("nova", ["blue", "red"])
        assert _sides(game) == [["ai"], ["blue", "red"]]

    def test_a_betrayer_is_no_longer_on_the_side(self, make_game):
        game = _game(make_game, ("blue", "red", "green"), ["blue-cru", "red-cru", "green-cru"])
        game.formAlliance("nova", ["blue", "red"])
        game.betrayAlliance("nova", "red")
        assert _sides(game) == [["blue"], ["red"], ["green"]]


class TestTheQueue:
    """The existing owner-battles-last re-pairing loop, now over sides."""

    def _pairing(self, game):
        return Combat.findSidesInTile(game, POS)[-2:]

    @pytest.mark.parametrize(("colors", "ships", "expected"), [
        # With two other sides present the owner side waits; they fight first.
        (("blue", "red", "green", "yellow"),
         ["blue-cru", "red-cru", "green-cru", "yellow-cru"], [["green"], ["yellow"]]),
        # Only one other side is left, so the owner side is drawn in against it.
        (("blue", "red", "green"),
         ["blue-cru", "red-cru", "green-cru"], [["blue", "red"], ["green"]]),
    ], ids=["two_attackers_fight_first", "owner_side_drawn_in"])
    def test_the_owner_side_is_drawn_in_only_when_it_is_needed(self, make_game, colors, ships, expected):
        game = _game(make_game, colors, ships, owner="blue")
        game.formAlliance("nova", ["blue", "red"])
        game.fixshipsOrder(POS)

        assert self._pairing(game) == expected


class TestSideTargeting:
    def test_an_ally_can_never_be_hit(self, make_game):
        game = _game(make_game, ("blue", "red", "green"),
                     ["blue-cru", "red-cru", "green-cru"],
                     attacker=["green"], defender=["blue", "red"], owner="blue")
        game.formAlliance("nova", ["blue", "red"])

        assert Combat.getOpponentUnitsThatCanBeHit(game, "green", ["blue-cru", "red-cru"], 6, 0, POS, 4) \
            == ["blue-cru", "red-cru"]
        assert Combat.getOpponentUnitsThatCanBeHit(game, "blue", ["green-cru"], 6, 0, POS, 4) == ["green-cru"]

    def test_targets_are_offered_latest_arrival_first(self, make_game):
        game = _game(make_game, ("blue", "red", "green"),
                     ["blue-cru", "red-cru", "green-cru"],
                     attacker=["green"], defender=["blue", "red"], owner="blue",
                     entry=["green", "blue", "red"])
        game.formAlliance("nova", ["blue", "red"])

        # red entered the sector last, so its ship is offered before blue's.
        assert Combat.getOpponentUnitsThatCanBeHit(game, "green", ["blue-cru", "red-cru"], 6, 0, POS, 4) \
            == ["red-cru", "blue-cru"]

    def test_buttons_name_the_owner_once_an_alliance_is_in_the_fight(self, make_game, run):
        game = _game(make_game, ("blue", "red", "green"),
                     ["blue-cru", "red-cru", "green-cru"],
                     attacker=["green"], defender=["blue", "red"], owner="blue",
                     entry=["green", "blue", "red"])
        game.formAlliance("nova", ["blue", "red"])
        game.gamestate["players"]["2"]["name"] = "Planta"
        game.gamestate["players"]["3"]["name"] = "Mechanema"

        # Two allied enemies field the same ship type, so each target button must say whose it is.
        targets = [Combat.getTargetButton(game, POS, ship)
                   for ship in Combat.getOpponentUnitsThatCanBeHit(
                       game, "green", ["blue-cru", "red-cru"], 6, 0, POS, 4)]

        assert [label for label, _icon in targets] == ["Hit cruiser (Planta)", "Hit cruiser (Hydran Progress)"]
        assert "plantatoken" in targets[0][1] and "hydrantoken" in targets[1][1]

        # Both defenders roll their own initiative, so their buttons must name them too.
        async def roll_buttons():
            return [(button.label, button.emoji) for button in Combat.getCombatButtons(game, POS).children
                    if "Roll Initative" in button.label]

        rolls = run(roll_buttons())

        assert [label for label, _icon in rolls] == ["(Defender) Roll Initative 2 Ships (Hydran Progress)",
                                                    "(Defender) Roll Initative 2 Ships (Planta)",
                                                    "(Attacker) Roll Initative 2 Ships (Mechanema)"]
        assert rolls[2][1].name == "mechanematoken"

        # The Ancients have no faction token, so their ships stay plainly named.
        assert Combat.getTargetButton(game, POS, "ai-anc") == ("Hit Ancient", None)

        # The damage log says whose ship was hit, too.
        interaction = FakeInteraction()
        run(Combat.assignHitTo(game, f"assignHitTo_{POS}_green_blue-cru_6_1", interaction, False))

        assert "dealt 1 damage to a cruiser (Hydran Progress) with a die" in interaction.channel.sent[0][0]

    def test_a_player_waiting_out_the_pairing_is_offered_no_targets(self, make_game):
        game = _game(make_game, ("blue", "red", "green", "yellow"),
                     ["blue-cru", "red-cru", "green-cru", "yellow-cru"],
                     attacker=["yellow"], defender=["green"], owner="blue")
        game.formAlliance("nova", ["blue", "red"])

        # The alliance is waiting for its turn, so it has nothing to shoot at.
        assert Combat.getOpponentUnitsThatCanBeHit(game, "blue", ["green-cru", "yellow-cru"], 6, 0, POS, 4) == []

    def test_without_recorded_sides_the_positional_fallback_still_applies(self, make_game):
        game = _game(make_game, ("blue", "green"), ["blue-cru", "green-cru"], owner="blue")

        # No attacker/defender at all: the last colour in the tile is the target.
        assert Combat.getOpponentUnitsThatCanBeHit(game, "blue", ["green-cru"], 6, 0, POS, 4) == ["green-cru"]

    def test_the_owner_side_defends_whichever_way_round_it_is_passed(self, make_game):
        game = _game(make_game, ("blue", "red", "green"), ["blue-cru", "red-cru", "green-cru"], owner="red")
        game.setAttackerAndDefender(["blue", "red"], ["green"], POS)

        assert game.gamestate["board"][POS]["defender"] == ["blue", "red"]
        assert game.gamestate["board"][POS]["attacker"] == ["green"]

    def test_a_bare_colour_from_an_older_save_still_works(self, make_game):
        game = _game(make_game, ("blue", "green"), ["blue-cru", "green-cru"],
                     attacker="green", defender="blue", owner="blue")

        assert Combat.sideOf("blue") == ["blue"]
        assert Combat.sideOf(["blue"]) == ["blue"]
        assert Combat.sideOf(None) == []
        assert Combat.sideOf(game.gamestate["board"][POS]["attacker"]) == ["green"]


class TestDracoAndAncients:
    """Draco (blue) may not battle the Ancients but fights players as usual.
    Alliance FAQ: an Ally fights the Ancients and Draco sits that battle out."""

    def _game_with_draco(self, make_game, ships, attacker=None, defender=None, owner="red",
                         colors=("blue", "red")):
        game_players = players(*colors)
        game_players["1"]["name"] = "Descendants of Draco"
        board = board_tile(ships, owner=owner)
        if attacker is not None:
            board[POS]["attacker"] = attacker
        if defender is not None:
            board[POS]["defender"] = defender
        game = make_game({"player_count": len(colors), "players": game_players, "board": board,
                          "advanced_ai": False, "wa_ai": False})
        game.fixshipsOrder(POS)
        return game

    @pytest.mark.parametrize(("ships", "pairing"), [
        (["blue-cru", "red-cru", "ai-anc"], [["ai"], ["red"]]),
        (["blue-cru", "red-cru"], [["red", "blue"]]),
    ], ids=["ancients_present", "no_ancients"])
    def test_an_allied_draco_sits_out_only_against_the_ancients(self, make_game, ships, pairing):
        game = self._game_with_draco(make_game, ships)
        game.formAlliance("nova", ["blue", "red"])

        assert Combat.currentPairing(game, POS) == pairing

    def test_draco_fights_a_player_before_the_ancients(self, make_game):
        game = self._game_with_draco(make_game, ["blue-cru", "red-cru", "ai-anc"], owner=0)

        assert Combat.currentPairing(game, POS) == [["blue"], ["red"]]

        game.remove_units(["blue-cru"], POS)
        assert Combat.currentPairing(game, POS) == [["ai"], ["red"]]

    def test_draco_winning_against_a_player_ends_combat(self, make_game):
        game = self._game_with_draco(make_game, ["blue-cru", "red-cru", "ai-anc"], owner=0)
        game.remove_units(["red-cru"], POS)

        assert Combat.isDracoAgainstAncients(game, POS)

    def test_draco_left_with_the_ancients_may_only_place_influence(self, make_game, run):
        game = self._game_with_draco(make_game, ["blue-cru", "ai-anc"], owner=0)
        game.gamestate["board"][POS]["disctile"] = 1
        interaction = FakeInteraction()

        run(Combat.declareAWinner(game, interaction, POS))

        ids = offered_ids(interaction)
        assert f"FCIDblue_addInfluenceFinish_{POS}" in ids
        assert not any("exploreDiscoveryTile" in button_id for button_id in ids)
        assert not any("Alliance" in content for content, _kwargs in interaction.channel.sent)

    def test_draco_defends_his_sector_last_among_players(self, make_game):
        game = self._game_with_draco(make_game, ["blue-cru", "red-cru", "green-cru", "ai-anc"],
                                     owner="blue", colors=("blue", "red", "green"))

        assert Combat.currentPairing(game, POS) == [["red"], ["green"]]

        game.remove_units(["red-cru"], POS)
        assert Combat.currentPairing(game, POS) == [["blue"], ["green"]]

    def test_draco_alone_against_the_ancients_is_recognised(self, make_game):
        game = self._game_with_draco(make_game, ["blue-cru", "ai-anc"])

        assert Combat.isDracoAgainstAncients(game, POS)

        game.add_units(["red-cru"], POS)
        assert not Combat.isDracoAgainstAncients(game, POS)

    def test_draco_cannot_be_hit_while_sitting_out(self, make_game, run):
        game = self._game_with_draco(make_game, ["blue-cru", "red-cru", "ai-anc"])
        game.formAlliance("nova", ["blue", "red"])
        run(_pair(game))

        # The Ancients may only shoot at the ally, never at Draco.
        assert Combat.getOpponentUnitsThatCanBeHit(game, "ai", ["blue-cru", "red-cru"], 6, 0, POS, 4) \
            == ["red-cru"]

    def test_draco_does_not_draw_reputation_after_ally_defeats_ancients(self, make_game, run):
        game = self._game_with_draco(make_game, ["blue-cru", "red-cru", "ai-anc"])
        game.formAlliance("nova", ["blue", "red"])
        run(_pair(game))
        game.remove_units(["ai-anc"], POS)
        interaction = FakeInteraction()

        run(Combat.declareAWinner(game, interaction, POS))

        assert _reputation_colors(interaction) == ["red"]

    def test_repaired_pairing_adds_new_actual_combatants(self, make_game, run):
        game = self._game_with_draco(make_game, ["blue-cru", "red-cru", "ai-anc"])
        game.formAlliance("nova", ["blue", "red"])
        run(_pair(game))
        game.remove_units(["ai-anc"], POS)

        game.setAttackerAndDefender(["blue", "red"], ["green"], POS)

        assert set(game.gamestate["board"][POS]["combatants"]) == {"red", "ai", "blue", "green"}


class TestTwoPlayerRegression:
    """With no alliances, combat must behave exactly as it did before sides."""

    def test_two_players_are_two_single_colour_sides(self, make_game):
        game = _game(make_game, ("blue", "red"), ["blue-cru", "red-cru"], owner="red")

        assert Combat.findSidesInTile(game, POS) == [["blue"], ["red"]]

        sides = Combat.findSidesInTile(game, POS)[-2:]
        game.setAttackerAndDefender(sides[1], sides[0], POS)
        # The owner defends.
        assert game.gamestate["board"][POS]["defender"] == ["red"]
        assert game.gamestate["board"][POS]["attacker"] == ["blue"]

    def test_a_solo_defender_is_still_the_only_target(self, make_game):
        game = _game(make_game, ("blue", "red"), ["blue-cru", "red-cru"],
                     attacker=["blue"], defender=["red"], owner="red")

        assert Combat.getOpponentUnitsThatCanBeHit(game, "blue", ["red-cru"], 6, 0, POS, 4) == ["red-cru"]
        assert Combat.getOpponentUnitsThatCanBeHit(game, "red", ["blue-cru"], 6, 0, POS, 4) == ["blue-cru"]

    def test_both_sides_roll_in_the_same_order_as_before(self, make_game):
        game = _game(make_game, ("blue", "red"), ["blue-cru", "red-cru"], owner="red")
        ships = game.gamestate["board"][POS]["player_ships"][:]

        # Defender wins initiative ties, as it always has.
        assert Combat.getBothCombatantShipsBySpeed(game, ["red"], ["blue"], ships, POS) \
            == [(2, "red"), (2, "blue")]

    def test_buttons_stay_plain_without_an_alliance(self, make_game, run):
        game = _game(make_game, ("blue", "red"), ["blue-cru", "red-cru"],
                     attacker=["blue"], defender=["red"], owner="red")

        async def roll_buttons():
            return [(button.label, button.emoji) for button in Combat.getCombatButtons(game, POS).children]

        assert Combat.getTargetButton(game, POS, "red-cru") == ("Hit cruiser", None)
        assert run(roll_buttons()) \
            == [("(Defender) Roll Initative 2 Ships", None), ("(Attacker) Roll Initative 2 Ships", None),
                ("Refresh Image", None), ("Remove Units", None)]

        interaction = FakeInteraction()
        run(Combat.assignHitTo(game, f"assignHitTo_{POS}_blue_red-cru_6_1", interaction, False))

        assert "dealt 1 damage to a cruiser with a die" in interaction.channel.sent[0][0]


class TestAllianceWinsTheSector:
    def test_the_winning_side_is_offered_the_disc_earliest_entry_first(self, make_game, run):
        game = _game(make_game, ("blue", "red", "green"),
                     ["blue-cru", "red-cru"],
                     attacker=["green"], defender=["blue", "red"], owner=0,
                     entry=["green", "red", "blue"])
        game.formAlliance("nova", ["blue", "red"])
        inter = FakeInteraction()

        run(Combat.declareAWinner(game, inter, POS))

        disc = [button_id for button_id in offered_ids(inter) if "addInfluenceFinish" in button_id]
        # red entered before blue, so red is offered the disc first.
        assert disc == [f"FCIDred_addInfluenceFinish_{POS}", f"FCIDblue_addInfluenceFinish_{POS}"]

    def test_a_solo_winner_still_gets_one_plain_button(self, make_game, run):
        game = _game(make_game, ("blue", "green"), ["blue-cru"],
                     attacker=["green"], defender=["blue"], owner=0, entry=["green", "blue"])
        inter = FakeInteraction()

        run(Combat.declareAWinner(game, inter, POS))

        labels = offered_labels(inter)
        assert "Place Influence" in labels
        assert not any(label.startswith("Place Influence (") for label in labels)


class TestEntryOrder:
    def test_units_are_recorded_in_arrival_order(self, make_game):
        game = _game(make_game, ("blue", "red"), [], owner=0)
        game.add_units(["blue-cru"], POS)
        game.add_units(["red-cru"], POS)
        game.add_units(["blue-cru"], POS)

        assert game.getEntryOrder(POS) == ["blue", "red"]

    def test_a_colour_leaves_the_order_once_its_last_ship_goes(self, make_game):
        game = _game(make_game, ("blue", "red"), [], owner=0)
        game.add_units(["blue-cru"], POS)
        game.add_units(["red-cru"], POS)
        game.remove_units(["blue-cru"], POS)

        assert game.getEntryOrder(POS) == ["red"]

    def test_re_entry_moves_a_colour_to_the_end(self, make_game):
        game = _game(make_game, ("blue", "red"), [], owner=0)
        game.add_units(["blue-cru"], POS)
        game.add_units(["red-cru"], POS)
        game.remove_units(["blue-cru"], POS)
        game.add_units(["blue-cru"], POS)

        assert game.getEntryOrder(POS) == ["red", "blue"]


class TestAllianceCombatEnd:
    def test_removing_one_ally_keeps_the_current_combat_pairing(self, make_game, run, monkeypatch):
        game = _game(make_game, ("blue", "red", "green"),
                     ["blue-cru", "red-cru", "green-cru"],
                     attacker=["green"], defender=["blue", "red"])
        game.formAlliance("nova", ["blue", "red"])
        game.remove_units(["blue-cru"], POS)
        prompted = []

        async def prompt(*args):
            prompted.append(args[1])

        async def unexpected_restart(*_args, **_kwargs):
            raise AssertionError("combat pairing restarted while both sides remain")

        monkeypatch.setattr(Combat, "promptNextSpeed", staticmethod(prompt))
        monkeypatch.setattr(Combat, "startCombat", staticmethod(unexpected_restart))
        run(Combat.checkCombatEnd(game, FakeInteraction(), POS, 3))

        assert prompted == [POS]

    def test_destroying_an_ally_waits_for_the_remaining_hits(self, make_game, run, monkeypatch):
        game = _game(make_game, ("blue", "red", "green"),
                     ["blue-cru", "red-int", "green-cru"],
                     attacker=["green"], defender=["blue", "red"])
        game.formAlliance("nova", ["blue", "red"])
        game.setUnresolvedHits(2, POS)
        prompted = []

        async def prompt(*args):
            prompted.append(args[1])

        monkeypatch.setattr(Combat, "promptNextSpeed", staticmethod(prompt))
        run(Combat.assignHitTo(game, f"assignHitTo_{POS}_green_red-int_6_5", FakeInteraction(), True))
        assert prompted == []

        run(Combat.assignHitTo(game, f"assignHitTo_{POS}_green_blue-cru_6_1", FakeInteraction(), True))
        assert prompted == [POS]

    def test_a_last_hit_that_destroys_an_ally_prompts_once(self, make_game, run, monkeypatch):
        game = _game(make_game, ("blue", "red", "green"),
                     ["blue-cru", "red-int", "green-cru"],
                     attacker=["green"], defender=["blue", "red"])
        game.formAlliance("nova", ["blue", "red"])
        game.setUnresolvedHits(1, POS)
        prompted = []

        async def prompt(*args):
            prompted.append(args[1])

        monkeypatch.setattr(Combat, "promptNextSpeed", staticmethod(prompt))
        run(Combat.assignHitTo(game, f"assignHitTo_{POS}_green_red-int_6_5", FakeInteraction(), True))

        assert prompted == [POS]

    def test_a_roll_from_outside_the_pairing_asks_for_a_refresh(self, make_game, run):
        game = _game(make_game, ("blue", "red", "green"),
                     ["blue-cru", "red-cru", "green-cru"], attacker=["green"], defender=["blue"])
        interaction = FakeInteraction()

        run(Combat.rollDice(game, f"rollDice_{POS}_red_2_deleteMsg", interaction))

        assert any("Refresh Image" in content for content, _kwargs in interaction.channel.sent)
        assert game.gamestate["board"][POS].get("currentRoller") is None

    def test_retreat_destination_with_allied_ships_is_valid(self, make_game, monkeypatch):
        game = _game(make_game, ("blue", "red", "green"), ["blue-cru", "red-cru"])
        game.formAlliance("nova", ["blue", "red"])
        game.gamestate["board"]["102"] = {
            "owner": "red", "sector": 102, "disctile": 0,
            "player_ships": ["blue-cru", "red-cru"],
        }
        game.gamestate["players"]["1"]["owned_tiles"] = ["102"]
        monkeypatch.setattr("helpers.CombatHelper.InfluenceButtons.areTwoTilesAdjacent",
                            lambda *_args: True)

        assert Combat.getRetreatTiles(game, POS, "blue") == ["102"]
        game.gamestate["players"]["1"]["name"] = "Descendants of Draco"
        assert Combat.getRetreatTiles(game, POS, "blue") == ["102"]

    def test_partial_retreat_continues_current_combat(self, make_game, run, monkeypatch):
        game = _game(make_game, ("blue", "red", "green"),
                     ["blue-cru", "blue-int", "red-cru", "green-cru"],
                     attacker=["green"], defender=["blue", "red"])
        game.formAlliance("nova", ["blue", "red"])
        game.gamestate["board"]["102"] = {
            "owner": "blue", "sector": 102, "disctile": 0, "player_ships": []
        }

        class Ship:
            def __init__(self, _player, ship_type):
                self.speed = {"cru": 2, "int": 3}[ship_type]

        monkeypatch.setattr("helpers.CombatHelper.PlayerShip", Ship)
        prompted = []

        async def prompt(_game, pos, _channel, _continue):
            prompted.append(pos)

        monkeypatch.setattr(Combat, "promptNextSpeed", staticmethod(prompt))
        interaction = FakeInteraction()
        run(Combat.finishRetreatingUnits(
            game, f"finishRetreatingUnits_{POS}_blue_2_102", interaction,
            game.getPlayerObjectFromColor("blue")))

        assert game.gamestate["board"][POS]["player_ships"] == [
            "blue-int", "red-cru", "green-cru"]
        assert prompted == [POS]

    def test_combat_ends_when_only_allies_remain_after_enemy_is_destroyed(self, make_game, run, monkeypatch):
        game = _game(make_game, ("blue", "red", "green"),
                     ["blue-cru", "red-cru"], attacker=["green"], defender=["blue", "red"])
        game.formAlliance("nova", ["blue", "red"])
        declared = _record_declared_winners(monkeypatch)

        run(Combat.checkCombatEnd(game, FakeInteraction(), POS, 3))

        assert declared == [POS]

    @pytest.mark.parametrize("removed", ["green-cru", "blue-cru"])
    def test_manual_unit_removal_defers_to_the_combat_end_check(self, make_game, run, monkeypatch, removed):
        game = _game(make_game, ("blue", "red", "green"),
                     ["blue-cru", "red-cru", "green-cru"])
        game.formAlliance("nova", ["blue", "red"])
        checked = []

        async def check_end(_game, _interaction, pos, old_length):
            checked.append((pos, old_length))

        async def edit(*_args, **_kwargs):
            return None

        monkeypatch.setattr(Combat, "checkCombatEnd", staticmethod(check_end))
        monkeypatch.setattr(Combat, "getRemovalButtons", staticmethod(lambda *_args: None))
        interaction = FakeInteraction()
        interaction.message.edit = edit
        run(Combat.removeThisUnit(game, f"removeThisUnit_{POS}_{removed}",
                                  game.getPlayerObjectFromColor("blue"), interaction))

        assert checked == [(POS, 3)]

    def test_retreat_ends_combat_when_only_allies_remain(self, make_game, run, monkeypatch):
        game = _game(make_game, ("blue", "red", "green"),
                     ["blue-cru", "red-cru", "green-cru"],
                     attacker=["green"], defender=["blue", "red"])
        game.formAlliance("nova", ["blue", "red"])
        game.gamestate["board"]["102"] = {
            "owner": "green", "sector": 102, "disctile": 0, "player_ships": []
        }
        declared = _record_declared_winners(monkeypatch)
        interaction = FakeInteraction()
        run(Combat.finishRetreatingUnits(game, f"finishRetreatingUnits_{POS}_green_2_102",
                                         interaction, game.getPlayerObjectFromColor("green")))

        assert game.gamestate["board"][POS]["player_ships"] == ["blue-cru", "red-cru"]
        assert declared == [POS]

    def test_reputation_prompts_follow_recorded_entry_order_including_eliminated_ally(
            self, make_game, run):
        game = _game(make_game, ("blue", "red", "green"), ["blue-cru", "red-cru"],
                     attacker=["green"], defender=["blue", "red"], owner="blue",
                     entry=["red", "green", "blue"])
        game.formAlliance("nova", ["blue", "red"])
        game.setCombatants(["blue", "red", "green"], POS)
        game.remove_units(["red-cru"], POS)
        interaction = FakeInteraction()

        run(Combat.declareAWinner(game, interaction, POS))

        assert _reputation_colors(interaction) == ["red", "green", "blue"]

    def test_allied_sector_owner_is_not_offered_as_an_enemy_to_bombard(self, make_game, run):
        game = _game(make_game, ("blue", "red", "green"), ["blue-cru", "red-cru"],
                     attacker=["green"], defender=["blue", "red"], owner="red")
        game.formAlliance("nova", ["blue", "red"])
        game.gamestate["board"][POS]["combatants"] = ["blue", "red", "green"]
        interaction = FakeInteraction()

        run(Combat.declareAWinner(game, interaction, POS))

        assert not any("rollDice" in button_id or "removeInfluenceFinish" in button_id
                       for button_id in offered_ids(interaction))


class TestStalemateResolution:
    def _unarmed_alliance_battle(self, make_game):
        game = _game(make_game, ("blue", "red", "green"),
                     ["blue-int", "red-int", "green-int", "green-cru", "green-drd"],
                     attacker=["green"], defender=["blue", "red"],
                     entry=["red", "green", "blue"])
        game.formAlliance("nova", ["blue", "red"])
        for player in game.gamestate["players"].values():
            for ship_type in ("interceptor", "cruiser", "dread"):
                player[f"{ship_type}_parts"] = ["empty"]
        game.gamestate["board"][POS]["currentSpeed"] = 1
        return game

    @pytest.mark.parametrize("source", ["combat_buttons", "prompt_next_speed"])
    def test_an_unarmed_battle_offers_the_attacker_the_stalemate_action(self, make_game, run, source):
        game = self._unarmed_alliance_battle(make_game)
        interaction = FakeInteraction()

        async def offered():
            if source == "combat_buttons":
                return [button.custom_id for button in Combat.getCombatButtons(game, POS).children]
            await Combat.promptNextSpeed(game, POS, interaction.channel, False)
            await asyncio.sleep(0)  # let the task sending the prompt finish
            return offered_ids(interaction)

        assert "FCIDgreen_resolveStalemate_101_green" in run(offered())

    def test_an_attacking_alliance_gets_one_named_stalemate_button_each(self, make_game, run):
        game = _game(make_game, ("blue", "red", "green"),
                     ["blue-int", "red-int", "green-int"],
                     attacker=["blue", "red"], defender=["green"], owner="green")
        game.formAlliance("nova", ["blue", "red"])
        for player in game.gamestate["players"].values():
            for ship_type in ("interceptor", "cruiser", "dread"):
                player[f"{ship_type}_parts"] = ["empty"]
        game.gamestate["board"][POS]["currentSpeed"] = 1
        game.gamestate["players"]["2"]["name"] = "Planta"

        async def stalemate_buttons():
            return [(button.label, button.emoji.name if button.emoji else None)
                    for button in Combat.getCombatButtons(game, POS).children if "Stalemate" in button.label]

        assert run(stalemate_buttons()) \
            == [("Resolve Stalemate (Destroy Attacking Ships) (Hydran Progress)", "hydrantoken"),
                ("Resolve Stalemate (Destroy Attacking Ships) (Planta)", "plantatoken")]

    def test_stalemate_is_blocked_during_missile_speed_and_pending_resolution(self, make_game):
        game = self._unarmed_alliance_battle(make_game)
        for speed in (98, 99, 101):
            game.gamestate["board"][POS]["currentSpeed"] = speed
            assert not Combat.canResolveStalemate(game, POS)

        game.gamestate["board"][POS]["currentSpeed"] = 1
        for pending in ({"unresolvedHits": 1},
                        {"pendingRiftDice": {"0": "cru"}},
                        {"pendingRiftBackfire": {"cru": 1}}):
            game.gamestate["board"][POS].update(pending)
            assert not Combat.canResolveStalemate(game, POS)
            for key in pending:
                game.gamestate["board"][POS].pop(key)

    def test_stalemate_destroys_attackers_and_credits_largest_ships_round_robin(
            self, make_game, run, monkeypatch):
        game = self._unarmed_alliance_battle(make_game)
        interaction = FakeInteraction()
        monkeypatch.setattr(Combat, "checkCombatEnd", staticmethod(_noop))

        run(Combat.resolveStalemate(game, f"resolveStalemate_{POS}_green", interaction))

        assert game.gamestate["board"][POS]["player_ships"] == ["blue-int", "red-int"]
        assert game.gamestate["board"][POS]["ships_destroyed_by_red"] == ["drd", "int"]
        assert game.gamestate["board"][POS]["ships_destroyed_by_blue"] == ["cru"]

    def test_stale_stalemate_action_cannot_destroy_a_different_attacker(self, make_game, run):
        game = self._unarmed_alliance_battle(make_game)
        game.gamestate["board"][POS]["attacker"] = ["blue"]

        run(Combat.resolveStalemate(game, f"resolveStalemate_{POS}_green", FakeInteraction()))

        assert game.gamestate["board"][POS]["player_ships"] == [
            "blue-int", "red-int", "green-int", "green-cru", "green-drd"
        ]

    def test_stalemate_action_refuses_ships_that_still_have_nonmissile_weapons(self, make_game, run):
        game = _game(make_game, ("blue", "red", "green"),
                     ["blue-int", "red-int", "green-cru"],
                     attacker=["green"], defender=["blue", "red"])
        game.formAlliance("nova", ["blue", "red"])
        game.gamestate["board"][POS]["currentSpeed"] = 1

        run(Combat.resolveStalemate(game, f"resolveStalemate_{POS}_green", FakeInteraction()))

        assert game.gamestate["board"][POS]["player_ships"] == ["blue-int", "red-int", "green-cru"]

    def test_stalemate_leaves_noncombat_orbitals_and_monuments_alone(self, make_game, run, monkeypatch):
        game = self._unarmed_alliance_battle(make_game)
        game.gamestate["board"][POS]["player_ships"].extend(["green-mon", "green-orb"])
        monkeypatch.setattr(Combat, "checkCombatEnd", staticmethod(_noop))

        run(Combat.resolveStalemate(game, f"resolveStalemate_{POS}_green", FakeInteraction()))

        assert "green-mon" in game.gamestate["board"][POS]["player_ships"]
        assert "green-orb" in game.gamestate["board"][POS]["player_ships"]

    def test_armed_exile_orbital_prevents_stalemate_resolution(self, make_game):
        game = _game(make_game, ("blue", "red", "green"),
                     ["blue-int", "red-int", "green-cru", "green-orb"],
                     attacker=["green"], defender=["blue", "red"], owner="green")
        game.formAlliance("nova", ["blue", "red"])
        game.gamestate["players"]["3"] = player_stats("exl", color="green")
        game.gamestate["board"][POS]["orbital_pop"] = [1]
        for player in game.gamestate["players"].values():
            for ship_type in ("interceptor", "cruiser", "dread"):
                player[f"{ship_type}_parts"] = ["empty"]
        game.gamestate["players"]["3"]["orb_parts"] = ["anc"]
        game.gamestate["board"][POS]["currentSpeed"] = 1

        assert not Combat.canResolveStalemate(game, POS)

    def test_stalemate_action_is_dispatched(self):
        with open("listeners/ButtonListener.py") as listener_file:
            listener = listener_file.read()

        assert 'customID.startswith("resolveStalemate")' in listener


class TestAllianceDiceAssignment:
    """FAQ: non-player (Ancient/Guardian/GCDS) dice hit the Alliance collectively,
    with ties between similar targets going to whoever entered last."""

    def _ai_game(self, make_game):
        game = _game(make_game, ("green", "red"), ["ai-anc", "green-int", "red-int"],
                     attacker="ai", defender=["green", "red"], entry=["green", "red"])
        game.gamestate["advanced_ai"] = False
        game.gamestate["wa_ai"] = False
        return game

    def test_never_targets_an_allied_ship(self, make_game):
        game = self._ai_game(make_game)
        ships = game.gamestate["board"][POS]["player_ships"]

        hittable = Combat.getOpponentUnitsThatCanBeHit(game, "ai", ships, 6, 1, POS, 2)

        assert hittable and all(ship.startswith("green-") or ship.startswith("red-") for ship in hittable)
        # and specifically: a player's own dice never see their Ally as hittable, only the real opponent.
        own_dice_targets = Combat.getOpponentUnitsThatCanBeHit(game, "green", ships, 6, 0, POS, 3)
        assert own_dice_targets and all(ship.startswith("ai-") for ship in own_dice_targets)

    def test_ties_between_similar_targets_go_to_the_last_entered_ally(self, make_game, run, no_random, monkeypatch):
        game = self._ai_game(make_game)
        no_random([6, 6])
        hit = []

        async def spy(_game, buttonID, _interaction, _flag):
            hit.append(buttonID.split("_")[3])

        monkeypatch.setattr(Combat, "assignHitTo", spy)
        monkeypatch.setattr(Combat, "promptNextSpeed", _noop)

        run(Combat.rollDice(game, f"rollDice_{POS}_ai_2_deleteMsg", FakeInteraction()))

        assert hit and all(ship == "red-int" for ship in hit)
