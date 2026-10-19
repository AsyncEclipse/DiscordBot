"""Founding, joining and leaving an Alliance, and the Act of Aggression rule."""
import re
from unittest.mock import AsyncMock

import discord
import pytest

from Buttons.Alliance import AllianceButtons
from Buttons.Turn import TurnButtons
from tests.fakes import FakeInteraction, POS, board_tile, offered_ids, player_helper, players


def _related(*colors):
    """Players who all hold Diplomatic Relations with each other."""
    game_players = players(*colors)
    for stats in game_players.values():
        stats["reputation_track"] = [f"amb-hydran-{color}" if color != stats["color"] else "mixed"
                                     for color in colors]
    return game_players


def _game(make_game, colors=("blue", "red", "green"), player_count=4, roundNum=3, owner=0, ships=()):
    game_players = _related(*colors)
    for stats in game_players.values():
        stats["allianceLeaveClosed"] = False
    return make_game({
        "alliances": True,
        "player_count": player_count,
        "roundNum": roundNum,
        "activePlayerColor": [colors[0]],
        "players": game_players,
        "board": board_tile(ships, owner),
    })


async def _alliance_button_ids(game, player):
    view = discord.ui.View()
    AllianceButtons.addAllianceButtons(view, game, player)
    return [button.custom_id for button in view.children]


async def _check_traitor(game, player):
    interaction = FakeInteraction()
    await TurnButtons.checkTraitor(game, player, interaction, player_helper(game, player["color"]))


def _last_round(game, _player):
    game.gamestate["roundNum"] = 8


def _not_blues_turn(game, _player):
    game.gamestate["activePlayerColor"] = ["red"]


def _spends_influence(game, player):
    player_helper(game, player["color"]).spend_influence_on_action("build")


def _adjusts_counter_only(game, player):
    player_helper(game, player["color"]).adjust_influence_on_action("build", 0)


class TestEligibility:
    def test_only_players_with_relations_can_found_together(self, make_game):
        game = _game(make_game)
        blue = game.getPlayerObjectFromColor("blue")
        # Green has relations with nobody: strip it from every track.
        for player in game.gamestate["players"].values():
            player["reputation_track"] = [t for t in player["reputation_track"] if "green" not in str(t)]
            if player["color"] == "green":
                player["reputation_track"] = ["mixed"] * 4

        founders = AllianceButtons.getPlayersToFoundWith(game, blue)
        assert [f["color"] for f in founders] == ["red"]

    def test_a_player_already_in_an_alliance_cannot_found_or_join(self, make_game):
        game = _game(make_game)
        game.formAlliance("nova", ["blue", "red"])
        blue = game.getPlayerObjectFromColor("blue")

        assert game.isInAlliance(blue)
        assert AllianceButtons.getPlayersToFoundWith(game, blue) == []
        assert AllianceButtons.getJoinableAlliances(game, blue) == []

    def test_an_unfounded_tile_is_needed_to_found(self, make_game):
        game = _game(make_game, colors=("blue", "red", "green", "yellow", "purple", "white"),
                     player_count=6)
        for tile, pair in zip(["nova", "flare", "vortex"],
                              [("blue", "red"), ("green", "yellow"), ("purple", "white")]):
            game.formAlliance(tile, list(pair))

        assert AllianceButtons.getPlayersToFoundWith(game, game.getPlayerObjectFromColor("blue")) == []

    def test_alliances_need_four_players(self, make_game):
        for player_count, expected in [(2, False), (3, False), (4, True)]:
            game = _game(make_game, player_count=player_count)
            blue = game.getPlayerObjectFromColor("blue")
            assert AllianceButtons.canUseAlliances(game, blue) is expected

    def test_alliances_can_be_formed_in_the_last_round(self, make_game, run):
        game = _game(make_game, roundNum=7)
        assert AllianceButtons.canUseAlliances(game, game.getPlayerObjectFromColor("blue"))
        game.gamestate["roundNum"] = 8
        game.update()

        ids = run(_alliance_button_ids(game, game.getPlayerObjectFromColor("blue")))
        assert any(custom_id.endswith("_startAlliance") for custom_id in ids)

    @pytest.mark.parametrize(("change", "window_open"), [
        (_last_round, False),
        (_not_blues_turn, False),
        (_spends_influence, False),
        (_adjusts_counter_only, True),
    ])
    def test_the_leave_window_closes_with_the_turn_and_the_first_action(
            self, make_game, run, change, window_open):
        game = _game(make_game)
        game.formAlliance("nova", ["blue", "red"])
        blue = game.getPlayerObjectFromColor("blue")
        change(game, blue)
        game.update()

        ids = run(_alliance_button_ids(game, blue))
        assert any(custom_id.endswith("_leaveAlliance_nova") for custom_id in ids) is window_open

        run(AllianceButtons.leaveAlliance(game, blue, FakeInteraction(), "leaveAlliance_nova"))

        assert (not game.isInAlliance(blue)) is window_open


