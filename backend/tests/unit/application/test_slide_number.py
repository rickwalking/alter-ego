"""Unit tests for slide number normalization."""

from __future__ import annotations

from rag_backend.application.services.carousel_template.slide_number import (
    normalize_slide_number,
)


def test_normalize_slide_number_accepts_positive_integers() -> None:
    assert normalize_slide_number(3) == "3"
    assert normalize_slide_number("7") == "7"


def test_normalize_slide_number_rejects_unsafe_values() -> None:
    assert normalize_slide_number("<script>") == "1"
    assert normalize_slide_number("0") == "1"
    assert normalize_slide_number("") == "1"
