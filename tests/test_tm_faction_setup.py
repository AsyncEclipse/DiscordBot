from Buttons.Research import ResearchButtons
from tests.fakes import FakeInteraction, buttons


def test_only_techno_mages_are_offered_the_pregame_tech(start_game, run):
    game, channel = start_game(factions=["hyd", "eri"])
    run(ResearchButtons.offerSetupTech(game, game.get_player(1), FakeInteraction(channel)))
    assert not [content for content, _ in channel.sent]

    game, channel = start_game(factions=["tm", "eri"])
    run(ResearchButtons.offerSetupTech(game, game.get_player(1), FakeInteraction(channel)))
    assert "FCIDblue_setupTech" in buttons(channel)
