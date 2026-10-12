"""Founding, joining and leaving an Alliance, and the Act of Aggression rule."""
import pytest

from Buttons.Alliance import AllianceButtons
from tests.fakes import FakeInteraction, player_stats

POS = "101"


def _related(*colors):
    """Players who all hold Diplomatic Relations with each other."""
    players = {}
    for i, color in enumerate(colors, 1):
        stats = player_stats("hyd", color=color)
        stats["reputation_track"] = [f"amb-hydran-{other}" if other != color else "mixed" for other in colors]
        players[str(i)] = stats
    return players


def _game(make_game, colors=("blue", "red", "green"), player_count=4, roundNum=3, owner=0, ships=()):
    players = _related(*colors)
    for player in players.values():
        player["allianceLeaveClosed"] = False
    return make_game({
        "alliances": True,
        "player_count": player_count,
        "roundNum": roundNum,
        "activePlayerColor": [colors[0]],
        "players": players,
        "board": {POS: {"owner": owner, "sector": 101, "player_ships": list(ships), "disctile": 0}},
    })


def _color(game, name):
    for player in game.gamestate["players"].values():
        if player["color"] == name:
            return player
    return None


class TestEligibility:
    def test_only_players_with_relations_can_found_together(self, make_game):
        game = _game(make_game)
        blue = _color(game, "blue")
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
        blue = _color(game, "blue")

        assert game.isInAlliance(blue)
        assert AllianceButtons.getPlayersToFoundWith(game, blue) == []
        assert AllianceButtons.getJoinableAlliances(game, blue) == []

    def test_an_unfounded_tile_is_needed_to_found(self, make_game):
        game = _game(make_game, colors=("blue", "red", "green", "yellow", "purple", "white"),
                     player_count=6)
        for tile, pair in zip(["nova", "flare", "vortex"],
                              [("blue", "red"), ("green", "yellow"), ("purple", "white")]):
            game.formAlliance(tile, list(pair))

        assert AllianceButtons.getPlayersToFoundWith(game, _color(game, "blue")) == []

    def test_alliances_need_four_players(self, make_game):
        for player_count, expected in [(2, False), (3, False), (4, True)]:
            game = _game(make_game, player_count=player_count)
            assert AllianceButtons.canUseAlliances(game, _color(game, "blue")) is expected

    def test_alliances_can_be_formed_in_the_last_round(self, make_game, run):
        game = _game(make_game, roundNum=7)
        assert AllianceButtons.canUseAlliances(game, _color(game, "blue"))
        game.gamestate["roundNum"] = 8
        game.update()

        async def collect():
            import discord
            view = discord.ui.View()
            AllianceButtons.addAllianceButtons(view, game, _color(game, "blue"))
            return [button.custom_id for button in view.children]

        ids = run(collect())
        assert any(custom_id.endswith("_startAlliance") for custom_id in ids)

    def test_leaving_is_closed_in_the_last_round(self, make_game, run):
        game = _game(make_game, roundNum=8)
        game.formAlliance("nova", ["blue", "red"])

        inter = FakeInteraction()
        run(AllianceButtons.leaveAlliance(game, _color(game, "blue"), inter, "leaveAlliance_nova"))

        assert game.isInAlliance(_color(game, "blue"))

    def test_leave_button_is_not_offered_after_the_player_acts(self, make_game, run):
        game = _game(make_game)
        game.formAlliance("nova", ["blue", "red"])
        game.gamestate["activePlayerColor"] = ["blue"]
        _color(game, "blue")["allianceLeaveClosed"] = True
        game.update()

        async def collect():
            import discord
            view = discord.ui.View()
            AllianceButtons.addAllianceButtons(view, game, _color(game, "blue"))
            return [button.custom_id for button in view.children]

        ids = run(collect())
        assert not any(custom_id.endswith("_leaveAlliance_nova") for custom_id in ids)

    def test_stale_leave_is_rejected_after_action(self, make_game, run):
        game = _game(make_game)
        game.formAlliance("nova", ["blue", "red"])
        blue = _color(game, "blue")
        from helpers.PlayerHelper import PlayerHelper
        PlayerHelper(game.get_player_from_color("blue"), blue).spend_influence_on_action("build")
        game.update()

        inter = FakeInteraction()
        run(AllianceButtons.leaveAlliance(game, blue, inter, "leaveAlliance_nova"))

        assert game.isInAlliance(blue)

    def test_adjusting_an_action_counter_does_not_close_leave_window(self, make_game, run):
        game = _game(make_game)
        game.formAlliance("nova", ["blue", "red"])
        blue = _color(game, "blue")
        from helpers.PlayerHelper import PlayerHelper
        PlayerHelper(game.get_player_from_color("blue"), blue).adjust_influence_on_action("build", 0)
        game.update()

        inter = FakeInteraction()
        run(AllianceButtons.leaveAlliance(game, blue, inter, "leaveAlliance_nova"))

        assert not game.isInAlliance(blue)


