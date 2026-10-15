"""Normalize slide numbers for safe HTML template interpolation."""

from __future__ import annotations

SLIDE_COUNTER_FORMAT = "{number:02d} / {total:02d}"


def normalize_slide_number(slide_number: str | int) -> str:
    """Return a positive numeric slide number string for template use."""
    text = str(slide_number).strip()
    if text.isdigit() and int(text) > 0:
        return text
    return "1"


def format_slide_counter(slide_number: str | int, total_slides: int) -> str:
    """``03 / 07``, ``10 / 10``: both sides zero-padded to two digits (AE-0372).

    The old templates glued a literal ``0`` in front of the number, so slide 10
    would have read ``010 / 10``.
    """
    number = int(normalize_slide_number(slide_number))
    return SLIDE_COUNTER_FORMAT.format(number=number, total=total_slides)


__all__ = ["SLIDE_COUNTER_FORMAT", "format_slide_counter", "normalize_slide_number"]
