"""Combat pairs SIDES, not colours: allies fight together and never each other."""
from helpers.CombatHelper import Combat
from tests.fakes import player_stats

POS = "101"


def _players(*colors):
    return {str(i): player_stats("hyd", color=color) for i, color in enumerate(colors, 1)}


def _game(make_game, colors, ships, attacker=None, defender=None, owner=0, entry=None):
    board = {POS: {"owner": owner, "sector": 101, "disctile": 0, "player_ships": list(ships)}}
    if attacker is not None:
        board[POS]["attacker"] = attacker
    if defender is not None:
        board[POS]["defender"] = defender
    if entry is not None:
        board[POS]["entryOrder"] = list(entry)
    return make_game({"player_count": len(colors), "players": _players(*colors), "board": board})


def _sides(game):
    return Combat.findSidesInTile(game, POS)


class TestSidesInTile:
    def test_unallied_players_are_each_their_own_side(self, make_game):
        game = _game(make_game, ("blue", "red", "green"), ["blue-cru", "red-cru", "green-cru"])
        assert _sides(game) == [["blue"], ["red"], ["green"]]

    def test_allies_become_one_side(self, make_game):
        game = _game(make_game, ("blue", "red", "green"), ["blue-cru", "red-cru", "green-cru"])
        game.formAlliance("nova", ["blue", "red"])
        assert _sides(game) == [["blue", "red"], ["green"]]

    def test_an_ally_is_merged_even_when_not_adjacent_in_the_ship_list(self, make_game):
        game = _game(make_game, ("blue", "red", "green"), ["blue-cru", "green-cru", "red-cru"])
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

    def test_the_owner_side_waits_so_the_two_attackers_fight_first(self, make_game):
        game = _game(make_game, ("blue", "red", "green", "yellow"),
                     ["blue-cru", "red-cru", "green-cru", "yellow-cru"], owner="blue")
        game.formAlliance("nova", ["blue", "red"])
        game.fixshipsOrder(POS)

        assert self._pairing(game) == [["green"], ["yellow"]]

    def test_after_one_attacker_dies_the_owner_side_is_drawn_in(self, make_game):
        game = _game(make_game, ("blue", "red", "green", "yellow"),
                     ["blue-cru", "red-cru", "green-cru"], owner="blue")
        game.formAlliance("nova", ["blue", "red"])
        game.fixshipsOrder(POS)

        # yellow is gone, so only two sides remain and both fight.
        assert self._pairing(game) == [["blue", "red"], ["green"]]

    def test_an_alliance_facing_a_single_enemy_fights_at_once(self, make_game):
        game = _game(make_game, ("blue", "red", "green"),
                     ["blue-cru", "red-cru", "green-cru"], owner="blue")
        game.formAlliance("nova", ["blue", "red"])
        game.fixshipsOrder(POS)

        assert self._pairing(game) == [["blue", "red"], ["green"]]


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
    """FAQ: the ally fights the Ancients; the Descendants of Draco do not."""

    def _game_with_draco(self, make_game, ships, attacker=None, defender=None):
        players = _players("blue", "red")
        players["1"]["name"] = "Descendants of Draco"
        board = {POS: {"owner": "red", "sector": 101, "disctile": 0, "player_ships": list(ships)}}
        if attacker is not None:
            board[POS]["attacker"] = attacker
        if defender is not None:
            board[POS]["defender"] = defender
        return make_game({"player_count": 2, "players": players, "board": board})

    def test_draco_is_left_out_when_ancients_are_present(self, make_game):
        game = self._game_with_draco(make_game, ["blue-cru", "red-cru", "ai-anc"])
        game.formAlliance("nova", ["blue", "red"])

        assert Combat.sitsOutAgainstAncients(game, "blue", POS)
        assert not Combat.sitsOutAgainstAncients(game, "red", POS)
        # Only the ally faces the Ancients.
        assert Combat.findSidesInTile(game, POS) == [["red"], ["ai"]]

    def test_draco_fights_normally_when_no_ancients_are_present(self, make_game):
        game = self._game_with_draco(make_game, ["blue-cru", "red-cru"])
        game.formAlliance("nova", ["blue", "red"])

        assert not Combat.sitsOutAgainstAncients(game, "blue", POS)
        assert Combat.findSidesInTile(game, POS) == [["blue", "red"]]

    def test_draco_cannot_be_hit_while_sitting_out(self, make_game):
        game = self._game_with_draco(make_game, ["blue-cru", "red-cru", "ai-anc"],
                                     attacker=["ai"], defender=["blue", "red"])
        game.formAlliance("nova", ["blue", "red"])

        # The Ancients may only shoot at the ally, never at Draco.
        assert Combat.getOpponentUnitsThatCanBeHit(game, "ai", ["blue-cru", "red-cru"], 6, 0, POS, 4) \
            == ["red-cru"]


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
