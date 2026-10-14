from Buttons.DiscoveryTile import DiscoveryTileButtons
from Buttons.Draft import DraftButtons
from Buttons.Research import ResearchButtons
from Buttons.Turn import TurnButtons
from helpers.DrawHelper import DrawHelper
from tests.fakes import FakeInteraction, buttons


def test_ancient_spirit_replaces_forbidden_tiles_before_offering_two_choices(make_game, run):
    game = make_game({
        "discTiles": ["all", "mat", "cru", "rep"],
        "board": {"201": {"disctile": 1}},
    })
    player = {"name": "Atlantians", "player_name": "Blue", "color": "blue"}
    interaction = FakeInteraction()

    run(DiscoveryTileButtons.exploreDiscoveryTile(game, "201", interaction, player))

    offered = buttons(interaction.channel)
    assert {custom_id.split("_")[1] for custom_id in offered} == {"selectDiscTile"}
    assert {custom_id.split("_")[3] for custom_id in offered} == {"rep", "all"}
    assert game.gamestate["discTiles"] == []
    assert game.gamestate["board"]["201"]["disctile"] == 0
    assert "discarded" in interaction.channel.sent[-1][0]
    assert "Gain 1 VP for every 3 Points of Reputation" in interaction.channel.sent[-1][0]
    assert "Gain 3 Money, 2 Materials and 2 Science" in interaction.channel.sent[-1][0]


def test_ancient_spirit_handles_deck_with_only_forbidden_tiles(make_game, run):
    game = make_game({
        "discTiles": ["mat", "cru"],
        "board": {"201": {"disctile": 1}},
    })
    player = {"name": "Atlantians", "player_name": "Blue", "color": "blue"}
    interaction = FakeInteraction()

    run(DiscoveryTileButtons.exploreDiscoveryTile(game, "201", interaction, player))

    assert not buttons(interaction.channel)
    assert "No eligible discovery tiles remain" in interaction.channel.sent[-1][0]
    assert game.gamestate["discTiles"] == []
    assert game.gamestate["board"]["201"]["disctile"] == 1


def test_ancient_spirit_choice_can_only_be_resolved_once(make_game, run, monkeypatch):
    game = make_game({
        "discTiles": ["all", "rep"],
        "board": {"201": {"disctile": 1}},
    })
    player = {"name": "Atlantians", "player_name": "Blue", "color": "blue"}
    interaction = FakeInteraction()

    monkeypatch.setattr(DrawHelper, "show_disc_tile", lambda drawing, name: None)
    run(DiscoveryTileButtons.exploreDiscoveryTile(game, "201", interaction, player))
    run(DiscoveryTileButtons.selectDiscTile(game, interaction, "selectDiscTile_1_rep_201", player))

    assert not game.gamestate["pendingDiscoveryChoices"]
    assert "found a Ancient Might" in interaction.channel.sent[-1][0]
    sent_count = len(interaction.channel.sent)
    run(DiscoveryTileButtons.selectDiscTile(game, interaction, "selectDiscTile_1_all_201", player))

    assert len(interaction.channel.sent) == sent_count
    assert "no longer available" in interaction.followup.sent[-1][0]


def test_ancient_labs_research_uses_ancient_spirit_choice(make_game, run, monkeypatch):
    player = {
        "name": "Atlantians", "player_name": "Blue", "color": "blue", "home_planet": "home",
        "science": 20, "materials": 0, "money": 0, "trade_value": 3,
        "military_tech": [], "grid_tech": [], "nano_tech": [], "reputation_track": [],
    }
    game = make_game({"discTiles": ["all", "mat", "rep"], "board": {"201": {"disctile": 0}}})
    game.get_player_from_color = lambda color: "1"
    game.getLocationFromID = lambda home_planet: "201"
    game.update_player = lambda player_helper: None
    game.playerResearchTech = lambda player_id, tech, tech_type: player["grid_tech"].append(tech)
    game.addDiscTile = lambda tile: game.gamestate["board"][tile].update(disctile=1)
    monkeypatch.setattr(DrawHelper, "show_tech_ref_image", lambda name, track: None)
    interaction = FakeInteraction()

    run(ResearchButtons.handle_specific_tech_selection(
        interaction, game, player, {"base_cost": 13, "min_cost": 9, "name": "Ancient Labs",
                                    "track": "any", "art_pt": 0, "infdisc": 0, "activ1": 0, "dtile": 1},
        "grid", "anl"))

    offered = buttons(interaction.channel)
    assert {custom_id.split("_")[3] for custom_id in offered} == {"all", "rep"}
    assert game.gamestate["discTiles"] == []


