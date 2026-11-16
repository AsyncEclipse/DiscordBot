from commands.tile_commands import TileCommands
from tests.fakes import FakeInteraction, offered_ids


def test_resolving_a_discovery_tile_gives_the_choice_to_the_sector_owner(start_game, run):
    _game, channel = start_game()
    interaction = FakeInteraction(channel, user_id=2)  # red runs it for blue's home sector

    cog = TileCommands(None)
    run(cog.resolve_specific_discovery_tile.callback(cog, interaction, "201", "rep"))

    ids = offered_ids(interaction)
    assert ids and all(cid.startswith("FCIDblue_") for cid in ids)


def test_resolving_a_discovery_tile_on_an_unowned_sector_says_so(start_game, run):
    game, channel = start_game()
    game.gamestate["board"]["201"]["owner"] = 0
    game.update()
    interaction = FakeInteraction(channel, user_id=2)

    cog = TileCommands(None)
    run(cog.resolve_specific_discovery_tile.callback(cog, interaction, "201", "rep"))

    assert "Nobody controls tile 201" in interaction.followup.sent[0][0]
