import io
from types import SimpleNamespace

import discord
from PIL import Image

from helpers import FactionData
from helpers.EmojiHelper import Emoji


class FakeEmojiClient:
    def __init__(self):
        self.uploaded = {}

    async def create_application_emoji(self, name, image):
        self.uploaded[name] = image
        return SimpleNamespace(name=name)


def test_terran_token_names_keep_their_separator():
    assert Emoji.token_name("terran_alliance") == "terran_alliance_token"
    assert Emoji.token_name("atlantians") == "atlantianstoken"


def test_upload_adds_only_missing_community_tokens(run):
    application_emojis = [SimpleNamespace(name="atlantianstoken")]
    client = FakeEmojiClient()

    result = run(Emoji.upload_missing_tokens(client, application_emojis))

    expected = {Emoji.token_name(faction["artwork"])
                for faction in FactionData.FACTIONS.values() if faction.get("community")}
    assert set(client.uploaded) == expected - {"atlantianstoken"}
    assert {emoji.name for emoji in result} == expected
    for image in client.uploaded.values():
        with Image.open(io.BytesIO(image)) as png:
            assert png.size == (128, 128)


def test_upload_failure_preserves_existing_emojis_and_logs_the_error(run, monkeypatch, caplog):
    client = FakeEmojiClient()
    existing = [SimpleNamespace(name="atlantianstoken")]

    async def fail_upload(**kwargs):
        raise discord.HTTPException(SimpleNamespace(status=400, reason="quota"), "Emoji quota exceeded")

    monkeypatch.setattr(client, "create_application_emoji", fail_upload)
    result = run(Emoji.upload_missing_tokens(client, existing))

    assert result == existing
    assert "Could not upload faction token" in caplog.text
    assert "Emoji quota exceeded" in caplog.text
