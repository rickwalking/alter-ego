"""Fenced JSON slide drafts.

Gherkin: tests/features/fenced_draft_blob_ae0400.feature
"""

from __future__ import annotations

import json

import pytest

from rag_backend.application.services.carousel.draft_blob_text import (
    looks_like_object,
    parse_object_text,
    strip_code_fence,
)
from rag_backend.application.services.carousel.malformed_draft_normalizer import (
    normalize_slide_draft,
    parse_bilingual_draft_blob,
)
from rag_backend.application.services.carousel.visible_copy_sanitize import (
    resolve_localized_string,
)

pytestmark = pytest.mark.unit

PT_BODY = (
    "Não quero um chat que tenta responder tudo. Quero agentes com escopo fechado."
)
EN_BODY = "I don't want a chat that tries to answer everything. I want bounded agents."
BLOB = {
    "pt": {"heading": "Escopo e aprovação final", "body": PT_BODY},
    "en": {"heading": "Scope and final approval", "body": EN_BODY},
}
FENCED = "```json\n" + json.dumps(BLOB, ensure_ascii=False, indent=2) + "\n```"


def _field(slide: dict[str, object], presentation: str, key: str) -> object:
    value = slide.get(presentation)
    assert isinstance(value, dict)
    return value.get(key)


# Scenario: A ```json fenced bilingual draft is normalized
def test_fenced_draft_is_normalized() -> None:
    slide = {"slide_index": 3, "slide_type": "content", "draft_text": FENCED}
    result = normalize_slide_draft(slide)
    assert result["draft_text"] == PT_BODY
    assert _field(result, "presentation_pt", "heading") == "Escopo e aprovação final"
    assert _field(result, "presentation_en", "body") == EN_BODY
    assert "```" not in json.dumps(result, ensure_ascii=False)


# Scenario: A plain fence without a language tag is read too
def test_plain_fence_is_read() -> None:
    raw = "```\n" + json.dumps(BLOB) + "\n```"
    assert parse_bilingual_draft_blob(raw) == BLOB


# Scenario: JSON literals that Python cannot read are parsed as JSON
def test_json_literals_are_parsed() -> None:
    raw = '```json\n{"pt": {"body": "x", "ok": true, "none": null, "no": false}}\n```'
    assert parse_object_text(raw) == {
        "pt": {"body": "x", "ok": True, "none": None, "no": False}
    }


def test_python_literal_still_parses() -> None:
    assert parse_object_text("{'pt': {'body': 'x'}}") == {"pt": {"body": "x"}}


# Scenario: Plain copy is left alone
def test_plain_copy_is_unchanged() -> None:
    slide = {"slide_index": 2, "draft_text": "Chatbot único vira **gargalo**"}
    assert normalize_slide_draft(slide) == slide
    assert looks_like_object(slide["draft_text"]) is False


# Scenario: A broken fenced object is not guessed
def test_broken_fenced_object_returns_none() -> None:
    raw = '```json\n{"pt": {"body": \n```'
    assert parse_object_text(raw) is None
    slide = {"slide_index": 3, "draft_text": raw}
    assert normalize_slide_draft(slide) == slide


def test_non_object_and_unfenced_text() -> None:
    assert parse_object_text("```json\n[1, 2]\n```") is None
    assert parse_object_text("hello") is None
    assert strip_code_fence("  plain  ") == "plain"


# Scenario: A stringified fenced locale blob resolves to one locale
def test_fenced_locale_strings_resolve() -> None:
    raw = '```json\n{"pt": "Olá", "en": "Hello"}\n```'
    assert resolve_localized_string(raw, locale="en") == "Hello"
