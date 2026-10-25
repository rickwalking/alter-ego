"""Copy-hygiene validators for one locale payload.

Each rule is active only when the loaded policy declares a severity for its
code (``pov_hook_v1`` and ``hero_lower_third_v4``), so older contracts keep
their semantics. They run on PT and EN, on the heading, the body and every
structured item (features, summary points, actions):

- ``structured_payload_in_copy``: JSON/dict text, code fences, leaked keys.
- ``markup_leak``: HTML tags other than ``<strong>``, Markdown headings/
  lists/tables, backticks, literal ``\\n`` / ``\\"``. The pipeline's emphasis
  (``**bold**`` in PT, balanced ``<strong>`` in EN) is never a leak.
- ``emphasis_unbalanced``: odd ``**`` count, empty ``****``.
- ``assistant_chatter``: "Here is", "Assistant:", "Claro! Aqui está o texto".
- ``placeholder_text``: ``[insert…]``, ``{topic}``, to-do markers, lorem ipsum, stubs.
- ``encoding_garbled``: mojibake, U+FFFD, control characters.
- ``copy_truncated``: the slide body stops mid-sentence, or a checklist item body is
  clearly cut off (an open ending, a dangling connector, or an unfinished last sentence).
- ``body_too_short``: a content slide body under 8 words (body only).
- ``wrong_language``: PT copy that reads as English, EN copy as Portuguese.
- ``repeated_text``: a sentence twice in one slide, or a doubled word.
- ``structured_item_split``: an item title that ends on a connector word
  ("Comece com dois ou"), its rest pushed into the item body.

The emphasis convention is PT ``**...**`` and EN ``<strong>...</strong>``; it is
locale-aware, so it is checked separately from the rules run on every visible field
(heading, body, item title and body).
"""

from __future__ import annotations

from collections.abc import Callable

from rag_backend.application.services.carousel.copy_hygiene_text import (
    assistant_chatter_detail,
    doubled_word_detail,
    emphasis_locale_detail,
    emphasis_unbalanced_detail,
    encoding_detail,
    item_split_detail,
    item_truncation_detail,
    markup_leak_detail,
    placeholder_detail,
    sentence_keys,
    structured_payload_detail,
    truncation_detail,
    word_count,
    wrong_language_detail,
)
from rag_backend.application.services.carousel.presentation_content_rules import (
    ContentRuleCommand,
    complete_item_count,
    language_fields,
    rule_active,
    slide_type_of,
    text_of,
    visible_fields,
)
from rag_backend.domain.constants.carousel import LANGUAGE_PT, SLIDE_TYPE_CONTENT
from rag_backend.domain.constants.carousel_presentation import (
    MIN_CONTENT_BODY_WORDS,
    MIN_CONTENT_FEATURES_WITHOUT_BODY,
    VIOLATION_ASSISTANT_CHATTER,
    VIOLATION_BODY_TOO_SHORT,
    VIOLATION_COPY_TRUNCATED,
    VIOLATION_EMPHASIS_MARKUP_LOCALE_MISMATCH,
    VIOLATION_EMPHASIS_UNBALANCED,
    VIOLATION_ENCODING_GARBLED,
    VIOLATION_MARKUP_LEAK,
    VIOLATION_PLACEHOLDER_TEXT,
    VIOLATION_REPEATED_TEXT,
    VIOLATION_STRUCTURED_ITEM_SPLIT,
    VIOLATION_STRUCTURED_PAYLOAD_IN_COPY,
    VIOLATION_WRONG_LANGUAGE,
)
from rag_backend.domain.models.carousel_presentation import (
    SlideValidationViolation,
    ViolationSeverity,
)

_FIELD_HEADING = "heading"
_FIELD_BODY = "body"
_KEY_FEATURES = "features"
_DETAIL_SEPARATOR = ": "
_ITEM_TITLE_SUFFIX = "].title"
_ITEM_BODY_SUFFIX = "].body"

_MESSAGES: dict[str, str] = {
    VIOLATION_STRUCTURED_PAYLOAD_IN_COPY: (
        "Visible copy contains JSON, a code fence or a raw copy key"
    ),
    VIOLATION_MARKUP_LEAK: (
        "Visible copy contains markup (an HTML tag other than <strong>, a "
        "Markdown heading/list/table, backticks or escapes)"
    ),
    VIOLATION_EMPHASIS_UNBALANCED: "Bold emphasis ** is unbalanced or empty",
    VIOLATION_EMPHASIS_MARKUP_LOCALE_MISMATCH: (
        "Emphasis uses the other locale's markup (PT: **…**, EN: <strong>…</strong>)"
    ),
    VIOLATION_ASSISTANT_CHATTER: (
        "Visible copy contains assistant chatter or a note about the task"
    ),
    VIOLATION_PLACEHOLDER_TEXT: "Visible copy contains a placeholder or a stub",
    VIOLATION_ENCODING_GARBLED: "Visible copy has garbled encoding",
    VIOLATION_COPY_TRUNCATED: "Body copy stops mid-sentence",
    VIOLATION_BODY_TOO_SHORT: (
        f"Content slide body needs at least {MIN_CONTENT_BODY_WORDS} words"
    ),
    VIOLATION_WRONG_LANGUAGE: "Copy is written in the wrong language",
    VIOLATION_REPEATED_TEXT: "Slide repeats a sentence or a word",
    VIOLATION_STRUCTURED_ITEM_SPLIT: (
        "An item title is cut mid-phrase (its rest is in the item body)"
    ),
}

