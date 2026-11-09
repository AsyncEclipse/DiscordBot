import pytest

from Buttons.DiscoveryTile import DiscoveryTileButtons
from Buttons.Research import ResearchButtons
from helpers.DrawHelper import DrawHelper
from helpers.PlayerHelper import PlayerHelper
from tests.fakes import FakeInteraction, buttons


@pytest.mark.parametrize("deck, offered", [
    (["all", "mat", "cru", "rep"], {"all", "rep"}),
    (["mat", "cru"], set()),
])
def test_ancient_spirit_skips_material_and_cruiser_tiles(make_game, run, deck, offered):
    game = make_game({"discTiles": deck, "board": {"201": {"disctile": 1}}})
    player = {"name": "Atlantians", "player_name": "Blue", "color": "blue"}
    interaction = FakeInteraction()

    run(DiscoveryTileButtons.exploreDiscoveryTile(game, "201", interaction, player))

    assert {custom_id.split("_")[2] for custom_id in buttons(interaction.channel)} == offered
    assert game.gamestate["discTiles"] == []


def test_ancient_spirit_discards_the_unchosen_tile(make_game, run):
    game = make_game({"discTiles": ["som", "jud"], "board": {"201": {"disctile": 1}}})
    player = {"name": "Atlantians", "player_name": "Blue", "color": "blue"}
    interaction = FakeInteraction()

    run(DiscoveryTileButtons.exploreDiscoveryTile(game, "201", interaction, player))
    run(DiscoveryTileButtons.selectDiscTile(game, interaction,
                                            "selectDiscTile_som_jud_201", player))

    assert game.gamestate["discTiles"] == []
    assert game.gamestate["discTilesDiscard"] == ["jud"]

    # The pile is empty, so the discard stack is shuffled back in and drawn from.
    assert game.getNextDiscTile("201") == "jud"
    assert game.gamestate["discTilesDiscard"] == []


def test_ancient_spirit_discards_material_cruiser_and_duplicate_draws(make_game, run):
    game = make_game({"discTiles": ["som", "som", "mat", "cru"],
                      "board": {"201": {"disctile": 1}}})
    player = {"name": "Atlantians", "player_name": "Blue", "color": "blue"}
    interaction = FakeInteraction()

    run(DiscoveryTileButtons.exploreDiscoveryTile(game, "201", interaction, player))

    assert game.gamestate["discTiles"] == []
    assert sorted(game.gamestate["discTilesDiscard"]) == ["cru", "mat", "som"]


def test_ancient_spirit_draws_from_the_discard_stack(make_game):
    game = make_game({"discTiles": [], "discTilesDiscard": ["rep", "art"],
                      "board": {"201": {}}})

    assert sorted(DiscoveryTileButtons.drawDiscoveryChoices(game, "201")) == ["art", "rep"]
    assert game.gamestate["discTiles"] == []
    assert game.gamestate["discTilesDiscard"] == []


def test_ancient_spirit_replenishes_between_choices(make_game):
    game = make_game({"discTiles": ["rep"], "discTilesDiscard": ["art"],
                      "board": {"201": {}}})

    assert DiscoveryTileButtons.drawDiscoveryChoices(game, "201") == ["rep", "art"]
    assert game.gamestate["discTilesDiscard"] == []


@pytest.mark.parametrize("sector_type, discards", [
    ("normal", ["mat", "cru"]),
    ("nebula", ["mat", "cru", "orb", "mon"]),
])
def test_ancient_spirit_stops_when_only_ineligible_discards_remain(make_game, sector_type, discards):
    game = make_game({"discTiles": ["rep"], "discTilesDiscard": discards,
                      "board": {"201": {"type": sector_type}}})

    assert DiscoveryTileButtons.drawDiscoveryChoices(game, "201") == ["rep"]
    assert game.gamestate["discTilesDiscard"] == discards


def test_existing_ancient_spirit_choice_still_resolves(make_game, run):
    game = make_game({"discTiles": [], "board": {"201": {"disctile": 0}}})
    player = {"name": "Atlantians", "player_name": "Blue", "color": "blue"}
    interaction = FakeInteraction()

    run(DiscoveryTileButtons.selectDiscTile(game, interaction, "selectDiscTile_som_201", player))

    assert "FCIDblue_usedDiscForAbility_som_201" in buttons(interaction.channel)
    assert not game.gamestate.get("discTilesDiscard")


def test_ancient_spirit_choice_shows_both_tile_images(make_game, run, monkeypatch):
    game = make_game({"discTiles": ["som", "jud"], "board": {"201": {"disctile": 1}}})
    player = {"name": "Atlantians", "player_name": "Blue", "color": "blue"}
    interaction = FakeInteraction()
    rendered_names = []
    tile_files = {name: object() for name in ("Jump Drive", "Soliton Missile")}

    def record_tile(drawing, name):
        rendered_names.append(name)
        return tile_files[name]

    monkeypatch.setattr(DrawHelper, "show_disc_tile", record_tile)

    run(DiscoveryTileButtons.exploreDiscoveryTile(game, "201", interaction, player))

    content, options = interaction.channel.sent[-1]
    assert rendered_names == ["Jump Drive", "Soliton Missile"]
    assert [button.label for button in options["view"].children] == rendered_names
    assert options["files"] == [tile_files[name] for name in rendered_names]
    assert "following the normal rules" not in content


def test_ancient_labs_research_uses_ancient_spirit_choice(make_game, run):
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
    interaction = FakeInteraction()

    run(ResearchButtons.handle_specific_tech_selection(
        interaction, game, player, PlayerHelper("1", player),
        {"base_cost": 13, "min_cost": 9, "name": "Ancient Labs",
                                    "track": "any", "art_pt": 0, "infdisc": 0, "activ1": 0, "dtile": 1},
        "grid", "anl"))

    assert {custom_id.split("_")[2] for custom_id in buttons(interaction.channel)} == {"all", "rep"}
    assert game.gamestate["discTiles"] == []
