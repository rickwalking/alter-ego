"""Excerpt matching for scout quotes (spec §4). Pure, no I/O.

Both the excerpt and the stored post text are normalised the same way, then
compared as a case-sensitive substring:

- Unicode NFC;
- curly quotes and apostrophes become straight ones;
- every whitespace run (line breaks included) becomes one space; ends trimmed.

Nothing else changes: case, punctuation, emoji and ellipses must match.
"""

from __future__ import annotations

import re
import unicodedata

from rag_backend.modules.autopilot.domain.topic_text import strip_controls
from rag_backend.modules.autopilot.quote_constants import (
    CURLY_QUOTE_TABLE,
    SINGLE_SPACE,
    STORED_POST_TEXT_MAX_CHARS,
    UNICODE_NFC,
    WHITESPACE_RUN_PATTERN,
)

_WHITESPACE_RUN = re.compile(WHITESPACE_RUN_PATTERN)


def spaced(value: str) -> str:
    """Every whitespace run (CR, LF, tabs included) as one space."""
    return _WHITESPACE_RUN.sub(SINGLE_SPACE, value)


def normalize_quote_text(value: str) -> str:
    """The comparable form of an excerpt or a post text."""
    composed = unicodedata.normalize(UNICODE_NFC, value)
    straight = composed.translate(CURLY_QUOTE_TABLE)
    return strip_controls(spaced(straight))


def excerpt_in_post(excerpt: str, post_text: str) -> bool:
    """True when ``excerpt`` is one continuous piece of the stored post text.

    The stored text is at most 600 characters, so the comparison never looks
    past that cut even if a longer text reaches this function.
    """
    needle = normalize_quote_text(excerpt)
    if not needle:
        return False
    haystack = normalize_quote_text(post_text[:STORED_POST_TEXT_MAX_CHARS])
    return needle in haystack


def word_count(value: str) -> int:
    """Whitespace-separated words."""
    return len(value.split())


__all__ = ["excerpt_in_post", "normalize_quote_text", "spaced", "word_count"]
