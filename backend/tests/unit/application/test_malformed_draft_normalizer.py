"""Tests for bilingual draft_text normalization."""

from __future__ import annotations

from rag_backend.application.services.carousel.malformed_draft_normalizer import (
    normalize_slide_draft,
    parse_bilingual_draft_blob,
)


def test_parse_bilingual_draft_blob_from_string() -> None:
    # Feature: Versioned carousel presentation contract
    # Scenario: Malformed draft_text is normalized into presentation payloads
    raw = (
        "{'pt': {'heading': 'Hook PT', 'subtitle': 'Body PT'}, "
        "'en': {'heading': 'Hook EN', 'subtitle': 'Body EN'}}"
    )
    parsed = parse_bilingual_draft_blob(raw)
    assert parsed is not None
    assert parsed["pt"]["heading"] == "Hook PT"


def test_normalize_slide_draft_builds_presentations_and_title() -> None:
    raw = (
        "{'pt': {'heading': 'Fable 5 e Mythos 5', 'subtitle': 'Subtitle PT'}, "
        "'en': {'heading': 'Fable 5 and Mythos 5', 'subtitle': 'Subtitle EN'}}"
    )
    slide = {
        "slide_index": 1,
        "slide_type": "intro",
        "tldr_strip": "TLDR PT",
        "draft_text": raw,
    }
    normalized = normalize_slide_draft(slide)

    assert normalized["title"] == "Fable 5 e Mythos 5"
    assert normalized["presentation_pt"]["heading"] == "Fable 5 e Mythos 5"
    assert normalized["presentation_pt"]["body"] == "Subtitle PT"
    assert normalized["presentation_en"]["heading"] == "Fable 5 and Mythos 5"
    assert normalized["draft_text"] == "Subtitle PT"
    assert normalized["presentation_en"]["tldr_strip"]


def test_normalize_slide_draft_keeps_valid_presentations() -> None:
    slide = {
        "slide_index": 2,
        "slide_type": "summary",
        "draft_text": "legacy",
        "presentation_pt": {
            "slide_type": "summary",
            "heading": "Resumo",
            "body": "",
            "summary_points": [],
        },
        "presentation_en": {
            "slide_type": "summary",
            "heading": "Summary",
            "body": "",
            "summary_points": [],
        },
    }
    normalized = normalize_slide_draft(slide)
    assert normalized["presentation_pt"]["heading"] == "Resumo"
