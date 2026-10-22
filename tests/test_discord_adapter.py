from dataclasses import replace
from datetime import datetime, timezone
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock

from config import Settings
from main import OrionClient
from moderation import Moderator


class AdapterTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.provider = SimpleNamespace(generate=AsyncMock(return_value="A useful reply."))
        self.bot = OrionClient(replace(Settings(), allowed_guild_ids=(1,), allowed_channel_ids=(2,)),
                               Moderator(["blockedexample"]), self.provider)
        self.addAsyncCleanup(self.bot.close)
        self.bot._connection.user = SimpleNamespace(id=99)
        self.now = 100
        self.bot.engine.clock = lambda: self.now
        self.sequence = 10
        self.channel = SimpleNamespace(id=2, fetch_message=AsyncMock())
        self.channel.send = AsyncMock(side_effect=self.sent)
        self.channel.history = self.history
        self.history_items = []

    def raw(self, text, author=4, bot=False, mention=True, reference=None):
        self.sequence += 1
        return SimpleNamespace(id=self.sequence, guild=SimpleNamespace(id=1), channel=self.channel,
                               author=SimpleNamespace(id=author, bot=bot), content=text,
                               created_at=datetime.now(timezone.utc), reference=reference,
                               mentions=[SimpleNamespace(id=99)] if mention else [])

    def sent(self, text, **kwargs):
        return self.raw(text, author=99, bot=True, mention=False)

    async def history(self, **kwargs):
        for item in self.history_items:
            yield item

    async def test_client_uses_minimal_intents_and_no_cache(self):
        self.assertTrue(self.bot.intents.guilds)
        self.assertTrue(self.bot.intents.guild_messages)
        self.assertTrue(self.bot.intents.message_content)
        self.assertFalse(self.bot.intents.members)
        self.assertFalse(self.bot.intents.presences)
        self.assertFalse(self.bot.intents.dm_messages)
        self.assertIsNone(self.bot._connection._messages)

    async def test_mention_flows_through_official_client_and_safe_sender(self):
        self.provider.generate.return_value = "Hello\U0001f600\u2014there :D"
        await self.bot.on_message(self.raw("<@99> Hello"))
        self.provider.generate.assert_awaited_once()
        self.channel.send.assert_awaited_once()
        self.assertEqual(self.channel.send.call_args.args[0], "Hello, there")
        self.assertTrue(self.channel.send.call_args.kwargs["suppress_embeds"])
        self.assertIn('"current_message": "Hello"', self.provider.generate.call_args.args[1])

    async def test_fetch_reply_reference_and_reply_without_mention(self):
        original = self.raw("A previous idea.", author=99, bot=True, mention=False)
        self.channel.fetch_message.return_value = original
        ref = SimpleNamespace(channel_id=2, message_id=original.id, resolved=None)
        await self.bot.on_message(self.raw("Why?", mention=False, reference=ref))
        self.channel.fetch_message.assert_awaited_once_with(original.id)
        self.channel.send.assert_awaited_once()
        self.assertIn("A previous idea.", self.provider.generate.call_args.args[1])

    async def test_unauthorized_channel_never_fetches_or_sends(self):
        self.channel.id = 77
        ref = SimpleNamespace(channel_id=77, message_id=1, resolved=None)
        await self.bot.on_message(self.raw("<@99> Hello", reference=ref))
        self.channel.fetch_message.assert_not_awaited()
        self.channel.send.assert_not_awaited()
        self.provider.generate.assert_not_awaited()

    async def test_other_bot_and_self_never_loop(self):
        for author in (99, 55):
            await self.bot.on_message(self.raw("<@99> Hello", author=author, bot=True))
        self.channel.send.assert_not_awaited()
        self.provider.generate.assert_not_awaited()

    async def test_cross_channel_reference_never_fetched(self):
        ref = SimpleNamespace(channel_id=77, message_id=1, resolved=None)
        await self.bot.on_message(self.raw("why?", mention=False, reference=ref))
        self.channel.fetch_message.assert_not_awaited()
        self.channel.send.assert_not_awaited()

    async def test_local_identity_uses_safe_sender(self):
        await self.bot.on_message(self.raw("<@!99> Who created you?"))
        self.provider.generate.assert_not_awaited()
        self.assertEqual(self.channel.send.call_args.args[0], "I'm Orion. Rontgen created me.")

    async def test_disabled_triggers_are_silent(self):
        self.bot.engine.settings = replace(self.bot.settings, reply_to_mentions=False, reply_to_replies=False)
        await self.bot.on_message(self.raw("<@99> Hello"))
        self.channel.send.assert_not_awaited()

    async def test_background_cleanup_starts_and_stops(self):
        await self.bot.setup_hook()
        self.assertFalse(self.bot.cleanup_task.done())
        await self.bot.close()
        self.assertTrue(self.bot.cleanup_task.cancelled())
