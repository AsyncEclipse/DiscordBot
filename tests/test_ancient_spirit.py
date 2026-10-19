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


def test_ancient_spirit_choice_shows_both_tile_images(make_game, run, monkeypatch):
    game = make_game({"discTiles": ["som", "jud"], "board": {"201": {"disctile": 1}}})
    player = {"name": "Atlantians", "player_name": "Blue", "color": "blue"}
    interaction = FakeInteraction()
    rendered_names = []
    render_tile = DrawHelper.show_disc_tile

    def record_tile(drawing, name):
        rendered_names.append(name)
        return render_tile(drawing, name)

    monkeypatch.setattr(DrawHelper, "show_disc_tile", record_tile)

    run(DiscoveryTileButtons.exploreDiscoveryTile(game, "201", interaction, player))

    content, options = interaction.channel.sent[-1]
    assert rendered_names == ["Jump Drive", "Soliton Missile"]
    assert [button.label for button in options["view"].children] == rendered_names
    assert len(options["files"]) == 2
    assert all(file.fp.getbuffer().nbytes > 0 for file in options["files"])
    assert "following the normal rules" not in content


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
        interaction, game, player, PlayerHelper("1", player),
        {"base_cost": 13, "min_cost": 9, "name": "Ancient Labs",
                                    "track": "any", "art_pt": 0, "infdisc": 0, "activ1": 0, "dtile": 1},
        "grid", "anl"))

    assert {custom_id.split("_")[2] for custom_id in buttons(interaction.channel)} == {"all", "rep"}
    assert game.gamestate["discTiles"] == []
