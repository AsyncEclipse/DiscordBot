"""A prompt that only expects one answer must not resolve twice."""
from tests.fakes import FakeMessage


def test_a_second_answer_on_the_same_message_is_ignored(start_game, press):
    _game, channel = start_game()
    # Two different answers of the accept/decline prompt, clicked off one Discord message.
    message = FakeMessage()
    press(channel, 2, "FCIDred_acceptRelationsWith_blue", message)
    refused = press(channel, 2, "FCIDred_declineRelationsWith_blue", message)

    assert "already answered" in refused.followup.sent[0][0]
    assert not any("been refused" in (content or "") for content, _kwargs in channel.sent)


def test_a_menu_press_does_not_consume_the_message(start_game, press):
    _game, channel = start_game()
    message = FakeMessage()
    press(channel, 1, "FCIDblue_showReputation", message)
    press(channel, 1, "FCIDblue_startExplore", message)

    assert any("select the tile you would like to explore" in (content or "")
               for content, _kwargs in channel.sent)