class TestStaleButtons:
    @pytest.mark.parametrize("has_left", [False, True])
    def test_leaving_preserves_the_turn_menu(self, start_game, run, has_left):
        game, channel = start_game(4)
        game.setAlliances(True)
        game.formAlliance("nova", ["blue", "red"])
        blue = game.getPlayerObjectFromColor("blue")
        TurnButtons.startNewTurn(blue, game)

        async def leave_from_turn_menu():
            view = TurnButtons.getStartTurnButtons(game, blue, "yellow")
            message = await channel.send("Choose an action", view=view)
            message.delete = AsyncMock()
            if has_left:
                game.betrayAlliance("nova", "blue")
            interaction = FakeInteraction(channel)
            interaction.message = message

            await AllianceButtons.leaveAlliance(game, blue, interaction, "leaveAlliance_nova")

            message.delete.assert_not_awaited()
            assert any(button.custom_id == "FCIDblue_startResearch" for button in view.children)
            assert not game.isInAlliance(blue)
            assert game.gamestate["activePlayerColor"] == ["blue"]

        run(leave_from_turn_menu())

    @pytest.mark.parametrize("response", ["accept", "decline"])
    def test_founding_offer_can_be_answered_after_the_turn_moves_on(self, make_game, run, response):
        game = _game(make_game)
        blue = game.getPlayerObjectFromColor("blue")
        red = game.getPlayerObjectFromColor("red")
        inter = FakeInteraction()
        run(AllianceButtons.offerAllianceTo(game, blue, inter, "offerAllianceTo_red"))

        TurnButtons.startNewTurn(game.getPlayerObjectFromColor("green"), game)
        handler = (AllianceButtons.acceptAllianceWith if response == "accept"
                   else AllianceButtons.declineAllianceWith)
        run(handler(game, red, inter, f"{response}AllianceWith_blue"))

        assert game.areAllied("blue", "red") is (response == "accept")
        assert ("have founded" if response == "accept" else "declined") in inter.channel.sent[-1][0]

    @pytest.mark.parametrize("invalidated", ["variant", "player_count", "relations", "game_ended"])
    def test_stale_founding_accept_rechecks_eligibility(self, make_game, run, invalidated):
        game = _game(make_game, colors=("blue", "red", "green"), player_count=6)
        if invalidated == "variant":
            game.gamestate["alliances"] = False
        elif invalidated == "player_count":
            game.gamestate["player_count"] = 3
        elif invalidated == "relations":
            for player in game.gamestate["players"].values():
                player["reputation_track"] = ["mixed"] * 4
        elif invalidated == "game_ended":
            game.gamestate["gameEnded"] = True
        game.update()

        inter = FakeInteraction()
        run(AllianceButtons.acceptAllianceWith(game, game.getPlayerObjectFromColor("blue"), inter,
                                               "acceptAllianceWith_red"))

        assert not game.isInAlliance(game.getPlayerObjectFromColor("blue"))
        assert not game.getAllianceMembers("nova")

    def test_stale_founding_accept_rechecks_membership(self, make_game, run):
        game = _game(make_game, colors=("blue", "red", "green"), player_count=6)
        game.formAlliance("flare", ["red", "green"])

        inter = FakeInteraction()
        run(AllianceButtons.acceptAllianceWith(game, game.getPlayerObjectFromColor("blue"), inter,
                                               "acceptAllianceWith_red"))

        assert not game.isInAlliance(game.getPlayerObjectFromColor("blue"))
        assert game.getAllianceMembers("flare") == ["red", "green"]

    @pytest.mark.parametrize(("invalidated", "player_count"), [
        ("capacity", 6), ("relations", 4),
    ])
    def test_stale_join_agreement_rechecks_eligibility(self, make_game, run, invalidated, player_count):
        game = _game(make_game, colors=("blue", "red", "green", "yellow"), player_count=player_count)
        game.formAlliance("nova", ["blue", "red"])
        if invalidated == "capacity":
            # The stale request finalizes after another player fills the alliance.
            game.formAlliance("nova", ["yellow"])
        elif invalidated == "relations":
            for player in game.gamestate["players"].values():
                player["reputation_track"] = ["mixed"] * 4
        game.update()

        inter = FakeInteraction()
        run(AllianceButtons.agreeJoinAlliance(game, game.getPlayerObjectFromColor("blue"), inter,
                                              "agreeJoinAlliance_nova_green_none"))
        run(AllianceButtons.agreeJoinAlliance(game, game.getPlayerObjectFromColor("red"), inter,
                                              "agreeJoinAlliance_nova_green_blue"))
        if invalidated == "capacity":
            run(AllianceButtons.agreeJoinAlliance(game, game.getPlayerObjectFromColor("yellow"), inter,
                                                  "agreeJoinAlliance_nova_green_blue+red"))

        assert "green" not in game.getAllianceMembers("nova")


