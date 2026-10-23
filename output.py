"""One final validation gate used by every Discord send."""
import re
import unicodedata
import emoji
from langdetect import DetectorFactory, LangDetectException, detect_langs
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
_SENTENCE_END = re.compile(r"[.!?](?:[\"')\]]{0,3})(?=\s|$)")
_CODE = re.compile(r"```.*?```|`[^`\n]*`", re.DOTALL)
_URL = re.compile(r"https?://\S+")
_ENGLISH_WORDS = {
    "a", "about", "again", "ai", "an", "answer", "are", "bot", "can",
    "can't", "channel's", "clear", "cleared", "complete", "connection",
    "context", "could", "created", "do", "don't", "english", "from",
    "goodbye", "have", "hello", "help", "hi", "i", "i'm", "i've", "in",
    "information", "is", "it", "later", "like", "long", "makes", "me",
    "mention", "message", "messages", "my", "needs", "neutral", "no", "not",
    "of", "okay", "one", "operator", "or", "orion", "output", "personal",
    "please", "quota", "repeat", "reply", "requested", "reset", "response",
    "rontgen", "say", "send", "sentence", "sense", "service", "settings",
    "shorter", "sure", "talk", "temporarily", "thank", "thanks", "that",
    "the", "there", "this", "to", "too", "try", "unavailable", "use",
    "version", "welcome", "what", "with", "won't", "would", "yes", "you",
    "your",
}

DetectorFactory.seed = 0


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


def _limit_at_sentence(text: str, max_length: int) -> str:
    """Fit UTF-16 limit, preferring a complete sentence over a partial one."""
    encoded = text.encode("utf-16-le")
    if len(encoded) <= max_length * 2:
        return text
    clipped = encoded[:max_length * 2].decode("utf-16-le", errors="ignore").rstrip()
    endings = list(_SENTENCE_END.finditer(clipped))
    if endings:
        return clipped[:endings[-1].end()].rstrip()
    # If the model produced no complete sentence, visibly mark the hard limit
    # instead of presenting a cut-off fragment as a finished response.
    room = max(1, max_length - 3)
    clipped = encoded[:room * 2].decode("utf-16-le", errors="ignore").rstrip()
    if " " in clipped:
        clipped = clipped.rsplit(None, 1)[0]
    return clipped.rstrip(" ,;:") + "..."


def finish_limited_output(text: str) -> str:
    """Remove the unfinished tail reported by a provider token limit."""
    text = text.rstrip()
    endings = list(_SENTENCE_END.finditer(text))
    if endings:
        return text[:endings[-1].end()].rstrip()
    return text.rstrip(" ,;:") + "..."


def english_only(text: str) -> bool:
    """Require English prose while allowing URLs, code, numbers, and punctuation."""
    prose = _URL.sub(" ", _CODE.sub(" ", text))
    for chunk in re.split(r"(?<=[.!?])\s+|\n+", prose):
        words = regex.findall(r"\p{L}+(?:['’]\p{L}+)*", chunk)
        if not words:
            continue
        normalized = [word.casefold().replace("’", "'") for word in words]
        if all(word in _ENGLISH_WORDS for word in normalized):
            continue
        try:
            english_confidence = next(
                (score.prob for score in detect_langs(chunk) if score.lang == "en"), 0.0)
        except LangDetectException:
            return False
        if english_confidence < 0.80:
            return False
    return True


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
    text = _limit_at_sentence(text, max_length)
    if (not text or not english_only(text) or moderator.blocked(text)
            or identity_violation(text)):
        return None
    return text
