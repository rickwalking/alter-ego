"""Build localized PT/EN slide review payloads from legacy or union drafts."""

from __future__ import annotations

from collections.abc import Mapping

from rag_backend.application.services.carousel.editorial_distribution_constants import (
    OUTLINE_LEGACY_BODY_KEY,
    OUTLINE_LEGACY_HEADING_KEY,
    SLIDE_DRAFT_TEXT_KEY,
    SLIDE_INDEX_KEY,
)
from rag_backend.application.services.carousel.malformed_draft_normalizer import (
    normalize_slide_draft,
)
from rag_backend.application.services.carousel.outline_normalize import (
    OUTLINE_FIELD_SLIDE_INDEX,
    OUTLINE_FIELD_TITLE,
    canonical_slide_type,
)
from rag_backend.domain.constants.presentation_policy import (
    DEFAULT_PRESENTATION_POLICY_VERSION,
)

PRESENTATION_PT_KEY = "presentation_pt"
PRESENTATION_EN_KEY = "presentation_en"
STRUCTURED_EXTRA_KEYS: tuple[str, ...] = (
    "features",
    "stats",
    "insight",
    "summary_points",
    "actions",
    "tldr_strip",
    "content_kind",
    "creator_name",
    "creator_handle",
    "creator_website",
)


def as_dict(value: object) -> dict[str, object] | None:
    """Return the value when it is a dict, otherwise None."""
    return value if isinstance(value, dict) else None


def resolve_slide_index(slide: Mapping[str, object], fallback: int) -> int:
    """Resolve a positive slide index from known draft keys."""
    raw = (
        slide.get(SLIDE_INDEX_KEY)
        or slide.get(OUTLINE_FIELD_SLIDE_INDEX)
        or slide.get("number")
    )
    if isinstance(raw, int) and raw > 0:
        return raw
    if isinstance(raw, str) and raw.isdigit():
        return int(raw)
    return fallback


def resolve_slide_type(slide: Mapping[str, object], slide_index: int) -> str:
    """Resolve the slide type, defaulting to the canonical type for the index."""
    raw = slide.get("slide_type") or slide.get("type")
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    return canonical_slide_type(slide_index)


def resolve_policy_version(slide_drafts: list[dict[str, object]]) -> str:
    """Resolve the presentation policy version embedded in drafts."""
    for slide in slide_drafts:
        version = slide.get("policy_version")
        if isinstance(version, str) and version.strip():
            return version.strip()
    return DEFAULT_PRESENTATION_POLICY_VERSION


def _resolve_en_source(
    slide: Mapping[str, object],
    slide_index: int,
    translations_en: Mapping[str, object] | Mapping[int, object] | None,
) -> Mapping[str, object] | None:
    presentation_en = as_dict(slide.get(PRESENTATION_EN_KEY))
    if presentation_en is not None:
        return presentation_en
    direct = as_dict(slide.get("translation_en"))
    if direct is not None:
        return direct
    extras = as_dict(slide.get("extras"))
    if extras is not None:
        nested = as_dict(extras.get("translation_en"))
        if nested is not None:
            return nested
    result: Mapping[str, object] | None = None
    if translations_en is not None:
        keyed = translations_en.get(slide_index)
        if isinstance(keyed, Mapping):
            result = keyed
        else:
            keyed_str = translations_en.get(str(slide_index))
            if isinstance(keyed_str, Mapping):
                result = keyed_str
    return result


def _build_locale_payload(
    slide: Mapping[str, object],
    *,
    slide_type: str,
    locale_source: Mapping[str, object] | None,
) -> dict[str, object]:
    source = locale_source or slide
    heading = str(
        source.get(OUTLINE_LEGACY_HEADING_KEY)
        or source.get(OUTLINE_FIELD_TITLE)
        or source.get("heading")
        or source.get("title")
        or ""
    )
    body = str(
        source.get(OUTLINE_LEGACY_BODY_KEY)
        or source.get("body")
        or source.get(SLIDE_DRAFT_TEXT_KEY)
        or ""
    )
    payload: dict[str, object] = {
        "slide_type": str(source.get("slide_type") or slide_type),
        "heading": heading,
        "body": body,
    }
    for key in STRUCTURED_EXTRA_KEYS:
        value = source.get(key)
        if value is not None:
            payload[key] = value
    return payload


def build_localized_slide(
    slide: Mapping[str, object],
    *,
    slide_index: int,
    translations_en: Mapping[str, object] | Mapping[int, object] | None = None,
) -> dict[str, object]:
    """Build one localized slide review record from a legacy or union draft."""
    normalized = (
        normalize_slide_draft(dict(slide)) if isinstance(slide, dict) else dict(slide)
    )
    slide = normalized
    slide_type = resolve_slide_type(slide, slide_index)
    presentation_pt = as_dict(slide.get(PRESENTATION_PT_KEY))
    presentation_en = as_dict(slide.get(PRESENTATION_EN_KEY))
    if presentation_pt is not None and presentation_en is not None:
        return {
            SLIDE_INDEX_KEY: slide_index,
            "slide_type": slide_type,
            PRESENTATION_PT_KEY: dict(presentation_pt),
            PRESENTATION_EN_KEY: dict(presentation_en),
        }
    en_source = _resolve_en_source(slide, slide_index, translations_en)
    return {
        SLIDE_INDEX_KEY: slide_index,
        "slide_type": slide_type,
        PRESENTATION_PT_KEY: _build_locale_payload(
            slide,
            slide_type=slide_type,
            locale_source=None,
        ),
        PRESENTATION_EN_KEY: _build_locale_payload(
            slide,
            slide_type=slide_type,
            locale_source=en_source,
        ),
    }


def build_localized_slides(
    slide_drafts: list[dict[str, object]],
    translations_en: Mapping[str, object] | Mapping[int, object] | None = None,
) -> list[dict[str, object]]:
    """Build localized slide review records for all drafts."""
    localized: list[dict[str, object]] = []
    for index, slide in enumerate(slide_drafts):
        if not isinstance(slide, dict):
            continue
        slide_index = resolve_slide_index(slide, index + 1)
        localized.append(
            build_localized_slide(
                slide,
                slide_index=slide_index,
                translations_en=translations_en,
            )
        )
    return localized


__all__ = [
    "PRESENTATION_EN_KEY",
    "PRESENTATION_PT_KEY",
    "STRUCTURED_EXTRA_KEYS",
    "as_dict",
    "build_localized_slide",
    "build_localized_slides",
    "resolve_policy_version",
    "resolve_slide_index",
    "resolve_slide_type",
]
