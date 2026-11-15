def test_an_unused_pulsar_build_does_not_shrink_the_next_build_action(start_game, press):
    game, channel = start_game()
    game.get_player(1)["pulsarBuild"] = True  # a Pulsar build that was finished without building
    game.update()

    press(channel, 1, "FCIDblue_startBuild")
    press(channel, 1, "FCIDblue_buildIn_201")

    assert f"up to {game.get_player(1)['build_apt']} units" in channel.sent[-1][0]
