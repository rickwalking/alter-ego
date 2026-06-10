"""Lucide icon registry for controlled inline SVG rendering in carousel templates."""

from __future__ import annotations

from collections.abc import Mapping

from rag_backend.domain.constants.carousel_presentation import LUCIDE_ICON_ALLOWLIST
from rag_backend.domain.models.carousel_presentation_adapters import (
    resolve_structured_item_icon_name,
)

_ERR_UNKNOWN_LUCIDE_ICON = "icon_name is not in the Lucide allowlist"
_SVG_OPEN = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
    'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" '
    'aria-hidden="true">'
)
_SVG_CLOSE = "</svg>"

_LUCIDE_INNER_SVG: dict[str, str] = {
    "book-open": (
        '<path d="M12 7v14"/>'
        '<path d="M3 18a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1h5a4 4 0 0 1 4 4 4 4 0 0 1 4-4h5'
        'a1 1 0 0 1 1 1v13a1 1 0 0 1-1 1h-6a3 3 0 0 0-3 3 3 3 0 0 0-3-3z"/>'
    ),
    "brain": (
        '<path d="M12 5a3 3 0 1 0-5.997.125 4 4 0 0 0-2.526 5.77 4 4 0 0 0 .556 6.588'
        'A4 4 0 1 0 12 18Z"/>'
        '<path d="M12 5a3 3 0 1 1 5.997.125 4 4 0 0 1 2.526 5.77 4 4 0 0 1-.556 6.588'
        'A4 4 0 1 1 12 18Z"/>'
        '<path d="M15 13a4.5 4.5 0 0 1-3-4 4.5 4.5 0 0 1-3 4"/>'
        '<path d="M17.599 6.5a3 3 0 0 0 .399-1.375"/>'
        '<path d="M6.003 5.125A3 3 0 0 0 6.401 6.5"/>'
        '<path d="M3.477 10.896a4 4 0 0 1 .585-.396"/>'
        '<path d="M19.938 10.5a4 4 0 0 1 .585.396"/>'
        '<path d="M6 18a4 4 0 0 1-1.967-.516"/>'
        '<path d="M19.967 17.484A4 4 0 0 1 18 18"/>'
    ),
    "chart-column": (
        '<path d="M3 3v16a2 2 0 0 0 2 2h16"/>'
        '<path d="M18 17V9"/>'
        '<path d="M13 17V5"/>'
        '<path d="M8 17v-3"/>'
    ),
    "eye": (
        '<path d="M2.062 12.348a1 1 0 0 1 0-.696 10.75 10.75 0 0 1 19.876 0 1 1 0 0 1 0 .696'
        '10.75 10.75 0 0 1-19.876 0"/>'
        '<circle cx="12" cy="12" r="3"/>'
    ),
    "flask-conical": (
        '<path d="M14 2v6a2 2 0 0 0 .245.96l5.51 10.08A2 2 0 0 1 18 22H6a2 2 0 0 1-1.755-2.96l5.51-10.08'
        'A2 2 0 0 0 10 8V2"/>'
        '<path d="M6.453 15h11.094"/>'
        '<path d="M8.5 2h7"/>'
    ),
    "message-circle": '<path d="M7.9 20A9 9 0 1 0 4 16.1L2 22Z"/>',
    "newspaper": (
        '<path d="M4 22h16a2 2 0 0 0 2-2V4a2 2 0 0 0-2-2H8a2 2 0 0 0-2 2v16a2 2 0 0 1-2 2Zm0 0'
        'a2 2 0 0 1-2-2v-9c0-1.1.9-2 2-2h2"/>'
        '<path d="M18 14h-8"/>'
        '<path d="M15 18h-5"/>'
        '<path d="M10 6h8v4h-8V6Z"/>'
    ),
    "shield-check": (
        '<path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1'
        'c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"/>'
        '<path d="m9 12 2 2 4-4"/>'
    ),
    "target": (
        '<circle cx="12" cy="12" r="10"/>'
        '<circle cx="12" cy="12" r="6"/>'
        '<circle cx="12" cy="12" r="2"/>'
    ),
    "wrench": (
        '<path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91'
        'a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/>'
    ),
}


class UnknownLucideIconError(ValueError):
    """Raised when a structured item resolves to a non-allowlisted icon identifier."""


def render_lucide_icon(icon_name: str) -> str:
    """Return inline Lucide SVG markup for an allowlisted icon_name."""
    normalized = icon_name.strip()
    if normalized not in LUCIDE_ICON_ALLOWLIST:
        raise UnknownLucideIconError(_ERR_UNKNOWN_LUCIDE_ICON)
    inner = _LUCIDE_INNER_SVG.get(normalized)
    if inner is None:
        raise UnknownLucideIconError(_ERR_UNKNOWN_LUCIDE_ICON)
    return f"{_SVG_OPEN}{inner}{_SVG_CLOSE}"


def render_structured_item_icon(item: Mapping[str, object]) -> str:
    """Resolve icon_name (with legacy icon fallback) and render controlled SVG."""
    resolved = resolve_structured_item_icon_name(item)
    if resolved is None:
        return ""
    return render_lucide_icon(resolved)


__all__ = [
    "UnknownLucideIconError",
    "render_lucide_icon",
    "render_structured_item_icon",
]
