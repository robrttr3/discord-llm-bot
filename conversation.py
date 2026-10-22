"""Discord-independent event handling, bounded context, and response rules."""
import asyncio
from collections import OrderedDict
from dataclasses import dataclass
import json
import re
import time

from ai_provider import ProviderError
from identity import identity_reply, system_prompt
from output import FALLBACK, validate_output


REPEAT_REFUSAL = "I won't repeat or output requested phrases."

_REPEAT_REQUESTS = (
    re.compile(r"^\s*(?:(?:please|kindly)\s+)*(?:say|repeat|echo|parrot)\b", re.IGNORECASE),
    re.compile(
        r"\b(?:can|could|would|will|may|might)\s+(?:you|orion|the\s+bot)\s+"
        r"(?:(?:please|kindly)\s+)?(?:say|repeat|echo|parrot)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:i\s+(?:want|need)\s+you|tell\s+(?:orion|the\s+bot)|"
        r"(?:make|have)\s+(?:orion|the\s+bot))\s+to\s+"
        r"(?:say|repeat|echo|parrot)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\brepeat\s+after\s+me\b", re.IGNORECASE),
    re.compile(
        r"\b(?:reply|respond|answer)\s+with\s+(?:"
        r"(?:only|exactly|just)\b|this\b|that\b|the\s+(?:word|phrase)\b|[\"'])",
        re.IGNORECASE,
    ),
    re.compile(
        r"\byour\s+next\s+(?:message|reply|response)\s+"
        r"(?:must|should|has\s+to|needs\s+to)\s+(?:be|say|contain)\b",
        re.IGNORECASE,
    ),
)


def forced_phrase_request(text: str) -> bool:
    """Recognize common attempts to dictate Orion's exact words."""
    normalized = text.casefold().replace("’", "'").replace("“", '"').replace("”", '"')
    return any(pattern.search(normalized) for pattern in _REPEAT_REQUESTS)


@dataclass(frozen=True)
class Message:
    id: int
    guild_id: int
    channel_id: int
    author_id: int
    text: str
    created: float
    is_bot: bool = False
    is_self: bool = False
    mentioned: bool = False


