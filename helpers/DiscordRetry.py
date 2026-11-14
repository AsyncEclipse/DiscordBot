"""One retry when a Discord request did not get through.

discord.py retries a reset connection only for errno 54/10054, which Linux never raises:
here the reset (errno 104) reaches the caller and the request is lost, so an interaction
is never acknowledged or a message never arrives. It retries 500/502/504/524, but not
503, so a single "Service Unavailable" in the middle of combat drops the report being
sent. install() puts one retry in front of the two request loops every call goes through:
the REST client, and the webhook adapter that answers interactions.

shortcut: the retry is blind, so a request that landed but lost its reply can repeat;
upgrade when discord.py retries ECONNRESET and 503 itself.
"""
import aiohttp
import discord
import discord.webhook.async_


def _retrying(call):
    async def request(*args, **kwargs):
        try:
            return await call(*args, **kwargs)
        except (aiohttp.ClientConnectionError, discord.DiscordServerError):
            return await call(*args, **kwargs)
    return request


def install(bot):
    """Give the bot's Discord traffic one retry; call once, before it connects."""
    bot.http.request = _retrying(bot.http.request)
    adapter = discord.webhook.async_.async_context.get()
    adapter.request = _retrying(adapter.request)