def test_other_factions_keep_the_single_tile_flow(make_game, run, monkeypatch):
    game = make_game({"discTiles": ["mat"], "board": {"201": {"disctile": 1}}})
    player = {"name": "Hydran Progress", "player_name": "Blue", "color": "blue"}
    interaction = FakeInteraction()
    monkeypatch.setattr(DrawHelper, "show_disc_tile", lambda drawing, name: None)

    run(DiscoveryTileButtons.exploreDiscoveryTile(game, "201", interaction, player))

    assert set(buttons(interaction.channel)) == {
        "FCIDblue_usedDiscForAbility_mat_201",
        "FCIDblue_keepDiscForPoints",
    }


def test_multiple_ancient_spirit_offers_keep_separate_pending_choices(make_game, run):
    game = make_game({
        "discTiles": ["all", "rep", "art", "sci"],
        "board": {"201": {"disctile": 1}, "203": {"disctile": 1}},
    })
    player = {"name": "Atlantians", "player_name": "Blue", "color": "blue"}
    interaction = FakeInteraction()

    run(DiscoveryTileButtons.exploreDiscoveryTile(game, "201", interaction, player))
    run(DiscoveryTileButtons.exploreDiscoveryTile(game, "203", interaction, player))

    assert set(game.gamestate["pendingDiscoveryChoices"]) == {"1", "2"}


def test_initial_ancient_labs_discovery_runs_once_during_setup(run, monkeypatch):
    class SetupGame:
        def __init__(self):
            self.gamestate = {
                "setup_finished": 0,
                "players": {"1": {"player_name": "Blue"}},
                "discTiles": ["all", "rep", "mat", "cru"],
            }

        def player_setup(self, player_id, faction, color, interaction):
            if self.gamestate["setup_finished"]:
                return
            self.gamestate["players"][str(player_id)].update({
                "name": "Atlantians", "color": color, "home_planet": "201", "nano_tech": ["anl"],
                "player_name": "Blue",
            })

        def get_player(self, player_id, interaction=None):
            return self.gamestate["players"][str(player_id)]

        def add_tile(self, position, rotation, tile, color=None):
            self.gamestate.setdefault("board", {})[position] = {"disctile": 0}

        def setup_finished(self):
            self.gamestate["setup_finished"] = 1

        def getLocationFromID(self, home_planet):
            return home_planet

        def addDiscTile(self, tile):
            self.gamestate["board"][tile]["disctile"] = 1

        def update(self):
            pass

        def initilizeKey(self, key):
            self.gamestate[key] = []

        def addToKey(self, key, value):
            self.gamestate[key].append(value)

        def updatePingTime(self):
            pass

        def getPlayerEmoji(self, player):
            return "emoji"

        def displayPlayerStats(self, player):
            return ""

        async def showUpdate(self, title, interaction):
            pass

    monkeypatch.setattr(TurnButtons, "getStartTurnButtons", staticmethod(lambda game, player, previous: None))
    game = SetupGame()
    interaction = FakeInteraction()

    run(DraftButtons.generalSetup(interaction, game, [1], ["atl"]))
    assert len(game.gamestate["pendingDiscoveryChoices"]) == 1
    run(DraftButtons.generalSetup(interaction, game, [1], ["atl"]))

    assert len(game.gamestate["pendingDiscoveryChoices"]) == 1
