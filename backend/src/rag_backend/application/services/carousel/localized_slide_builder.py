"""Build localized PT/EN slide review payloads from legacy or union drafts."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

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
from rag_backend.application.services.carousel.slide_parse_failures import (
    PARSE_FAILURE_MISSING_CANONICAL_KEYS,
    PARSE_FAILURE_RAW_DRAFT_FALLBACK,
    SlideParseFailure,
    is_clean_draft_copy,
    missing_canonical_keys,
)
from rag_backend.domain.constants.carousel import LANGUAGE_EN, LANGUAGE_PT
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


@dataclass(frozen=True)
class _LocalePayloadBuild:
    """One built locale payload plus its typed parse-failure reason, if any."""

    payload: dict[str, object] = field(default_factory=dict)
    failure_reason: str | None = None


def _resolve_locale_body(source: Mapping[str, object]) -> tuple[str, str | None]:
    """Resolve visible body copy; never dump a raw scaffold draft into body.

    AE-0309: when locale extraction fails and only the raw ``draft_text`` is
    available, plain clean copy is still accepted (legacy drafts store their
    body there), but scaffold/blob-looking drafts return a typed failure
    instead of leaking the whole raw draft into visible copy.
    """
    body = str(source.get(OUTLINE_LEGACY_BODY_KEY) or "")
    if body:
        return body, None
    raw_draft = str(source.get(SLIDE_DRAFT_TEXT_KEY) or "")
    if not raw_draft:
        return "", None
    if is_clean_draft_copy(raw_draft):
        return raw_draft, None
    return "", PARSE_FAILURE_RAW_DRAFT_FALLBACK


def _build_locale_payload(
    slide: Mapping[str, object],
    *,
    slide_type: str,
    locale_source: Mapping[str, object] | None,
) -> _LocalePayloadBuild:
    source = locale_source or slide
    heading = str(
        source.get(OUTLINE_LEGACY_HEADING_KEY)
        or source.get(OUTLINE_FIELD_TITLE)
        or source.get("title")
        or ""
    )
    body, failure_reason = _resolve_locale_body(source)
    payload: dict[str, object] = {
        "slide_type": str(source.get("slide_type") or slide_type),
        "heading": heading,
        "body": body,
    }
    for key in STRUCTURED_EXTRA_KEYS:
        value = source.get(key)
        if value is not None:
            payload[key] = value
    return _LocalePayloadBuild(payload=payload, failure_reason=failure_reason)


_LOCALE_PAYLOAD_PAIRS: tuple[tuple[str, str], ...] = (
    (PRESENTATION_PT_KEY, LANGUAGE_PT),
    (PRESENTATION_EN_KEY, LANGUAGE_EN),
)


def _canonical_key_failures(
    record: Mapping[str, object],
    raw_draft: str,
) -> list[SlideParseFailure]:
    """Flag locale payloads missing the canonical key set (AE-0309)."""
    slide_index_value = record.get(SLIDE_INDEX_KEY)
    slide_index = slide_index_value if isinstance(slide_index_value, int) else 0
    failures: list[SlideParseFailure] = []
    for locale_key, locale in _LOCALE_PAYLOAD_PAIRS:
        payload = as_dict(record.get(locale_key))
        if payload is None:
            continue
        if missing_canonical_keys(payload):
            failures.append(
                SlideParseFailure(
                    slide_index=slide_index,
                    locale=locale,
                    reason=PARSE_FAILURE_MISSING_CANONICAL_KEYS,
                    raw_draft=raw_draft,
                )
            )
    return failures


def _fallback_failures(
    record: Mapping[str, object],
    builds: tuple[_LocalePayloadBuild, _LocalePayloadBuild],
    raw_draft: str,
) -> list[SlideParseFailure]:
    """Collect typed raw-draft fallback failures for the built locales."""
    slide_index_value = record.get(SLIDE_INDEX_KEY)
    slide_index = slide_index_value if isinstance(slide_index_value, int) else 0
    locales = (LANGUAGE_PT, LANGUAGE_EN)
    return [
        SlideParseFailure(
            slide_index=slide_index,
            locale=locale,
            reason=build.failure_reason or "",
            raw_draft=raw_draft,
        )
        for locale, build in zip(locales, builds, strict=True)
        if build.failure_reason is not None
    ]


def build_localized_slide_with_failures(
    slide: Mapping[str, object],
    *,
    slide_index: int,
    translations_en: Mapping[str, object] | Mapping[int, object] | None = None,
) -> tuple[dict[str, object], list[SlideParseFailure]]:
    """Build one localized slide record plus its typed parse failures."""
    normalized = (
        normalize_slide_draft(dict(slide)) if isinstance(slide, dict) else dict(slide)
    )
    slide = normalized
    raw_draft = str(slide.get(SLIDE_DRAFT_TEXT_KEY) or "")
    slide_type = resolve_slide_type(slide, slide_index)
    presentation_pt = as_dict(slide.get(PRESENTATION_PT_KEY))
    presentation_en = as_dict(slide.get(PRESENTATION_EN_KEY))
    if presentation_pt is not None and presentation_en is not None:
        record: dict[str, object] = {
            SLIDE_INDEX_KEY: slide_index,
            "slide_type": slide_type,
            PRESENTATION_PT_KEY: dict(presentation_pt),
            PRESENTATION_EN_KEY: dict(presentation_en),
        }
        return record, _canonical_key_failures(record, raw_draft)
    en_source = _resolve_en_source(slide, slide_index, translations_en)
    pt_build = _build_locale_payload(slide, slide_type=slide_type, locale_source=None)
    en_build = _build_locale_payload(
        slide, slide_type=slide_type, locale_source=en_source
    )
    record = {
        SLIDE_INDEX_KEY: slide_index,
        "slide_type": slide_type,
        PRESENTATION_PT_KEY: pt_build.payload,
        PRESENTATION_EN_KEY: en_build.payload,
    }
    failures = _fallback_failures(record, (pt_build, en_build), raw_draft)
    failed_locales = {failure.locale for failure in failures}
    failures.extend(
        failure
        for failure in _canonical_key_failures(record, raw_draft)
        if failure.locale not in failed_locales
    )
    return record, failures


def build_localized_slide(
    slide: Mapping[str, object],
    *,
    slide_index: int,
    translations_en: Mapping[str, object] | Mapping[int, object] | None = None,
) -> dict[str, object]:
    """Build one localized slide review record from a legacy or union draft."""
    record, _ = build_localized_slide_with_failures(
        slide,
        slide_index=slide_index,
        translations_en=translations_en,
    )
    return record


def build_localized_slides_with_failures(
    slide_drafts: list[dict[str, object]],
    translations_en: Mapping[str, object] | Mapping[int, object] | None = None,
) -> tuple[list[dict[str, object]], list[SlideParseFailure]]:
    """Build localized slide records plus all typed parse failures."""
    localized: list[dict[str, object]] = []
    failures: list[SlideParseFailure] = []
    for index, slide in enumerate(slide_drafts):
        if not isinstance(slide, dict):
            continue
        slide_index = resolve_slide_index(slide, index + 1)
        record, slide_failures = build_localized_slide_with_failures(
            slide,
            slide_index=slide_index,
            translations_en=translations_en,
        )
        localized.append(record)
        failures.extend(slide_failures)
    return localized, failures


def build_localized_slides(
    slide_drafts: list[dict[str, object]],
    translations_en: Mapping[str, object] | Mapping[int, object] | None = None,
) -> list[dict[str, object]]:
    """Build localized slide review records for all drafts."""
    localized, _ = build_localized_slides_with_failures(
        slide_drafts,
        translations_en=translations_en,
    )
    return localized


__all__ = [
    "PRESENTATION_EN_KEY",
    "PRESENTATION_PT_KEY",
    "STRUCTURED_EXTRA_KEYS",
    "as_dict",
    "build_localized_slide",
    "build_localized_slide_with_failures",
    "build_localized_slides",
    "build_localized_slides_with_failures",
    "resolve_policy_version",
    "resolve_slide_index",
    "resolve_slide_type",
]
