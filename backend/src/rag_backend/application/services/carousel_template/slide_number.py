"""Normalize slide numbers for safe HTML template interpolation."""

from __future__ import annotations


def normalize_slide_number(slide_number: str | int) -> str:
    """Return a positive numeric slide number string for template use."""
    text = str(slide_number).strip()
    if text.isdigit() and int(text) > 0:
        return text
    return "1"


__all__ = ["normalize_slide_number"]
