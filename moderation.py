"""Bounded keyword moderation with Unicode and common evasion normalization.

Default prohibited tokens are code points so examples, errors, and logs never
display them. This is not encryption or a complete semantic hate classifier.
"""
import re
import unicodedata

_BUILTIN = (
    (110, 105, 103, 103, 101, 114), (110, 105, 103, 103, 97),
    (99, 104, 105, 110, 107), (115, 112, 105, 99),
    (107, 105, 107, 101), (103, 111, 111, 107),
)
_SUBSTITUTIONS = str.maketrans({"0": "o", "1": "i", "3": "e", "4": "a",
                              "5": "s", "7": "t", "@": "a", "$": "s"})


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).casefold().translate(_SUBSTITUTIONS)
    return "".join(char for char in text if unicodedata.category(char) not in ("Mn", "Me", "Cf"))


class Moderator:
    def __init__(self, extra_terms=(), use_builtin=True):
        terms = list(extra_terms)
        if use_builtin:
            terms += ["".join(map(chr, points)) for points in _BUILTIN]
        patterns = []
        for term in terms:
            normalized = "".join(char for char in normalize(term) if char.isalnum())
            if not normalized:
                raise ValueError("A moderation term must contain letters or digits.")
            # Unicode boundaries avoid matching a prohibited word inside normal words.
            body = r"[\W_]*".join(re.escape(char) for char in normalized)
            patterns.append(r"(?<!\w)" + body + r"(?:s)?(?!\w)")
        self.pattern = re.compile("|".join(patterns)) if patterns else None

    def blocked(self, text: str) -> bool:
        return bool(self.pattern and self.pattern.search(normalize(text)))