class TestJoining:
    def test_a_third_player_may_join_once_every_member_agrees(self, make_game, run):
        game = _game(make_game, colors=("blue", "red", "green", "yellow"), player_count=6)
        game.formAlliance("nova", ["blue", "red"])
        green = game.getPlayerObjectFromColor("green")

        assert "nova" in AllianceButtons.getJoinableAlliances(game, green)

        TurnButtons.startNewTurn(green, game)
        run(AllianceButtons.offerJoinAlliance(game, green, FakeInteraction(), "offerJoinAlliance_nova"))
        TurnButtons.startNewTurn(game.getPlayerObjectFromColor("yellow"), game)

        run(AllianceButtons.agreeJoinAlliance(game, game.getPlayerObjectFromColor("blue"),
                                              FakeInteraction(), "agreeJoinAlliance_nova_green_none"))
        assert game.getAllianceMembers("nova") == ["blue", "red"]

        run(AllianceButtons.agreeJoinAlliance(game, game.getPlayerObjectFromColor("red"),
                                              FakeInteraction(), "agreeJoinAlliance_nova_green_blue"))
        assert sorted(game.getAllianceMembers("nova")) == ["blue", "green", "red"]
        assert game.areAllied("green", "blue")

    def test_joining_is_refused_when_the_joiner_betrayed_that_alliance(self, make_game):
        game = _game(make_game, colors=("blue", "red", "green"), player_count=6)
        game.formAlliance("nova", ["blue", "red"])
        game.betrayAlliance("nova", "green")
        green = game.getPlayerObjectFromColor("green")

        assert "nova" not in AllianceButtons.getJoinableAlliances(game, green)

    def test_joining_is_refused_once_the_alliance_is_full(self, make_game):
        game = _game(make_game, colors=("blue", "red", "green"), player_count=4)
        game.formAlliance("nova", ["blue", "red"])

        # 4-player games cap an alliance at two.
        assert AllianceButtons.getJoinableAlliances(game, game.getPlayerObjectFromColor("green")) == []

    def test_a_stale_agree_button_cannot_add_an_unwilling_player(self, make_game, run):
        game = _game(make_game, colors=("blue", "red", "green"), player_count=6)
        game.formAlliance("nova", ["blue", "red"])
        game.formAlliance("flare", ["green"])

        run(AllianceButtons.agreeJoinAlliance(game, game.getPlayerObjectFromColor("blue"),
                                              FakeInteraction(), "agreeJoinAlliance_nova_green_none"))
        assert game.getAllianceMembers("nova") == ["blue", "red"]


