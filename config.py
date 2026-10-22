"""Read non-secret TOML settings and secret environment variables separately."""
from dataclasses import dataclass
from pathlib import Path
import os
import re
import tomllib
from urllib.parse import urlsplit

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent


class ConfigError(ValueError):
    pass


@dataclass(frozen=True)
class Settings:
    allowed_guild_ids: tuple[int, ...] = ()
    allowed_channel_ids: tuple[int, ...] = ()
    reply_to_mentions: bool = True
    reply_to_replies: bool = True
    provider: str = "gemini"
    model: str = "gemini-3.8-flash"
    base_url: str = "https://api.groq.com/openai/v1"
    personality: str = "Be casual, thoughtful, direct, and natural."
    history_messages: int = 8
    history_ttl_seconds: int = 600
    history_characters: int = 6000
    input_characters: int = 3000
    max_response_characters: int = 1800
    max_output_tokens: int = 1024
    request_timeout_seconds: int = 40
    user_cooldown_seconds: int = 15
    channel_cooldown_seconds: int = 8
    outage_notice_seconds: int = 120
    daily_request_limit: int = 100
    max_active_channels: int = 100
    extra_blocked_terms: tuple[str, ...] = ()
    use_builtin_terms: bool = True


def load_settings(path: Path = ROOT / "settings.toml") -> Settings:
    try:
        with path.open("rb") as file:
            data = tomllib.load(file)
        moderation = data.pop("moderation", {})
        data.update(moderation)
        for name in ("allowed_guild_ids", "allowed_channel_ids", "extra_blocked_terms"):
            if name in data:
                if not isinstance(data[name], list):
                    raise ConfigError(f"{name} must be a TOML list.")
                data[name] = tuple(data[name])
        settings = Settings(**data)
    except ConfigError:
        raise
    except (OSError, ValueError, TypeError):
        raise ConfigError("Cannot read settings.toml. Check its keys and TOML syntax.") from None
    for name in ("allowed_guild_ids", "allowed_channel_ids"):
        ids = getattr(settings, name)
        if not ids or any(type(item) is not int or item <= 0 for item in ids):
            raise ConfigError(f"Set {name} to a nonempty list of positive Discord IDs.")
        if len(ids) > 1000:
            raise ConfigError(f"{name} supports at most 1000 IDs.")
    bounds = {
        "history_messages": (0, 30), "history_ttl_seconds": (10, 3600),
        "history_characters": (100, 20000), "input_characters": (100, 6000),
        "max_response_characters": (100, 2000), "max_output_tokens": (64, 4096),
        "request_timeout_seconds": (5, 120), "user_cooldown_seconds": (1, 3600),
        "channel_cooldown_seconds": (1, 3600), "outage_notice_seconds": (10, 3600),
        "daily_request_limit": (1, 10000), "max_active_channels": (1, 1000),
    }
    for name, (low, high) in bounds.items():
        value = getattr(settings, name)
        if type(value) is not int or not low <= value <= high:
            raise ConfigError(f"{name} must be an integer from {low} to {high}.")
    if settings.provider not in ("gemini", "openai", "ollama"):
        raise ConfigError("provider must be gemini, openai, or ollama.")
    if any(type(getattr(settings, name)) is not bool for name in ("reply_to_mentions", "reply_to_replies")):
        raise ConfigError("reply_to_mentions and reply_to_replies must be true or false.")
    if not isinstance(settings.model, str) or not re.fullmatch(r"[A-Za-z0-9._:/-]{1,150}", settings.model):
        raise ConfigError("model contains unsupported characters.")
    if not isinstance(settings.personality, str) or len(settings.personality) > 2000:
        raise ConfigError("personality must be text of at most 2000 characters.")
    if type(settings.use_builtin_terms) is not bool or any(
        not isinstance(term, str) or not term.strip() or len(term) > 80
        for term in settings.extra_blocked_terms
    ):
        raise ConfigError("Invalid moderation settings.")
    try:
        url = urlsplit(settings.base_url)
        local = url.hostname in ("localhost", "127.0.0.1", "::1")
        if url.username or url.password or url.query or url.fragment or not url.hostname:
            raise ValueError
        if url.scheme != "https" and not (url.scheme == "http" and local and settings.provider == "ollama"):
            raise ValueError
    except (TypeError, ValueError):
        raise ConfigError("base_url must use HTTPS; local Ollama may use HTTP. No credentials or query strings.") from None
    return settings


def load_credentials(*, discord_required: bool = True, ai_required: bool = True,
                     provider: str = "gemini") -> tuple[str, str]:
    load_dotenv(ROOT / ".env", override=False)
    token = os.environ.get("DISCORD_BOT_TOKEN", "").strip()
    key = os.environ.get("ORION_AI_KEY", "").strip()
    for name, value, required in (
        ("DISCORD_BOT_TOKEN", token, discord_required),
        ("ORION_AI_KEY", key, ai_required and provider != "ollama"),
    ):
        if required and (not value or value.startswith("replace_with_")):
            raise ConfigError(f"Set {name} privately in .env or the process environment.")
    return token, key
