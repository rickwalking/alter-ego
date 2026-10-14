"""Apply the deterministic casing repair to persisted slide copy (AE-0366).

The validator approves the REPAIRED copy (first letters capitalized, configured
proper nouns canonicalized), so the ``carousel_slides`` rows the renderer reads
must carry the same repaired copy in both locales: heading, body, structured
items and ``translation_en``. Policy-version gated (no-op on v1) and idempotent.
"""

from __future__ import annotations

from dataclasses import replace

from rag_backend.application.services.carousel.presentation_casing import (
    repair_casing,
)
from rag_backend.application.services.carousel.presentation_policy_types import (
    CarouselPresentationPolicy,
)
from rag_backend.application.services.carousel.types import SlideData
from rag_backend.domain.constants.carousel import LANGUAGE_EN, LANGUAGE_PT

_KEY_SLIDE_TYPE = "slide_type"
_KEY_HEADING = "heading"
_KEY_BODY = "body"
_KEY_FEATURES = "features"
_KEY_SUMMARY_POINTS = "summary_points"


def _item_list(value: object) -> list[dict[str, str]] | None:
    if not isinstance(value, list):
        return None
    return [
        {str(key): str(item_value) for key, item_value in item.items()}
        for item in value
        if isinstance(item, dict)
    ]


def _repair_translation(
    translation_en: dict[str, object] | None,
    slide_type: str,
    policy: CarouselPresentationPolicy,
) -> dict[str, object] | None:
    if translation_en is None:
        return None
    repaired = repair_casing(
        {**translation_en, _KEY_SLIDE_TYPE: slide_type}, LANGUAGE_EN, policy
    )
    if _KEY_SLIDE_TYPE not in translation_en:
        repaired.pop(_KEY_SLIDE_TYPE, None)
    return repaired


def repair_slide_data_casing(
    data: SlideData,
    policy: CarouselPresentationPolicy,
) -> SlideData:
    """Return the slide data with PT + EN copy casing-repaired for rendering."""
    if not policy.has_casing_rules:
        return data
    pt = repair_casing(
        {
            _KEY_SLIDE_TYPE: data.slide_type,
            _KEY_HEADING: data.heading,
            _KEY_BODY: data.body,
            _KEY_FEATURES: data.features,
            _KEY_SUMMARY_POINTS: data.summary_points,
        },
        LANGUAGE_PT,
        policy,
    )
    return replace(
        data,
        heading=str(pt.get(_KEY_HEADING) or ""),
        body=str(pt.get(_KEY_BODY) or ""),
        features=_item_list(pt.get(_KEY_FEATURES)),
        summary_points=_item_list(pt.get(_KEY_SUMMARY_POINTS)),
        translation_en=_repair_translation(
            data.translation_en, data.slide_type, policy
        ),
    )


__all__ = ["repair_slide_data_casing"]
