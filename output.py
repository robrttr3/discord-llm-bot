"""One final validation gate used by every Discord send."""
import re
import unicodedata
import emoji
import regex

from identity import identity_violation

FALLBACK = "I can't help with that message."
_CUSTOM = re.compile(r"<a?:[A-Za-z0-9_]+:\d+>")
_SYMBOLS = regex.compile(r"[\p{Extended_Pictographic}\p{Regional_Indicator}\p{Emoji_Presentation}\uFE0F\uFE0E\u200D\u20E3\U000E0020-\U000E007F]")
_EMOTICONS = re.compile(
    r"(?<!\w)(?:[<>]?[=:;8xX][\-^'oO]?[)(/\\DPpOo*|]+|[)(][\-^']?[=:;]|"
    r"[xX][dD]|[Tt][_.-][Tt]|[oO][_.-][oO]|[-=][_.][-=]|>_<|"
    r"\^[_ .oOuU-]?\^|<+/?3+)(?!\w)"
)
_KAOMOJI = re.compile(
    r"¯\\_\(ツ\)_/¯|"
    r"[（(](?=[^()\n]{1,24}[)）])(?=[^()\n]*[°ಠಥ◕•])"
    r"[^()\nA-Za-z0-9]{1,24}[)）][╯づっノつ]*"
)


def strip_prohibited(text: str) -> str:
    text = _CUSTOM.sub("", text)
    text = emoji.replace_emoji(text, replace="")
    text = _SYMBOLS.sub("", text)
    text = _EMOTICONS.sub("", text)
    text = _KAOMOJI.sub("", text)
    text = text.replace("\u2014", ", ")
    text = "".join(char for char in text if char in "\n\t" or (
        not unicodedata.category(char).startswith("C") and unicodedata.category(char) != "So"))
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def validate_output(text, moderator, max_length=1800) -> str | None:
    """None means reject. Callers may retry once or validate a fixed fallback."""
    if not isinstance(text, str) or not text.strip() or len(text) > 100000:
        return None
    if moderator.blocked(text):
        return None
    text = strip_prohibited(text)
    if not text or identity_violation(text) or moderator.blocked(text):
        return None
    # Discord's 2000-character bound is conservatively measured in UTF-16 units.
    text = text.encode("utf-16-le")[:max_length * 2].decode("utf-16-le", errors="ignore").rstrip()
    if not text or moderator.blocked(text) or identity_violation(text):
        return None
    return text
