"""Deterministic repair for the AE-0401 copy-hygiene rules.

Only what is safe to fix without a model, and only when the policy declares
the rule (so older contracts are untouched):

- a heading/body that is a (fenced) bilingual JSON object becomes that
  locale's heading and body; a fence around plain copy is removed;
- ``<b>`` becomes ``<strong>``; other HTML tags (never ``<strong>``, the EN
  emphasis) are dropped, their text kept; a leading Markdown ``#`` is
  dropped (the whole line when it repeats the slide heading); backticks are
  removed and literal ``\\n`` / ``\\"`` are unescaped;
- an empty ``****`` is dropped and an odd trailing ``**`` removed;
- control characters are removed and cp1252 mojibake is decoded back;
- a doubled word ("o o", "the the") is collapsed;
- in EN, a word capitalized right after a mid-sentence colon is lowercased
  (proper nouns, "I" and acronyms kept).

Lists, chatter, placeholders, truncation and the wrong language are left to
the model fix. Idempotent; no I/O.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping

from rag_backend.application.services.carousel.copy_hygiene_text import (
    BACKTICK,
    BOLD_MARK,
    CODE_FENCE,
    CONTROL_CHAR_PATTERN,
    DOUBLED_WORD_ALLOWLIST,
    DOUBLED_WORD_PATTERN,
    EMPHASIS_TAG_PATTERN,
    EMPTY_BOLD,
    HTML_TAG_PATTERN,
    MARKDOWN_HEADING_PATTERN,
    MOJIBAKE_PATTERN,
)
from rag_backend.application.services.carousel.draft_blob_text import (
    parse_object_text,
    strip_code_fence,
)
from rag_backend.application.services.carousel.owner_autofix_paths import (
    ITEM_LISTS,
    map_texts,
)
from rag_backend.application.services.carousel.presentation_content_rules import (
    rule_active,
    slide_type_of,
)
from rag_backend.application.services.carousel.presentation_policy_types import (
    CarouselPresentationPolicy,
)
from rag_backend.domain.constants.carousel import LANGUAGE_EN
from rag_backend.domain.constants.carousel_autofix import KNOWN_PROPER_NOUNS
from rag_backend.domain.constants.carousel_presentation import (
    VIOLATION_EMPHASIS_UNBALANCED,
    VIOLATION_ENCODING_GARBLED,
    VIOLATION_MARKUP_LEAK,
    VIOLATION_REPEATED_TEXT,
    VIOLATION_STRUCTURED_PAYLOAD_IN_COPY,
)

_HEADING = "heading"
_BODY = "body"
_DRAFT_TEXT = "draft_text"
_TITLE = "title"
_ICON_NAME = "icon_name"
_LOCALE_PREFIX = "presentation_"
_B_TAG_PATTERN = re.compile(r"<\s*(/?)\s*b\s*>", flags=re.IGNORECASE)
_BREAK_TAG_PATTERN = re.compile(r"<\s*br\s*/?\s*>", flags=re.IGNORECASE)
_SPACES_PATTERN = re.compile(r"[ \t]{2,}")
# A capitalized word right after "word: " (not at a line start).
_COLON_WORD_PATTERN = re.compile(
    r"(\w[*]{0,2}:[ \t]+(?:\*\*|<strong>)?)([A-Z][\w'\u2019]*)"
)
_COLON_KEEP: tuple[str, ...] = ("I", "I'm", "I've", "I'd", "I'll")
_LITERAL_UNESCAPES: tuple[tuple[str, str], ...] = (
    ("\\n", " "),
    ("\\t", " "),
    ('\\"', '"'),
)
_MOJIBAKE_CODEC = "cp1252"
_UTF8 = "utf-8"


def _tidy(text: str) -> str:
    lines = [_SPACES_PATTERN.sub(" ", line).strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def _keep_strong(match: re.Match[str]) -> str:
    tag = match.group(0)
    return tag if EMPHASIS_TAG_PATTERN.fullmatch(tag) else ""


def repair_markup(text: str) -> str:
    """``<b>`` to ``<strong>``, other tags and leading ``#`` dropped, escapes undone.

    ``<strong>`` and ``**bold**`` are the pipeline's emphasis and are kept.
    """
    repaired = _B_TAG_PATTERN.sub(lambda match: f"<{match.group(1)}strong>", text)
    repaired = _BREAK_TAG_PATTERN.sub(" ", repaired)
    repaired = HTML_TAG_PATTERN.sub(_keep_strong, repaired)
    repaired = MARKDOWN_HEADING_PATTERN.sub("", repaired)
    repaired = repaired.replace(BACKTICK, "")
    for literal, plain in _LITERAL_UNESCAPES:
        repaired = repaired.replace(literal, plain)
    return _tidy(repaired) if repaired != text else text


def repair_emphasis(text: str) -> str:
    """Drop empty ``****`` and an unpaired last ``**``."""
    repaired = text.replace(EMPTY_BOLD, "")
    if repaired.count(BOLD_MARK) % 2 == 1:
        cut = repaired.rfind(BOLD_MARK)
        repaired = repaired[:cut] + repaired[cut + len(BOLD_MARK) :]
    return _tidy(repaired) if repaired != text else text


def _decode_mojibake(text: str) -> str:
    try:
        decoded = text.encode(_MOJIBAKE_CODEC).decode(_UTF8)
    except UnicodeError:
        return text
    return decoded if not MOJIBAKE_PATTERN.search(decoded) else text


def repair_encoding(text: str) -> str:
    """Remove control characters and decode cp1252 mojibake when it round-trips."""
    cleaned = CONTROL_CHAR_PATTERN.sub("", text)
    if MOJIBAKE_PATTERN.search(cleaned):
        cleaned = _decode_mojibake(cleaned)
    return cleaned


def repair_doubled_words(text: str) -> str:
    """Collapse a word written twice in a row (grammatical doubles kept)."""

    def _collapse(match: re.Match[str]) -> str:
        if match.group(1).casefold() in DOUBLED_WORD_ALLOWLIST:
            return match.group(0)
        return match.group(1)

    return DOUBLED_WORD_PATTERN.sub(_collapse, text)


def _blob_copy(payload: Mapping[str, object], locale: str) -> dict[str, object]:
    """Heading/body from a (fenced) object written into the heading or body."""
    for field in (_BODY, _HEADING):
        value = payload.get(field)
        parsed = parse_object_text(value) if isinstance(value, str) else None
        if parsed is None:
            continue
        nested = parsed.get(locale) or parsed.get(_LOCALE_PREFIX + locale)
        source = nested if isinstance(nested, Mapping) else parsed
        body = source.get(_BODY) or source.get(_DRAFT_TEXT)
        found = {_HEADING: source.get(_HEADING), _BODY: body}
        copy: dict[str, object] = {
            key: text
            for key, text in found.items()
            if isinstance(text, str) and text.strip()
        }
        copy.update(_blob_items(source, payload))
        return copy
    return {}


def _blob_item(item: object, current: object) -> dict[str, object] | None:
    if not isinstance(item, Mapping):
        return None
    title, body = item.get(_TITLE), item.get(_BODY)
    if not isinstance(title, str) or not isinstance(body, str) or not title.strip():
        return None
    base = dict(current) if isinstance(current, Mapping) else {}
    icon = item.get(_ICON_NAME) or base.get(_ICON_NAME)
    whole = {**base, _TITLE: title.strip(), _BODY: body.strip()}
    return {**whole, _ICON_NAME: icon} if isinstance(icon, str) and icon else whole


def _blob_items(
    source: Mapping[str, object], payload: Mapping[str, object]
) -> dict[str, object]:
    """Whole items (title AND body) of the blob's lists, never re-split (AE-0401).

    Prod slide 8: a fenced blob carried ``summary_points``; rebuilding them
    from a split string cut "Comece com dois ou três agentes" in two.
    """
    lists: dict[str, object] = {}
    for list_field in ITEM_LISTS:
        raw = source.get(list_field)
        if not isinstance(raw, list) or not raw:
            continue
        current = payload.get(list_field)
        old = current if isinstance(current, list) else []
        items = [
            _blob_item(item, old[index] if index < len(old) else None)
            for index, item in enumerate(raw)
        ]
        if all(item is not None for item in items):
            lists[list_field] = items
    return lists


def _unfence(text: str) -> str:
    inner = strip_code_fence(text)
    return inner if CODE_FENCE not in inner else text


def repair_structured_payload(
    payload: Mapping[str, object], locale: str
) -> dict[str, object]:
    """Read a JSON blob written as the copy; drop a fence around plain copy."""
    repaired = {**payload, **_blob_copy(payload, locale)}
    for field in (_HEADING, _BODY):
        value = repaired.get(field)
        if isinstance(value, str) and CODE_FENCE in value:
            repaired[field] = _unfence(value)
    return repaired


def drop_heading_line(payload: Mapping[str, object]) -> dict[str, object]:
    """Drop a Markdown heading line in the body that repeats the slide heading.

    Prod slide 8 started its body with "## Checklist para salvar", the slide's
    own heading: dropping only the "#" would leave the heading in the body.
    """
    body, heading = payload.get(_BODY), payload.get(_HEADING)
    if not isinstance(body, str) or not isinstance(heading, str) or not heading:
        return dict(payload)
    target = heading.strip().casefold()
    lines = [
        line
        for line in body.splitlines()
        if not (
            MARKDOWN_HEADING_PATTERN.match(line)
            and MARKDOWN_HEADING_PATTERN.sub("", line).strip().casefold() == target
        )
    ]
    if len(lines) == len(body.splitlines()):
        return dict(payload)
    return {**payload, _BODY: "\n".join(lines).strip()}


def _colon_word(match: re.Match[str], keep: frozenset[str]) -> str:
    word = match.group(2)
    if word in keep or word.isupper() or any(ch.isupper() for ch in word[1:]):
        return match.group(0)
    return match.group(1) + word[0].lower() + word[1:]


def repair_colon_case_en(text: str, proper_nouns: tuple[str, ...] = ()) -> str:
    """Lowercase the word after a mid-sentence colon in EN copy.

    Prod 2026-10-16: "I see the mistake: It responds", "decide: Pass or
    return". A proper noun, "I", an acronym or a camel-case brand keeps its
    capital.
    """
    keep = frozenset({*proper_nouns, *KNOWN_PROPER_NOUNS, *_COLON_KEEP})
    return _COLON_WORD_PATTERN.sub(lambda match: _colon_word(match, keep), text)


_TEXT_REPAIRS: tuple[tuple[str, Callable[[str], str]], ...] = (
    (VIOLATION_ENCODING_GARBLED, repair_encoding),
    (VIOLATION_MARKUP_LEAK, repair_markup),
    (VIOLATION_EMPHASIS_UNBALANCED, repair_emphasis),
    (VIOLATION_REPEATED_TEXT, repair_doubled_words),
)


def repair_copy_hygiene(
    payload: Mapping[str, object],
    locale: str,
    policy: CarouselPresentationPolicy,
) -> dict[str, object]:
    """Apply the safe copy-hygiene repairs the policy enables to one payload."""
    slide_type = slide_type_of(payload)
    repaired = dict(payload)
    if rule_active(policy, VIOLATION_STRUCTURED_PAYLOAD_IN_COPY, slide_type):
        repaired = repair_structured_payload(repaired, locale)
    if rule_active(policy, VIOLATION_MARKUP_LEAK, slide_type):
        repaired = drop_heading_line(repaired)
    for code, repair in _TEXT_REPAIRS:
        if rule_active(policy, code, slide_type):
            repaired = map_texts(repaired, repair)
    if locale == LANGUAGE_EN and rule_active(policy, VIOLATION_MARKUP_LEAK, slide_type):
        nouns = policy.proper_nouns
        repaired = map_texts(repaired, lambda text: repair_colon_case_en(text, nouns))
    return repaired


__all__ = [
    "drop_heading_line",
    "repair_colon_case_en",
    "repair_copy_hygiene",
    "repair_doubled_words",
    "repair_emphasis",
    "repair_encoding",
    "repair_markup",
    "repair_structured_payload",
]