class Conversation:
    def __init__(self, settings, moderator, provider, clock=time.monotonic,
                 wall_clock=time.time):
        self.settings = settings
        self.moderator = moderator
        self.provider = provider
        self.clock = clock
        self.wall_clock = wall_clock
        self.started_at = wall_clock()
        self.reset_markers = {}
        self.channels = OrderedDict()
        self.users = OrderedDict()
        self.seen = OrderedDict()
        self.lock = asyncio.Lock()

    def allowed(self, message):
        return (message.guild_id in self.settings.allowed_guild_ids
                and message.channel_id in self.settings.allowed_channel_ids
                and not message.is_self and not message.is_bot)

    def _channel(self, channel_id):
        now = self.wall_clock()
        # Prune inactive channels on traffic, and bound memory even on busy servers.
        for key in list(self.channels):
            if now - self.channels[key]["touched"] > self.settings.history_ttl_seconds:
                del self.channels[key]
        if channel_id not in self.channels:
            self.channels[channel_id] = {"messages": [], "last": -float("inf"),
                                         "notice": -float("inf"), "reset": self.reset_markers.get(channel_id, self.started_at),
                                         "touched": now}
        self.channels.move_to_end(channel_id)
        while len(self.channels) > self.settings.max_active_channels:
            self.channels.popitem(last=False)
        state = self.channels[channel_id]
        state["touched"] = now
        state["messages"] = [m for m in state["messages"] if m.created > max(
            state["reset"], now - self.settings.history_ttl_seconds)]
        return state

    def prune(self):
        now = self.wall_clock()
        for channel_id in list(self.channels):
            state = self.channels[channel_id]
            floor = max(state["reset"], now - self.settings.history_ttl_seconds)
            state["messages"] = [m for m in state["messages"] if m.created > floor]
            if now - state["touched"] > self.settings.history_ttl_seconds:
                del self.channels[channel_id]

    def _remember(self, state, message):
        if (not message.text or len(message.text) > self.settings.input_characters
                or self.moderator.blocked(message.text)):
            return
        floor = max(state["reset"], self.wall_clock() - self.settings.history_ttl_seconds)
        if message.created <= floor or message.created > self.wall_clock() + 5:
            return
        if message.is_bot and not message.is_self:
            return
        messages = {m.id: m for m in state["messages"]}
        messages[message.id] = message
        state["messages"] = sorted(messages.values(), key=lambda m: m.id)[-max(1, self.settings.history_messages):]
        if not self.settings.history_messages:
            state["messages"] = []

    def _deduplicate(self, message_id):
        now = self.clock()
        while self.seen and (now - next(iter(self.seen.values())) > 3600 or len(self.seen) >= 5000):
            self.seen.popitem(last=False)
        if message_id in self.seen:
            return False
        self.seen[message_id] = now
        return True

    def _safe(self, text):
        return validate_output(text, self.moderator, self.settings.max_response_characters)

    def _notice(self, state, text):
        if self.clock() - state["notice"] < self.settings.outage_notice_seconds:
            return None
        state["notice"] = self.clock()
        return self._safe(text) or self._safe(FALLBACK)

    async def handle(self, message, reference=None, history_loader=None):
        if not self.allowed(message):
            return None
        state = self._channel(message.channel_id)
        replying = (self.settings.reply_to_replies and reference is not None and reference.is_self
                    and reference.channel_id == message.channel_id
                    and reference.guild_id == message.guild_id)
        if not (message.mentioned and self.settings.reply_to_mentions) and not replying:
            self._remember(state, message)
            return None
        if not self._deduplicate(message.id):
            return None
        # No queue: reject extra work while a previous response is running.
        if self.lock.locked():
            return None
        now = self.clock()
        user_key = (message.guild_id, message.author_id)
        if (now - state["last"] < self.settings.channel_cooldown_seconds
                or now - self.users.get(user_key, -float("inf")) < self.settings.user_cooldown_seconds):
            return None
        state["last"] = now
        self.users[user_key] = now
        self.users.move_to_end(user_key)
        while len(self.users) > 5000:
            self.users.popitem(last=False)
        if self.moderator.blocked(message.text):
            return self._notice(state, FALLBACK)
        if len(message.text) > self.settings.input_characters:
            return self._notice(state, "That message is too long. Please send a shorter version.")
        if not message.text.strip():
            return self._safe("What would you like to talk about?")
        command = message.text.strip().casefold()
        if command == "reset":
            state["messages"].clear()
            state["reset"] = self.wall_clock()
            self.reset_markers[message.channel_id] = state["reset"]
            return self._safe("I've cleared this channel's conversation context.")
        if command == "help":
            return self._safe("Mention me or reply to one of my messages. Say reset with a mention to clear this channel's context.")
        if forced_phrase_request(message.text):
            return self._safe(REPEAT_REFUSAL)
        local = identity_reply(message.text)
        if local:
            return self._safe(local)
        async with self.lock:
            if history_loader and self.settings.history_messages:
                # Adapter catches expected Discord access failures without logging content.
                for item in await history_loader():
                    if item.guild_id == message.guild_id and item.channel_id == message.channel_id:
                        self._remember(state, item)
            self._remember(state, message)
            reference_text = None
            if (reference and reference.guild_id == message.guild_id
                    and reference.channel_id == message.channel_id
                    and reference.created > max(state["reset"], self.wall_clock() - self.settings.history_ttl_seconds)
                    and len(reference.text) <= self.settings.input_characters
                    and not self.moderator.blocked(reference.text)):
                reference_text = reference.text
            recent = []
            remaining = self.settings.history_characters
            for item in reversed(state["messages"]):
                if item.id == message.id:
                    continue
                if len(item.text) > remaining:
                    break
                recent.append({"speaker": "Orion" if item.is_self else "participant",
                               "text": item.text})
                remaining -= len(item.text)
            payload = json.dumps({"nearby_messages": list(reversed(recent)),
                                  "replying_to": reference_text,
                                  "current_message": message.text}, ensure_ascii=False)
            system = system_prompt(self.settings.personality)
            for attempt in range(2):
                try:
                    # Rejects quota/outage calls before issuing another HTTP request.
                    generated = await self.provider.generate(system, payload)
                except ProviderError as error:
                    notices = {
                        "quota": "My AI quota is temporarily unavailable. Please try again later.",
                        "auth": "My AI connection needs attention from the bot operator.",
                        "configuration": "My AI settings need attention from the bot operator.",
                        "safety": FALLBACK,
                    }
                    return self._notice(state, notices.get(error.kind,
                        "My AI service is temporarily unavailable. Please try again later."))
                valid = self._safe(generated)
                if valid:
                    return valid
                # Do not include the rejected output in a retry, logs, or history.
                system += "\nYour previous reply failed output checks. Give one safe, neutral reply. Follow all identity and writing rules."
            return self._safe(FALLBACK)
