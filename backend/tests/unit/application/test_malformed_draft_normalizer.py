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


def test_normalize_flat_locale_suffixed_intro_maps_subtitle_to_body() -> None:
    # Feature: GLM flat draft blob normalization
    # Scenario: Locale-suffixed intro blob maps subtitle_pt into the body
    raw = (
        "{'slide_number': 1, 'slide_type': 'intro', "
        "'heading_pt': 'Manchete PT', 'heading_en': 'Headline EN', "
        "'subtitle_pt': 'Corpo do slide em portugues.', "
        "'subtitle_en': 'Slide body in English.'}"
    )
    slide = {"slide_index": 1, "slide_type": "intro", "draft_text": raw}
    normalized = normalize_slide_draft(slide)

    pt = normalized["presentation_pt"]
    assert pt["body"] == "Corpo do slide em portugues."
    assert not pt["body"].startswith("{")
    assert normalized["presentation_en"]["body"] == "Slide body in English."


def test_normalize_flat_clean_single_locale_blob_maps_body() -> None:
    # Feature: GLM flat draft blob normalization
    # Scenario: Clean single-locale blob maps body into the presentation
    raw = (
        "{'heading': 'Acesso bloqueado', "
        "'body': 'O modelo chegou com acesso restrito por seguranca.'}"
    )
    slide = {"slide_index": 3, "slide_type": "content", "draft_text": raw}
    normalized = normalize_slide_draft(slide)

    assert (
        normalized["presentation_pt"]["body"]
        == "O modelo chegou com acesso restrito por seguranca."
    )


def test_normalize_flat_summary_points_localize_per_locale() -> None:
    # Feature: GLM flat draft blob normalization
    # Scenario: Summary points with title_pt items localize per locale
    raw = (
        "{'slide_type': 'summary', 'heading_pt': 'O que saber', "
        "'points': [{'title_pt': 'Ponto um', 'body_pt': 'Detalhe um', "
        "'title_en': 'Point one', 'body_en': 'Detail one'}]}"
    )
    slide = {"slide_index": 2, "slide_type": "summary", "draft_text": raw}
    normalized = normalize_slide_draft(slide)

    points = normalized["presentation_pt"]["summary_points"]
    assert points[0]["title"] == "Ponto um"
    assert points[0]["body"] == "Detalhe um"
    assert normalized["presentation_en"]["summary_points"][0]["title"] == "Point one"


def test_normalize_leaves_non_dict_draft_text_untouched() -> None:
    # Feature: GLM flat draft blob normalization
    # Scenario: Non-dict draft_text is left untouched
    slide = {
        "slide_index": 1,
        "slide_type": "intro",
        "draft_text": "Just plain prose, not a blob.",
    }
    assert normalize_slide_draft(slide) == slide


def test_parse_flat_blob_without_locale_keys_returns_nested_shape() -> None:
    # Feature: GLM flat draft blob normalization
    # Scenario: Locale-suffixed intro blob maps subtitle_pt into the body
    parsed = parse_bilingual_draft_blob(
        "{'heading_pt': 'PT', 'subtitle_pt': 'Corpo', 'subtitle_en': 'Body'}"
    )
    assert parsed is not None
    assert parsed["pt"]["body"] == "Corpo"
    assert parsed["en"]["body"] == "Body"
