"""A retried button ack counts as acknowledged even when Discord calls it a duplicate."""
from types import SimpleNamespace

import discord
import pytest

from listeners.ButtonListener import acknowledge

DUPLICATE = {"code": 40060, "message": "Interaction has already been acknowledged."}


class Responder:
    def __init__(self, error=None):
        self.error = error

    async def defer(self, **kwargs):
        if self.error is not None:
            raise self.error


def http_error(body):
    return discord.HTTPException(SimpleNamespace(status=400, reason="Bad Request"), body)


def test_a_duplicate_acknowledgement_is_a_success(run):
    run(acknowledge(SimpleNamespace(response=Responder(http_error(DUPLICATE)))))


def test_another_http_error_still_raises(run):
    with pytest.raises(discord.HTTPException):
        run(acknowledge(SimpleNamespace(response=Responder(
            http_error({"code": 50035, "message": "Invalid Form Body"})))))