class TestStaleButtons:
    @pytest.mark.parametrize("invalidated", ["variant", "player_count", "relations", "turn", "game_ended"])
    def test_stale_founding_accept_rechecks_eligibility(self, make_game, run, invalidated):
        game = _game(make_game, colors=("blue", "red", "green"), player_count=6)
        if invalidated == "variant":
            game.gamestate["alliances"] = False
        elif invalidated == "player_count":
            game.gamestate["player_count"] = 3
        elif invalidated == "relations":
            for player in game.gamestate["players"].values():
                player["reputation_track"] = ["mixed"] * 4
        elif invalidated == "turn":
            game.gamestate["activePlayerColor"] = ["green"]
        elif invalidated == "game_ended":
            game.gamestate["gameEnded"] = True
        game.update()

        inter = FakeInteraction()
        run(AllianceButtons.acceptAllianceWith(game, _color(game, "blue"), inter,
                                               "acceptAllianceWith_red"))

        assert not game.isInAlliance(_color(game, "blue"))
        assert not game.getAllianceMembers("nova")

    def test_stale_founding_accept_rechecks_membership(self, make_game, run):
        game = _game(make_game, colors=("blue", "red", "green"), player_count=6)
        game.formAlliance("flare", ["red", "green"])

        inter = FakeInteraction()
        run(AllianceButtons.acceptAllianceWith(game, _color(game, "blue"), inter,
                                               "acceptAllianceWith_red"))

        assert not game.isInAlliance(_color(game, "blue"))
        assert game.getAllianceMembers("flare") == ["red", "green"]

    @pytest.mark.parametrize("invalidated", ["capacity", "relations"])
    def test_stale_join_agreement_rechecks_capacity_and_relations(self, make_game, run, invalidated):
        player_count = 6 if invalidated == "capacity" else 4
        game = _game(make_game, colors=("blue", "red", "green", "yellow"), player_count=player_count)
        game.formAlliance("nova", ["blue", "red"])
        if invalidated == "capacity":
            # The stale request finalizes after another player fills the alliance.
            game.formAlliance("nova", ["yellow"])
        else:
            for player in game.gamestate["players"].values():
                player["reputation_track"] = ["mixed"] * 4

        inter = FakeInteraction()
        run(AllianceButtons.agreeJoinAlliance(game, _color(game, "blue"), inter,
                                              "agreeJoinAlliance_nova_green_none"))
        run(AllianceButtons.agreeJoinAlliance(game, _color(game, "red"), inter,
                                              "agreeJoinAlliance_nova_green_blue"))
        if invalidated == "capacity":
            run(AllianceButtons.agreeJoinAlliance(game, _color(game, "yellow"), inter,
                                                  "agreeJoinAlliance_nova_green_blue+red"))

        assert "green" not in game.getAllianceMembers("nova")

    def test_stale_join_agreement_rechecks_turn(self, make_game, run):
        game = _game(make_game, colors=("blue", "red", "green", "yellow"), player_count=6)
        game.formAlliance("nova", ["blue", "red"])
        game.gamestate["activePlayerColor"] = ["yellow"]
        game.update()

        inter = FakeInteraction()
        run(AllianceButtons.agreeJoinAlliance(game, _color(game, "blue"), inter,
                                              "agreeJoinAlliance_nova_green_none"))
        run(AllianceButtons.agreeJoinAlliance(game, _color(game, "red"), inter,
                                              "agreeJoinAlliance_nova_green_blue"))

        assert "green" not in game.getAllianceMembers("nova")

    def test_stale_leave_rechecks_turn(self, make_game, run):
        game = _game(make_game)
        game.formAlliance("nova", ["blue", "red"])
        game.gamestate["activePlayerColor"] = ["red"]
        game.update()

        inter = FakeInteraction()
        run(AllianceButtons.leaveAlliance(game, _color(game, "blue"), inter, "leaveAlliance_nova"))

        assert game.isInAlliance(_color(game, "blue"))


