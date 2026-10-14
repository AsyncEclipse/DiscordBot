"""Leaving an Alliance only makes the leaver a Traitor after aggression."""

from discord.ui import View
import pytest

from Buttons.Alliance import AllianceButtons
from Buttons.Turn import TurnButtons
from helpers.CombatHelper import Combat
from tests.fakes import FakeInteraction, board_tile, player_helper, players


def _game_state():
    game_players = players("blue", "red", "green", "yellow")
    game_players["1"].update(owned_tiles=["101"], reputation_track=["amb-hydran-red"])
    game_players["2"]["reputation_track"] = ["amb-hydran-blue"]
    game_players["3"]["reputation_track"] = ["mixed"]
    game_players["4"]["reputation_track"] = ["mixed"]
    return {
        "player_count": 4,
        "players": game_players,
        "board": {**board_tile(owner="blue"),
                  **board_tile(["blue-int", "green-int"], owner="green", sector=102)},
    }


def _leave_nova(game):
    game.formAlliance("nova", ["blue", "red"])
    game.betrayAlliance("nova", "blue")


def _traitor_check(game, color):
    player = game.getPlayerObjectFromColor(color)
    return TurnButtons.checkTraitor(game, player, FakeInteraction(), player_helper(game, color))


def _one_related(state):
    state["players"]["2"]["owned_tiles"] = ["101"]
    state["board"]["101"].update(owner="red", player_ships=["blue-int"])


def _two_related(state):
    state["players"]["1"]["reputation_track"] = ["amb-hydran-red", "amb-hydran-green"]
    state["players"]["2"]["owned_tiles"] = ["101"]
    state["players"]["3"]["owned_tiles"] = ["102"]
    state["board"]["101"].update(owner="red", player_ships=["blue-int"])
    state["board"]["102"]["player_ships"] = ["blue-int"]


class TestAllianceBetrayal:
    @pytest.mark.parametrize(("ships_101", "traitor"), [
        (["red-int"], True),
        ([], False),
    ], ids=["former_ally_present", "no_former_ally"])
    def test_a_former_allys_presence_decides_whether_the_leaver_is_traitor(
            self, make_game, run, ships_101, traitor):
        state = _game_state()
        state["board"]["101"]["player_ships"] = ships_101
        game = make_game(state)
        _leave_nova(game)

        run(_traitor_check(game, "blue"))

        assert bool(game.getPlayerObjectFromColor("blue").get("traitor")) is traitor

    @pytest.mark.parametrize(("mutate", "expected"), [
        (_one_related, [("blue", "red")]),
        (_two_related, [("blue", "red"), ("blue", "green")]),
    ])
    def test_ordinary_aggression_breaks_relations_with_each_related_player(
            self, make_game, run, monkeypatch, mutate, expected):
        state = _game_state()
        mutate(state)
        game = make_game(state)
        calls = []

        async def break_relations(_game, player, other, _interaction):
            calls.append((player["color"], other["color"]))

        monkeypatch.setattr(
            "Buttons.Turn.DiplomaticRelationsButtons.breakRelationsWith", break_relations
        )

        run(_traitor_check(game, "blue"))

        assert calls == expected
        assert game.getPlayerObjectFromColor("blue")["traitor"] is True

    def test_a_different_allys_ships_do_not_count_as_former_ally_aggression(
        self, make_game, run
    ):
        state = _game_state()
        state["board"]["101"] = {
            "owner": 0,
            "sector": 101,
            "player_ships": ["blue-int", "green-int"],
        }
        state["players"]["1"]["owned_tiles"] = []
        state["players"]["2"]["owned_tiles"] = []
        game = make_game(state)
        _leave_nova(game)
        game.formAlliance("flare", ["blue", "green"])

        run(_traitor_check(game, "blue"))

        assert game.getPlayerObjectFromColor("blue").get("traitor") is not True

    def test_former_ally_without_direct_diplomatic_relations_still_triggers_faq(
        self, make_game, run
    ):
        state = _game_state()
        state["player_count"] = 6
        state["board"]["101"]["player_ships"] = ["green-int"]
        game = make_game(state)
        game.formAlliance("nova", ["blue", "red", "green"])
        game.betrayAlliance("nova", "blue")
        blue = game.getPlayerObjectFromColor("blue")

        assert not any("green" in tile for tile in blue["reputation_track"])

        run(_traitor_check(game, "blue"))

        assert blue["traitor"] is True

    def test_new_turn_opens_leave_window_and_action_closes_it(self, make_game, run):
        game = make_game(_game_state())
        game.setAlliances(True)
        game.formAlliance("nova", ["blue", "red"])
        blue = game.getPlayerObjectFromColor("blue")

        TurnButtons.startNewTurn(blue, game)
        assert game.gamestate["activePlayerColor"] == ["blue"]

        async def check_views():
            view = View()
            AllianceButtons.addAllianceButtons(view, game, blue)
            assert any("Leave" in button.label for button in view.children)

            player_helper(game, "blue").spend_influence_on_action("explore")
            view = View()
            AllianceButtons.addAllianceButtons(view, game, blue)

            assert not any("Leave" in button.label for button in view.children)

        run(check_views())

    def test_passing_the_turn_also_checks_the_traitor_rule(self, make_game, run, monkeypatch):
        """FAQ: aggression against a former Ally counts at the end of your Action OR Turn."""
        state = _game_state()
        state["board"]["101"]["player_ships"] = ["red-int"]
        game = make_game(state)
        _leave_nova(game)
        blue = game.getPlayerObjectFromColor("blue")

        checked = []

        async def spy(_game, player, _interaction, _player_helper):
            checked.append(player["color"])

        monkeypatch.setattr(TurnButtons, "checkTraitor", spy)
        monkeypatch.setattr(game, "get_next_player", lambda _player: None)
        monkeypatch.setattr(Combat, "findTilesInConflict", staticmethod(lambda _g: []))
        monkeypatch.setattr(Combat, "findUnownedTilesToTakeOver", staticmethod(lambda _g: []))
        monkeypatch.setattr(Combat, "findTilesInContention", staticmethod(lambda _g: []))
        async def noop(*_a, **_k):
            return None
        monkeypatch.setattr(game, "updateNamesAndOutRimTiles", noop)

        inter = FakeInteraction(role_names=[game.game_id])
        run(TurnButtons.passForRound(blue, game, inter, player_helper(game, "blue")))

        assert checked == ["blue"]

    @pytest.mark.parametrize(
        ("saved_closed", "current_closed", "can_leave"),
        [(False, True, True), (True, False, False)],
    )
    def test_restart_preserves_saved_leave_window(
        self, make_game, run, monkeypatch, saved_closed, current_closed, can_leave
    ):
        game = make_game(_game_state())
        game.setAlliances(True)
        game.formAlliance("nova", ["blue", "red"])
        blue = game.getPlayerObjectFromColor("blue")
        blue["allianceLeaveClosed"] = saved_closed
        game.gamestate["activePlayerColor"] = ["blue"]
        game.update()
        game.updateSaveFile()
        blue["allianceLeaveClosed"] = current_closed
        game.update()

        monkeypatch.setattr("Buttons.Turn.GamestateHelper", lambda channel: game)
        rendered = {}

        def capture_restored_leave_window(game_arg, player, last_player_color):
            rendered["can_leave"] = AllianceButtons.canLeaveAlliance(game_arg, player, "nova")
            return "view"

        monkeypatch.setattr(
            TurnButtons, "getStartTurnButtons", staticmethod(capture_restored_leave_window)
        )

        run(TurnButtons.restartTurn(blue, game, FakeInteraction()))

        assert rendered["can_leave"] is can_leave
