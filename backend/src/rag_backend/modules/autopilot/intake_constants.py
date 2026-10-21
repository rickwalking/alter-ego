"""``field`` names on topic-intake rejections (spec §6).

A rejection carries ``field`` when one field caused it, so the scout can fix
that topic. The names are the request's JSON keys.
"""

from __future__ import annotations

FIELD_TITLE = "title"
FIELD_ANGLE = "angle"
FIELD_WHY_VIRAL = "why_viral"
FIELD_AUDIENCE = "audience"
FIELD_NICHE = "niche"
FIELD_BRIEF = "brief"
FIELD_IMAGE_STYLE = "image_style"
FIELD_IMAGE_GUIDANCE = "image_guidance"
FIELD_THESIS_DRAFT = "thesis_draft"
FIELD_SOURCES_TEMPLATE = "sources[{index}]"

__all__ = [
    "FIELD_ANGLE",
    "FIELD_AUDIENCE",
    "FIELD_BRIEF",
    "FIELD_IMAGE_GUIDANCE",
    "FIELD_IMAGE_STYLE",
    "FIELD_NICHE",
    "FIELD_SOURCES_TEMPLATE",
    "FIELD_THESIS_DRAFT",
    "FIELD_TITLE",
    "FIELD_WHY_VIRAL",
]
