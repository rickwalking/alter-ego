"""Locale-safe sentence-case detection and repair for visible slide copy.

Pure text helpers shared by the presentation casing rules and the deterministic
repair. A text "starts lowercase" when its first significant character (after
whitespace, HTML tags, markdown emphasis, quotes and other punctuation) is a
lowercase letter. A leading digit is acceptable sentence case ("5 dicas ...").
Text that opens with an intentionally lowercase token from the policy allowlist
(``iPhone``, ``eBay``, ``macOS``) is never flagged nor rewritten.

The repair only ever uppercases that first letter. It never guesses proper
nouns: restoring "argon" to "Argon" is left to regeneration.

A text whose first significant word is an ``@handle`` or a URL
(``http://``, ``https://``, ``www.``) keeps its case: it is the source's, so
``@taylorhbuilds`` never becomes ``@Taylorhbuilds``.

A sentence boundary is end punctuation (including a trailing "..." run) followed by
whitespace.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

_HTML_TAG_PATTERN = re.compile(r"<[^>]+>")
_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+")
_HANDLE_MARK = "@"
_URL_START = re.compile(r"(?:https?://|www\.)", flags=re.IGNORECASE)


def _first_significant_index(text: str, start: int) -> int | None:
    """Index of the first letter or digit at/after ``start``, skipping markup."""
    index = start
    length = len(text)
    while index < length:
        tag = _HTML_TAG_PATTERN.match(text, index)
        if tag is not None:
            index = tag.end()
            continue
        if text[index].isalnum():
            return index
        index += 1
    return None


def _allowlisted_at(text: str, index: int, allowlist: Iterable[str]) -> bool:
    """True when an allowlisted token starts at ``index`` as a whole word."""
    for token in allowlist:
        if not token or not text.startswith(token, index):
            continue
        end = index + len(token)
        if end >= len(text) or not text[end].isalnum():
            return True
    return False


def _handle_or_url_at(text: str, index: int) -> bool:
    """True when an ``@handle`` or a URL starts at ``index``."""
    after_mark = index > 0 and text[index - 1] == _HANDLE_MARK
    return after_mark or _URL_START.match(text, index) is not None


def _lowercase_letter_at(
    text: str, index: int | None, allowlist: Iterable[str]
) -> bool:
    if index is None:
        return False
    char = text[index]
    if not char.isalpha() or not char.islower():
        return False
    if _handle_or_url_at(text, index):
        return False
    return not _allowlisted_at(text, index, allowlist)


def starts_lowercase(text: str, allowlist: Iterable[str] = ()) -> bool:
    """Return True when the text's first significant letter is lowercase."""
    return _lowercase_letter_at(text, _first_significant_index(text, 0), allowlist)


def has_lowercase_sentence(text: str, allowlist: Iterable[str] = ()) -> bool:
    """Return True when any sentence in the text starts lowercase."""
    return any(
        starts_lowercase(sentence, allowlist)
        for sentence in _SENTENCE_BOUNDARY.split(text)
    )


def _upper_char(char: str) -> str:
    """Uppercase one character, keeping it when the mapping is not 1:1 (ß)."""
    upper = char.upper()
    return upper if len(upper) == 1 else char


def capitalize_at(text: str, start: int, allowlist: Iterable[str] = ()) -> str:
    """Uppercase the first significant letter at/after ``start`` when lowercase.

    Markup, quotes and punctuation are skipped and left untouched; a leading
    digit or an allowlisted token stops the repair. Idempotent.
    """
    index = _first_significant_index(text, start)
    if index is None or not _lowercase_letter_at(text, index, allowlist):
        return text
    return text[:index] + _upper_char(text[index]) + text[index + 1 :]


def capitalize_first_letter(text: str, allowlist: Iterable[str] = ()) -> str:
    """Uppercase the first letter of a heading-like text when lowercase."""
    return capitalize_at(text, 0, allowlist)


def capitalize_sentence_starts(text: str, allowlist: Iterable[str] = ()) -> str:
    """Uppercase the first letter of every sentence, preserving markup.

    Each swap replaces one character with one character, so the boundary offsets stay
    valid.
    """
    if not text:
        return text
    starts = [0, *[match.end() for match in _SENTENCE_BOUNDARY.finditer(text)]]
    result = text
    for start in starts:
        result = capitalize_at(result, start, allowlist)
    return result


__all__ = [
    "capitalize_at",
    "capitalize_first_letter",
    "capitalize_sentence_starts",
    "has_lowercase_sentence",
    "starts_lowercase",
]
