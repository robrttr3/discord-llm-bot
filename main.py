"""Official Discord bot entry point and credential-safe diagnostics."""
import argparse
import asyncio
from contextlib import suppress
import logging
import os
from pathlib import Path
import re
import sys

import discord
import httpx

from ai_provider import AIProvider, ProviderError
from config import ROOT, ConfigError, load_credentials, load_settings
from conversation import Conversation, Message
from identity import system_prompt
from moderation import Moderator
from output import FALLBACK, validate_output

logger = logging.getLogger("orion")


def record(message, self_id):
    return Message(
        id=message.id, guild_id=message.guild.id if message.guild else 0,
        channel_id=message.channel.id, author_id=message.author.id,
        text=re.sub(rf"<@!?{self_id}>", "", message.content).strip(),
        created=message.created_at.timestamp(), is_bot=message.author.bot,
        is_self=message.author.id == self_id,
        mentioned=any(user.id == self_id for user in message.mentions),
    )


class SafeSender:
    def __init__(self, moderator, max_length):
        self.moderator = moderator
        self.max_length = max_length

    async def send(self, channel, text):
        validated = validate_output(text, self.moderator, self.max_length)
        if validated is None:
            validated = validate_output(FALLBACK, self.moderator, self.max_length)
        if validated is None:
            logger.warning("Outgoing message suppressed by configured filters.")
            return None
        try:
            # No reply ping, @everyone, user mention, role mention, link embed, or TTS.
            return await channel.send(validated, allowed_mentions=discord.AllowedMentions.none(),
                                      suppress_embeds=True)
        except discord.HTTPException:
            logger.warning("Discord send failed. Check channel access and network availability.")
            return None


class OrionClient(discord.Client):
    def __init__(self, settings, moderator, provider):
        intents = discord.Intents.none()
        intents.guilds = True
        intents.guild_messages = True
        intents.message_content = True
        # No members, presences, direct messages, or typing events.
        super().__init__(intents=intents, allowed_mentions=discord.AllowedMentions.none(),
                         max_messages=None, proxy=os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy"))
        self.settings = settings
        self.engine = Conversation(settings, moderator, provider)
        self.sender = SafeSender(moderator, settings.max_response_characters)
        self.cleanup_task = None

    async def setup_hook(self):
        self.cleanup_task = asyncio.create_task(self._cleanup_context())

    async def _cleanup_context(self):
        while True:
            await asyncio.sleep(min(30, self.settings.history_ttl_seconds))
            self.engine.prune()

    async def close(self):
        if self.cleanup_task:
            self.cleanup_task.cancel()
            with suppress(asyncio.CancelledError):
                await self.cleanup_task
        await super().close()

    async def on_ready(self):
        logger.info("Orion connected. Listening only in configured server and channel IDs.")

    async def on_error(self, event_method, *args, **kwargs):
        # discord.py's default handler includes repr(event arguments) and tracebacks.
        logger.error("A Discord event failed. No message content was logged.")

    async def on_message(self, raw):
        if self.user is None:
            return
        message = record(raw, self.user.id)
        if not self.engine.allowed(message):
            return
        reference = None
        if self.settings.reply_to_replies and raw.reference and raw.reference.message_id:
            # Fetch only a reference in this same authorized channel.
            if raw.reference.channel_id == raw.channel.id:
                resolved = raw.reference.resolved
                try:
                    if not isinstance(resolved, discord.Message):
                        resolved = await raw.channel.fetch_message(raw.reference.message_id)
                    reference = record(resolved, self.user.id)
                except discord.HTTPException:
                    logger.info("Referenced message unavailable; mention handling remains available.")

        async def nearby():
            try:
                return [record(item, self.user.id) async for item in raw.channel.history(
                    limit=self.settings.history_messages, before=raw)]
            except discord.HTTPException:
                logger.info("Recent history unavailable; continuing with in-memory context.")
                return []

        reply = await self.engine.handle(message, reference, nearby)
        if reply:
            sent = await self.sender.send(raw.channel, reply)
            if sent:
                state = self.engine._channel(message.channel_id)
                self.engine._remember(state, record(sent, self.user.id))


async def run(args):
    settings = load_settings(args.config)
    moderator = Moderator(settings.extra_blocked_terms, settings.use_builtin_terms)
    if args.check_config:
        print("Configuration OK. Allowlists and output rules loaded. Credentials not tested.")
        return
    token, key = load_credentials(discord_required=not args.check_ai,
                                 ai_required=not args.check_discord, provider=settings.provider)
    if args.check_discord:
        async with httpx.AsyncClient(timeout=20, follow_redirects=False) as client:
            try:
                result = await client.get("https://discord.com/api/v10/users/@me",
                                          headers={"Authorization": "Bot " + token})
                if result.status_code != 200 or not result.json().get("bot"):
                    raise ConfigError("Discord bot authentication failed. Check or reset the BOT token.")
            except (httpx.HTTPError, ValueError):
                raise ConfigError("Discord connectivity check failed; no response body was logged.") from None
        print("Discord bot authentication OK. Gateway connection and channel permissions not yet tested.")
        return
    provider = AIProvider(settings, key)
    try:
        if args.check_ai:
            text = await provider.generate(system_prompt(settings.personality),
                                           '{"current_message":"Say hello briefly."}')
            valid = validate_output(text, moderator, settings.max_response_characters)
            if not valid:
                raise ConfigError("AI returned text that failed output checks. No content logged.")
            print("AI request and output validation OK. Model response omitted for privacy.")
            return
        bot = OrionClient(settings, moderator, provider)
        async with bot:
            # Disable dependency logs that could contain headers, URLs, or user data.
            await bot.start(token)
    finally:
        await provider.close()


def main():
    parser = argparse.ArgumentParser(description="Orion, an official Discord AI bot.")
    parser.add_argument("--config", type=Path, default=ROOT / "settings.toml",
                        help="Optional path to a non-secret TOML configuration.")
    checks = parser.add_mutually_exclusive_group()
    checks.add_argument("--check-config", action="store_true")
    checks.add_argument("--check-ai", action="store_true")
    checks.add_argument("--check-discord", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    for handler in logging.getLogger().handlers:
        handler.addFilter(lambda item: item.name == "orion")
    # Deliberately avoid raw third-party logs and exception strings.
    for name in ("discord", "httpx", "httpcore"):
        logging.getLogger(name).disabled = True
    try:
        asyncio.run(run(args))
    except (ConfigError, ValueError) as error:
        # ConfigError messages are authored locally, never provider error bodies.
        if isinstance(error, ConfigError):
            logger.error("%s", error)
        else:
            logger.error("Configuration could not be loaded. Check moderation settings.")
        sys.exit(1)
    except ProviderError as error:
        logger.error("AI diagnostic failed: %s. See README troubleshooting.", error.kind)
        sys.exit(1)
    except discord.LoginFailure:
        logger.error("Bot login failed. Check or reset DISCORD_BOT_TOKEN.")
        sys.exit(1)
    except discord.PrivilegedIntentsRequired:
        logger.error("Enable Message Content Intent for this bot in the Developer Portal.")
        sys.exit(1)
    except KeyboardInterrupt:
        print("Orion stopped. In-memory conversation context cleared.")
    except Exception:
        logger.error("Startup or connection failed. No credentials or message content logged. See README.")
        sys.exit(1)


if __name__ == "__main__":
    main()