_FieldCheck = Callable[[str], str]

_EVERY_FIELD: tuple[tuple[str, _FieldCheck], ...] = (
    (VIOLATION_STRUCTURED_PAYLOAD_IN_COPY, structured_payload_detail),
    (VIOLATION_MARKUP_LEAK, markup_leak_detail),
    (VIOLATION_EMPHASIS_UNBALANCED, emphasis_unbalanced_detail),
    (VIOLATION_ASSISTANT_CHATTER, assistant_chatter_detail),
    (VIOLATION_PLACEHOLDER_TEXT, placeholder_detail),
    (VIOLATION_ENCODING_GARBLED, encoding_detail),
    (VIOLATION_REPEATED_TEXT, doubled_word_detail),
)


def _violation(
    command: ContentRuleCommand, code: str, place: tuple[str, str]
) -> SlideValidationViolation:
    field, detail = place
    severity: ViolationSeverity = (
        "warning" if command.policy.is_casing_warning(code) else "blocker"
    )
    message = _MESSAGES[code] + (_DETAIL_SEPARATOR + detail if detail else "")
    return SlideValidationViolation(
        code=code,
        message=message,
        slide_index=command.slide_index,
        locale=command.locale,
        field=field,
        severity=severity,
    )


def _field_codes(
    fields: list[tuple[str, str]], active: frozenset[str]
) -> list[tuple[str, tuple[str, str]]]:
    found: list[tuple[str, tuple[str, str]]] = []
    for code, check in _EVERY_FIELD:
        if code not in active:
            continue
        for field, text in fields:
            detail = check(text) if text else ""
            if detail:
                found.append((code, (field, detail)))
    return found


def _repeated_sentence(fields: list[tuple[str, str]]) -> tuple[str, str] | None:
    seen: set[str] = set()
    for field, text in fields:
        if field == _FIELD_HEADING:
            continue
        for key in sentence_keys(text):
            if key in seen:
                return field, f'sentence "{key}" appears twice'
            seen.add(key)
    return None


def _body_too_short(command: ContentRuleCommand, slide_type: str) -> str:
    body = text_of(command.payload, _FIELD_BODY)
    if slide_type != SLIDE_TYPE_CONTENT or not body.strip():
        return ""
    features = complete_item_count(command.payload, _KEY_FEATURES)
    count = word_count(body)
    if count >= MIN_CONTENT_BODY_WORDS or features >= MIN_CONTENT_FEATURES_WITHOUT_BODY:
        return ""
    return f"{count} words"


def _body_codes(
    command: ContentRuleCommand, slide_type: str, active: frozenset[str]
) -> list[tuple[str, tuple[str, str]]]:
    body = text_of(command.payload, _FIELD_BODY)
    portuguese = command.locale == LANGUAGE_PT
    details = {
        VIOLATION_COPY_TRUNCATED: lambda: truncation_detail(body),
        VIOLATION_BODY_TOO_SHORT: lambda: _body_too_short(command, slide_type),
    }
    found = [
        (code, (_FIELD_BODY, detail))
        for code, detail_of in details.items()
        if code in active and (detail := detail_of())
    ]
    if VIOLATION_COPY_TRUNCATED in active:
        found.extend(
            (VIOLATION_COPY_TRUNCATED, (field, detail))
            for field, text in visible_fields(command.payload)
            if field.endswith(_ITEM_BODY_SUFFIX)
            and (detail := item_truncation_detail(text))
        )
    if VIOLATION_WRONG_LANGUAGE in active:
        found.extend(
            (VIOLATION_WRONG_LANGUAGE, (field, detail))
            for field, text in language_fields(command.payload)
            if (detail := wrong_language_detail(text, portuguese=portuguese))
        )
    return found


def copy_hygiene_violations(
    command: ContentRuleCommand,
) -> list[SlideValidationViolation]:
    """Copy-hygiene violations of one locale payload (v4/POV)."""
    slide_type = slide_type_of(command.payload)
    active = frozenset(
        code for code in _MESSAGES if rule_active(command.policy, code, slide_type)
    )
    if not active:
        return []
    fields = visible_fields(command.payload)
    found = _field_codes(fields, active)
    if VIOLATION_EMPHASIS_MARKUP_LOCALE_MISMATCH in active:
        portuguese = command.locale == LANGUAGE_PT
        found.extend(
            (VIOLATION_EMPHASIS_MARKUP_LOCALE_MISMATCH, (field, detail))
            for field, text in fields
            if (detail := emphasis_locale_detail(text, portuguese=portuguese))
        )
    if VIOLATION_STRUCTURED_ITEM_SPLIT in active:
        found.extend(
            (VIOLATION_STRUCTURED_ITEM_SPLIT, (field, detail))
            for field, text in fields
            if field.endswith(_ITEM_TITLE_SUFFIX)
            and (detail := item_split_detail(text))
        )
    found.extend(_body_codes(command, slide_type, active))
    repeated = _repeated_sentence(fields) if VIOLATION_REPEATED_TEXT in active else None
    if repeated is not None:
        found.append((VIOLATION_REPEATED_TEXT, repeated))
    return [_violation(command, code, place) for code, place in found]


__all__ = ["copy_hygiene_violations"]
