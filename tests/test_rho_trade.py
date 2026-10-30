"""Rho Indi's 3:2 money trade: the resource the build does not use stays with the player."""
from Buttons.Build import BuildButtons
from tests.fakes import FakeInteraction, player_stats


def _press_build_trade(make_game, run, faction, material="0", money="3", spent="4", cost="5"):
    game = make_game({"players": {"1": player_stats(faction, materials=int(material),
                                                    money=int(money), science=0)}})
    player = game.gamestate["players"]["1"]
    inter = FakeInteraction()
    button = f"convertResource_blue-int_{cost}_201_{material}_0_{money}_{spent}_Money"
    run(BuildButtons.convertResource(game, player, inter, button))
    return player, inter.message.edited["content"]


def test_rho_money_trade_keeps_the_second_resource_of_an_odd_cost(make_game, run):
    player, content = _press_build_trade(make_game, run, "rho")
    assert "Materials-1" in content
    assert "Money-0" in content
    assert "Resources spent: 5" in content


def test_other_factions_get_one_resource_per_trade(make_game, run):
    player, content = _press_build_trade(make_game, run, "hyd")
    assert "Materials-0" in content
    assert "Resources spent: 5" in content