class TestButtonDispatch:
    """A custom id nobody handles is a dead end, so every button the alliance
    UI builds has to appear in the listener's dispatch chain."""

    def _verbs(self):
        listener = open("listeners/ButtonListener.py").read()
        return re.findall(r'customID\.startswith\("([^"]+)"\)', listener)

    def _assert_dispatched(self, custom_ids):
        verbs = self._verbs()
        assert custom_ids
        for custom_id in custom_ids:
            stripped = custom_id.split("_", 1)[1]
            assert any(stripped.startswith(verb) for verb in verbs), \
                f"{custom_id} has no handler"

    def test_the_turn_buttons_are_dispatched(self, make_game, run):
        game = _game(make_game, colors=("blue", "red", "green"), player_count=6)
        player = game.getPlayerObjectFromColor("blue")

        async def collect():
            """Founding, allied, and betrayed all offer different buttons."""
            ids = []
            for stage in ("fresh", "allied", "betrayed"):
                if stage == "allied":
                    game.formAlliance("nova", ["blue", "red"])
                if stage == "betrayed":
                    game.betrayAlliance("nova", "blue")
                ids.extend(await _alliance_button_ids(game, player))
            return ids

        self._assert_dispatched(run(collect()))

    def test_the_offer_and_join_buttons_are_dispatched(self, make_game, run):
        game = _game(make_game, colors=("blue", "red", "green"), player_count=6)
        game.formAlliance("nova", ["blue", "red"])
        game.gamestate["activePlayerColor"] = ["green"]
        game.update()
        inter = FakeInteraction()

        run(AllianceButtons.offerJoinAlliance(game, game.getPlayerObjectFromColor("green"), inter,
                                              "offerJoinAlliance_nova"))
        self._assert_dispatched(offered_ids(inter))

        offer_game = _game(make_game, colors=("blue", "red", "green"), player_count=6)
        inter = FakeInteraction()
        run(AllianceButtons.offerAllianceTo(offer_game, offer_game.getPlayerObjectFromColor("blue"), inter,
                                            "offerAllianceTo_red"))
        self._assert_dispatched(offered_ids(inter))


class TestActOfAggression:
    def test_an_allies_presence_is_not_aggression(self, make_game, run):
        game = _game(make_game, ships=["blue-int", "red-int"], owner="red")
        game.formAlliance("nova", ["blue", "red"])
        blue = game.getPlayerObjectFromColor("blue")

        run(_check_traitor(game, blue))
        assert not blue.get("traitor")

    def test_aggression_against_a_former_ally_breaks_relations_once(self, make_game, run):
        game = _game(make_game, ships=["blue-int", "red-int"], owner="red")
        game.formAlliance("nova", ["blue", "red"])
        game.betrayAlliance("nova", "blue")
        blue = game.getPlayerObjectFromColor("blue")
        green = game.getPlayerObjectFromColor("green")

        run(_check_traitor(game, blue))

        assert blue.get("traitor")
        assert not any("red" in str(tile) for tile in blue["reputation_track"])

        # Someone else takes the card later; staying next to red must not take it back.
        game.makeEveryoneNotTraitor()
        green["traitor"] = True
        run(_check_traitor(game, blue))

        assert green["traitor"] and not blue.get("traitor")
