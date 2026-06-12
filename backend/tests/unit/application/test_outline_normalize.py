"""Unit tests for editorial outline normalization."""

from rag_backend.application.services.carousel.outline_normalize import (
    canonical_slide_type,
    normalize_editorial_outline,
)
from rag_backend.application.services.carousel.types import MAX_SLIDES
from rag_backend.domain.constants.carousel import (
    SLIDE_TYPE_CLOSING,
    SLIDE_TYPE_CONTENT,
    SLIDE_TYPE_CTA,
    SLIDE_TYPE_INTRO,
    SLIDE_TYPE_SUMMARY,
)


class TestNormalizeEditorialOutline:
    def test_trims_extra_slides_to_max(self) -> None:
        raw = [
            {"slide_index": index, "title": f"Slide {index}", "key_points": ["a"]}
            for index in range(1, 12)
        ]
        result = normalize_editorial_outline(raw)
        assert len(result) == MAX_SLIDES

    def test_assigns_canonical_slide_types(self) -> None:
        raw = [{"slide_index": 1, "title": "Hook", "key_points": ["a"]}]
        result = normalize_editorial_outline(raw)
        assert result[0]["slide_type"] == SLIDE_TYPE_INTRO

    def test_renumbers_slides_sequentially(self) -> None:
        raw = [
            {"slide_index": 99, "title": "A", "key_points": []},
            {"slide_index": 100, "title": "B", "key_points": []},
        ]
        result = normalize_editorial_outline(raw)
        assert result[0]["slide_index"] == 1
        assert result[1]["slide_index"] == 2

    def test_preserves_intro_tldr_strip(self) -> None:
        raw = [
            {
                "slide_index": 1,
                "title": "Hook",
                "key_points": [],
                "tldr_strip": "One-line summary.",
            }
        ]
        result = normalize_editorial_outline(raw)
        assert result[0].get("tldr_strip") == "One-line summary."

    def test_resolves_bilingual_title_dict_to_portuguese(self) -> None:
        raw = [
            {
                "slide_index": 1,
                "title": {
                    "pt": "O que é **harness** na IA?",
                    "en": "What is **harness** in AI?",
                },
                "key_points": [],
            }
        ]
        result = normalize_editorial_outline(raw)
        assert result[0]["title"] == "O que é **harness** na IA?"

    def test_resolves_stringified_bilingual_title(self) -> None:
        raw = [
            {
                "slide_index": 1,
                "title": "{'pt': 'Hook PT', 'en': 'Hook EN'}",
                "key_points": [{"pt": "Ponto A", "en": "Point A"}],
            }
        ]
        result = normalize_editorial_outline(raw)
        assert result[0]["title"] == "Hook PT"
        assert result[0]["key_points"] == ["Ponto A"]

    def test_strips_dash_punctuation_from_outline_copy(self) -> None:
        raw = [
            {
                "slide_index": 1,
                "title": "Ideia\u2014outra ideia",
                "key_points": ["Um ponto - outro ponto"],
            }
        ]
        result = normalize_editorial_outline(raw)
        assert result[0]["title"] == "Ideia, outra ideia"
        assert result[0]["key_points"] == ["Um ponto, outro ponto"]


class TestCanonicalSlideType:
    def test_maps_all_seven_positions(self) -> None:
        assert canonical_slide_type(1) == SLIDE_TYPE_INTRO
        assert canonical_slide_type(2) == SLIDE_TYPE_SUMMARY
        assert canonical_slide_type(3) == SLIDE_TYPE_CONTENT
        assert canonical_slide_type(6) == SLIDE_TYPE_CLOSING
        assert canonical_slide_type(7) == SLIDE_TYPE_CTA
