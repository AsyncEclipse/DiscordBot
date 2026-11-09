import pytest

from Buttons.Influence import InfluenceButtons
from tests.fakes import FakeInteraction, buttons, reload


@pytest.mark.parametrize("faction, initial_ships, refreshed", [
    ("ra", 1, 2), ("tm", 1, 2), ("hyd", 1, 3),
])
def test_influence_refreshes_the_factions_colony_ship_allowance(
        start_game, press, faction, initial_ships, refreshed):
    game, channel = start_game(factions=[faction, "eri"])
    game.get_player(1)["colony_ships"] = initial_ships
    game.update()

    press(channel, 1, "FCIDblue_startInfluence")
    allowance = refreshed - initial_ships
    assert f"Refresh {allowance} Colony Ship{'s' if allowance > 1 else ''}" in buttons(channel).values()
    press(channel, 1, "FCIDblue_refreshPopShips")

    assert reload(game).get_player(1)["colony_ships"] == refreshed


@pytest.mark.parametrize("faction, activations", [("wra", 1), ("hyd", 2)])
def test_relocating_discs_uses_one_activation_each(start_game, run, faction, activations):
    game, channel = start_game(factions=[faction, "eri"])
    player = game.get_player(1)
    interaction = FakeInteraction(channel)
    for position in ("102", "103", "104", "105", "106", "101"):
        game.add_tile(position, 0, "102")
    for position in ("102", "103", "106"):
        game.add_control("blue", position)
    run(InfluenceButtons.startInfluence(game, player, interaction))

    for source, destination in list(zip(("102", "103"), ("104", "105")))[:activations]:
        run(InfluenceButtons.removeInfluenceFinish(
            game, interaction, f"removeInfluenceFinish_{source}_normal", True, player))
        run(InfluenceButtons.addInfluenceFinish(game, player, interaction, f"addInfluenceFinish_{destination}"))
        assert game.gamestate["board"][source]["owner"] == 0
        assert game.gamestate["board"][destination]["owner"] == "blue"

    run(InfluenceButtons.removeInfluenceFinish(
        game, interaction, "removeInfluenceFinish_106_normal", True, player))
    run(InfluenceButtons.addInfluenceFinish(game, player, interaction, "addInfluenceFinish_101"))
    assert game.gamestate["board"]["106"]["owner"] == "blue"
    assert game.gamestate["board"]["101"]["owner"] == 0


def test_placing_from_the_track_does_not_allow_a_free_removal_afterwards(start_game, run):
    game, channel = start_game(factions=["wra", "eri"])
    player = game.get_player(1)
    game.add_tile("102", 0, "102")
    interaction = FakeInteraction(channel)
    run(InfluenceButtons.startInfluence(game, player, interaction))
    run(InfluenceButtons.addInfluenceFinish(game, player, interaction, "addInfluenceFinish_102"))

    run(InfluenceButtons.removeInfluenceFinish(
        game, interaction, "removeInfluenceFinish_201_normal", True, player))

    assert game.gamestate["board"]["201"]["owner"] == "blue"
    assert game.gamestate["board"]["102"]["owner"] == "blue"