class TestJoining:
    def test_a_third_player_may_join_once_every_member_agrees(self, make_game, run):
        game = _game(make_game, colors=("blue", "red", "green"), player_count=6)
        game.formAlliance("nova", ["blue", "red"])
        green = _color(game, "green")

        assert "nova" in AllianceButtons.getJoinableAlliances(game, green)

        inter = FakeInteraction()
        run(AllianceButtons.agreeJoinAlliance(game, _color(game, "blue"), inter, "agreeJoinAlliance_nova_green_none"))
        assert game.getAllianceMembers("nova") == ["blue", "red"]

        inter = FakeInteraction()
        run(AllianceButtons.agreeJoinAlliance(game, _color(game, "red"), inter, "agreeJoinAlliance_nova_green_blue"))
        assert sorted(game.getAllianceMembers("nova")) == ["blue", "green", "red"]
        assert game.areAllied("green", "blue")

    def test_joining_is_refused_when_the_joiner_betrayed_that_alliance(self, make_game):
        game = _game(make_game, colors=("blue", "red", "green"), player_count=6)
        game.formAlliance("nova", ["blue", "red"])
        game.betrayAlliance("nova", "green")
        green = _color(game, "green")

        assert "nova" not in AllianceButtons.getJoinableAlliances(game, green)

    def test_joining_is_refused_once_the_alliance_is_full(self, make_game):
        game = _game(make_game, colors=("blue", "red", "green"), player_count=4)
        game.formAlliance("nova", ["blue", "red"])

        # 4-player games cap an alliance at two.
        assert AllianceButtons.getJoinableAlliances(game, _color(game, "green")) == []

    def test_a_stale_agree_button_cannot_add_an_unwilling_player(self, make_game, run):
        game = _game(make_game, colors=("blue", "red", "green"), player_count=6)
        game.formAlliance("nova", ["blue", "red"])
        game.formAlliance("flare", ["green"])

        inter = FakeInteraction()
        run(AllianceButtons.agreeJoinAlliance(game, _color(game, "blue"), inter, "agreeJoinAlliance_nova_green_none"))
        assert game.getAllianceMembers("nova") == ["blue", "red"]


class TestButtonDispatch:
    """A custom id nobody handles is a dead end, so every button the alliance
    UI builds has to appear in the listener's dispatch chain."""

    def _verbs(self):
        import re
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
        import discord
        from Buttons.Alliance import AllianceButtons
        game = _game(make_game, colors=("blue", "red", "green"), player_count=6)
        player = _color(game, "blue")

        async def collect():
            """Founding, allied, and betrayed all offer different buttons."""
            ids = []
            for stage in ("fresh", "allied", "betrayed"):
                if stage == "allied":
                    game.formAlliance("nova", ["blue", "red"])
                if stage == "betrayed":
                    game.betrayAlliance("nova", "blue")
                view = discord.ui.View()
                AllianceButtons.addAllianceButtons(view, game, player)
                ids.extend(child.custom_id for child in view.children)
            return ids

        self._assert_dispatched(run(collect()))

    def test_the_offer_and_join_buttons_are_dispatched(self, make_game, run):
        from Buttons.Alliance import AllianceButtons
        game = _game(make_game, colors=("blue", "red", "green"), player_count=6)
        game.formAlliance("nova", ["blue", "red"])
        game.gamestate["activePlayerColor"] = ["green"]
        game.update()
        inter = FakeInteraction()

        run(AllianceButtons.offerJoinAlliance(game, _color(game, "green"), inter,
                                              "offerJoinAlliance_nova"))
        join_ids = [child.custom_id for _content, kwargs in inter.channel.sent
                    for child in getattr(kwargs.get("view"), "children", [])]
        self._assert_dispatched(join_ids)

        offer_game = _game(make_game, colors=("blue", "red", "green"), player_count=6)
        inter = FakeInteraction()
        run(AllianceButtons.offerAllianceTo(offer_game, _color(offer_game, "blue"), inter,
                                            "offerAllianceTo_red"))
        offer_ids = [child.custom_id for _content, kwargs in inter.channel.sent
                     for child in getattr(kwargs.get("view"), "children", [])]
        self._assert_dispatched(offer_ids)


class TestActOfAggression:
    def test_an_allies_presence_is_not_aggression(self, make_game, run):
        game = _game(make_game, ships=["blue-int", "red-int"], owner="red")
        game.formAlliance("nova", ["blue", "red"])
        blue = _color(game, "blue")

        run(_check(game, blue))
        assert not blue.get("traitor")

    def test_a_former_ally_becomes_the_traitor_without_breaking_relations(self, make_game, run):
        game = _game(make_game, ships=["blue-int", "red-int"], owner="red")
        game.formAlliance("nova", ["blue", "red"])
        game.betrayAlliance("nova", "blue")
        blue = _color(game, "blue")
        relationsBefore = list(blue["reputation_track"])

        run(_check(game, blue))

        assert blue.get("traitor")
        assert blue["reputation_track"] == relationsBefore


async def _check(game, player):
    from Buttons.Turn import TurnButtons
    from helpers.PlayerHelper import PlayerHelper
    inter = FakeInteraction()
    inter.message = None
    helper = PlayerHelper(game.get_player_from_color(player["color"]), player)
    await TurnButtons.checkTraitor(game, player, inter, helper)
