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


def test_rho_research_counts_money_at_its_3_to_2_ratio(make_game, run):
    from Buttons.Research import ResearchButtons
    from helpers.PlayerHelper import PlayerHelper
    game = make_game({"players": {"1": player_stats("rho", science=0, materials=0, money=6)},
                      "available_techs": ["nea"]})
    player = game.gamestate["players"]["1"]
    inter = FakeInteraction()
    tech = {"base_cost": 4, "min_cost": 4, "name": "Test Tech", "track": "nano",
            "art_pt": 0, "infdisc": 0, "activ1": 0, "dtile": 0}

    run(ResearchButtons.handle_specific_tech_selection(inter, game, player, PlayerHelper("1", player),
                                                       tech, "nano", "nea"))

    assert not any("did not have enough" in content for content, _kwargs in inter.channel.sent)
