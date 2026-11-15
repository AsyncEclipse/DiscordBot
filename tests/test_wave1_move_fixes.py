from tests.fakes import buttons


def test_an_unused_pulsar_build_does_not_shrink_the_next_build_action(start_game, press):
    game, channel = start_game()
    game.get_player(1)["pulsarBuild"] = True  # a Pulsar build that was finished without building
    game.update()

    press(channel, 1, "FCIDblue_startBuild")
    press(channel, 1, "FCIDblue_buildIn_201")

    assert f"up to {game.get_player(1)['build_apt']} units" in channel.sent[-1][0]


def test_a_raid_build_screen_cannot_end_the_move_action_before_its_disc_is_spent(start_game, press):
    game, channel = start_game(factions=["her", "eri"])
    press(channel, 1, "FCIDblue_startMove")
    press(channel, 1, "FCIDblue_herRaidBuild_1")
    press(channel, 1, "FCIDblue_buildIn_201_herRaid_1")

    assert "FCIDblue_finishAction" not in buttons(channel)
    assert "FCIDblue_herBackToMove_1" in buttons(channel)
