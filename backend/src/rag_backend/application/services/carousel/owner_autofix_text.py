"""Pure text repairs for the owner "Fix issues" button (AE-0367).

- ``balance_strong``: rebuild ``<strong>`` emphasis from the bare
  ``strong ... /strong`` residue a tag-stripping sanitizer leaves behind, drop
  every other tag (keeping its text), drop stray or nested tags and close an
  unclosed one, so ``emphasis_markup_is_valid`` accepts the result.
- ``restore_proper_nouns``: put back the capitals of known proper nouns where
  the copy has them fully lowercase ("argon" -> "Argon"). Mixed or upper case
  is left alone, so a deliberate "ARGON" is never rewritten.
- ``looks_portuguese`` / ``is_untranslated``: detect EN copy that is still the
  PT copy, or still Portuguese.

No I/O and idempotent.
"""

from __future__ import annotations

import re

from rag_backend.domain.constants.carousel_autofix import (
    ENGLISH_MARKERS,
    PORTUGUESE_ACCENTS,
    PORTUGUESE_MARKERS,
    PORTUGUESE_MIN_MARKERS,
    PORTUGUESE_MIN_WORDS_WITH_ACCENT,
    UNTRANSLATED_MIN_CHARS,
)

_STRONG = "strong"
_OPEN = "<strong>"
_CLOSE = "</strong>"
_TAG_PATTERN = re.compile(r"<\s*(/?)\s*([A-Za-z][A-Za-z0-9]*)[^>]*>")
# "strongindirect prompt injections/strong" (the "<" and ">" were stripped).
_MANGLED_PATTERN = re.compile(
    r"(?<![<\w/])strong\s?(?=\S)(.+?)\s?/strong(?![\w>])",
    flags=re.IGNORECASE,
)
_WORD_PATTERN = re.compile(r"[^\W\d_]+")
_WHITESPACE_PATTERN = re.compile(r"\s+")


def _demangle(text: str) -> str:
    return _MANGLED_PATTERN.sub(lambda match: f"{_OPEN}{match.group(1)}{_CLOSE}", text)


def _kept_tag(depth: int, *, closing: bool) -> str:
    """The normalized tag to keep at this depth, or "" to drop it."""
    if closing and depth == 1:
        return _CLOSE
    if not closing and depth == 0:
        return _OPEN
    return ""


def balance_strong(text: str) -> str:
    """Return the text with balanced, non-nested ``<strong>`` emphasis only."""
    source = _demangle(text)
    parts: list[str] = []
    depth = 0
    cursor = 0
    for match in _TAG_PATTERN.finditer(source):
        parts.append(source[cursor : match.start()])
        cursor = match.end()
        if match.group(2).lower() != _STRONG:
            continue
        tag = _kept_tag(depth, closing=match.group(1) == "/")
        if tag:
            parts.append(tag)
            depth = 1 - depth
    parts.append(source[cursor:])
    if depth == 1:
        parts.append(_CLOSE)
    return "".join(parts)


def _noun_pattern(noun: str) -> re.Pattern[str]:
    return re.compile(rf"(?<!\w){re.escape(noun)}(?!\w)", flags=re.IGNORECASE)


def restore_proper_nouns(text: str, nouns: tuple[str, ...]) -> str:
    """Restore the canonical capitals of nouns written fully lowercase."""
    result = text
    for noun in nouns:

        def _swap(match: re.Match[str], canonical: str = noun) -> str:
            found = match.group(0)
            return canonical if found == found.lower() else found

        result = _noun_pattern(noun).sub(_swap, result)
    return result


def lowercase_nouns(text: str, nouns: tuple[str, ...]) -> tuple[str, ...]:
    """The nouns the text writes fully lowercase (what the restore would fix)."""
    found: list[str] = []
    for noun in nouns:
        if noun == noun.lower():
            continue
        for match in _noun_pattern(noun).finditer(text):
            if match.group(0) == match.group(0).lower():
                found.append(match.group(0))
                break
    return tuple(found)


def _plain(text: str) -> str:
    stripped = _TAG_PATTERN.sub("", text)
    return _WHITESPACE_PATTERN.sub(" ", stripped).strip()


def looks_portuguese(text: str) -> bool:
    """True when the text reads as Portuguese rather than English."""
    plain = _plain(text).casefold()
    words = _WORD_PATTERN.findall(plain)
    portuguese = sum(1 for word in words if word in PORTUGUESE_MARKERS)
    english = sum(1 for word in words if word in ENGLISH_MARKERS)
    if portuguese >= PORTUGUESE_MIN_MARKERS and portuguese > english:
        return True
    accented = any(char in PORTUGUESE_ACCENTS for char in plain)
    return (
        portuguese >= 1
        and english == 0
        and accented
        and len(words) >= PORTUGUESE_MIN_WORDS_WITH_ACCENT
    )


def is_untranslated(english: str, portuguese: str) -> bool:
    """True when EN copy is the PT copy pasted as-is, or is still Portuguese."""
    plain_en = _plain(english)
    if not plain_en:
        return False
    same = plain_en.casefold() == _plain(portuguese).casefold()
    if same and len(plain_en) >= UNTRANSLATED_MIN_CHARS:
        return True
    return looks_portuguese(plain_en)


__all__ = [
    "balance_strong",
    "is_untranslated",
    "looks_portuguese",
    "lowercase_nouns",
    "restore_proper_nouns",
]
