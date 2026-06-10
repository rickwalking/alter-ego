"""Presentation validation and workflow review updates for content gates."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime

from rag_backend.application.services.carousel.editorial_distribution_constants import (
    SLIDE_INDEX_KEY,
)
from rag_backend.application.services.carousel.localized_slide_builder import (
    PRESENTATION_EN_KEY,
    PRESENTATION_PT_KEY,
    as_dict,
    build_localized_slide,
    build_localized_slides,
    resolve_policy_version,
)
from rag_backend.application.services.carousel.presentation_policy import (
    load_presentation_policy,
)
from rag_backend.application.services.carousel.presentation_review_repair import (
    repair_localized_slides,
    repair_localized_slides_sync,
)
from rag_backend.application.services.carousel.presentation_validation import (
    build_validation_report,
    validate_bilingual_shape_parity,
    validate_slide_payload,
)
from rag_backend.domain.constants.carousel import LANGUAGE_EN, LANGUAGE_PT
from rag_backend.domain.constants.presentation_policy import (
    DEFAULT_PRESENTATION_POLICY_VERSION,
)
from rag_backend.domain.models.carousel_presentation import (
    SlideValidationReport,
    SlideValidationViolation,
)

WORKFLOW_STATE_LOCALIZED_SLIDES_KEY = "localized_slides"
WORKFLOW_STATE_PRESENTATION_VALIDATION_KEY = "presentation_validation"
WORKFLOW_STATE_PRESENTATION_POLICY_VERSION_KEY = "presentation_policy_version"
WORKFLOW_STATE_TRANSLATIONS_EN_KEY = "translations_en"


def validate_localized_slides(
    localized_slides: list[dict[str, object]],
    *,
    policy_version: str | None = None,
) -> SlideValidationReport:
    """Validate PT/EN presentation payloads and return a blocking report."""
    active_version = policy_version or DEFAULT_PRESENTATION_POLICY_VERSION
    policy = load_presentation_policy(active_version)
    violations: list[SlideValidationViolation] = []
    for slide in localized_slides:
        slide_index_value = slide.get(SLIDE_INDEX_KEY)
        slide_index = slide_index_value if isinstance(slide_index_value, int) else None
        presentation_pt = as_dict(slide.get(PRESENTATION_PT_KEY))
        presentation_en = as_dict(slide.get(PRESENTATION_EN_KEY))
        if presentation_pt is not None:
            violations.extend(
                validate_slide_payload(
                    presentation_pt,
                    locale=LANGUAGE_PT,
                    policy=policy,
                    slide_index=slide_index,
                )
            )
        if presentation_en is not None:
            violations.extend(
                validate_slide_payload(
                    presentation_en,
                    locale=LANGUAGE_EN,
                    policy=policy,
                    slide_index=slide_index,
                )
            )
        if presentation_pt is not None and presentation_en is not None:
            parity = validate_bilingual_shape_parity(
                presentation_pt,
                presentation_en,
                slide_index=slide_index,
            )
            if parity is not None:
                violations.append(parity)
    return build_validation_report(violations, blocking=True)


def validation_report_to_dict(report: SlideValidationReport) -> dict[str, object]:
    """Serialize a validation report for workflow state and API consumers."""
    return report.model_dump(mode="json")


def serialize_translations_en(
    translations_en: Mapping[int, dict[str, object]],
) -> dict[str, object]:
    """Serialize EN translations keyed by slide index for workflow state."""
    return {str(index): payload for index, payload in translations_en.items()}


def deserialize_translations_en(
    raw: object,
) -> dict[int, dict[str, object]] | None:
    """Deserialize workflow-state EN translations keyed by slide index."""
    if not isinstance(raw, dict):
        return None
    result: dict[int, dict[str, object]] = {}
    for key, value in raw.items():
        if not isinstance(value, dict):
            continue
        index = int(key) if isinstance(key, int) else int(str(key))
        result[index] = value
    return result or None


def _empty_review_updates(policy_version: str | None) -> dict[str, object]:
    return {
        WORKFLOW_STATE_LOCALIZED_SLIDES_KEY: [],
        WORKFLOW_STATE_PRESENTATION_VALIDATION_KEY: validation_report_to_dict(
            SlideValidationReport(
                validation_status="valid",
                validated_at=datetime.now(tz=UTC),
                blocking=False,
                violations=[],
            )
        ),
        WORKFLOW_STATE_PRESENTATION_POLICY_VERSION_KEY: (
            policy_version or DEFAULT_PRESENTATION_POLICY_VERSION
        ),
    }


def _review_updates_for(
    localized_slides: list[dict[str, object]],
    *,
    resolved_policy: str,
    translations_en: Mapping[int, dict[str, object]] | None,
) -> dict[str, object]:
    report = validate_localized_slides(
        localized_slides,
        policy_version=resolved_policy,
    )
    updates: dict[str, object] = {
        WORKFLOW_STATE_LOCALIZED_SLIDES_KEY: localized_slides,
        WORKFLOW_STATE_PRESENTATION_VALIDATION_KEY: validation_report_to_dict(report),
        WORKFLOW_STATE_PRESENTATION_POLICY_VERSION_KEY: resolved_policy,
    }
    if translations_en:
        updates[WORKFLOW_STATE_TRANSLATIONS_EN_KEY] = serialize_translations_en(
            dict(translations_en)
        )
    return updates


def build_presentation_review_updates(
    slide_drafts: list[dict[str, object]],
    *,
    translations_en: Mapping[int, dict[str, object]] | None = None,
    policy_version: str | None = None,
) -> dict[str, object]:
    """Build workflow updates for localized slides and presentation validation."""
    if not slide_drafts:
        return _empty_review_updates(policy_version)
    resolved_policy = policy_version or resolve_policy_version(slide_drafts)
    localized_slides = repair_localized_slides_sync(
        build_localized_slides(
            slide_drafts,
            translations_en=translations_en,
        ),
        policy_version=resolved_policy,
    )
    return _review_updates_for(
        localized_slides,
        resolved_policy=resolved_policy,
        translations_en=translations_en,
    )


async def build_presentation_review_updates_async(
    slide_drafts: list[dict[str, object]],
    *,
    translations_en: Mapping[int, dict[str, object]] | None = None,
    policy_version: str | None = None,
) -> dict[str, object]:
    """Async workflow variant that routes repair through run_bounded_repair."""
    if not slide_drafts:
        return _empty_review_updates(policy_version)
    resolved_policy = policy_version or resolve_policy_version(slide_drafts)
    localized_slides = await repair_localized_slides(
        build_localized_slides(
            slide_drafts,
            translations_en=translations_en,
        ),
        policy_version=resolved_policy,
    )
    return _review_updates_for(
        localized_slides,
        resolved_policy=resolved_policy,
        translations_en=translations_en,
    )


def _state_policy_version(state: Mapping[str, object]) -> str | None:
    raw = state.get(WORKFLOW_STATE_PRESENTATION_POLICY_VERSION_KEY)
    return str(raw) if raw else None


def resolve_presentation_review_from_state(
    state: Mapping[str, object],
) -> dict[str, object]:
    """Ensure presentation review fields exist, deriving them from drafts when needed."""
    localized = state.get(WORKFLOW_STATE_LOCALIZED_SLIDES_KEY)
    validation = state.get(WORKFLOW_STATE_PRESENTATION_VALIDATION_KEY)
    policy_version = _state_policy_version(state) or DEFAULT_PRESENTATION_POLICY_VERSION
    if isinstance(validation, dict):
        return {
            WORKFLOW_STATE_LOCALIZED_SLIDES_KEY: (
                localized if isinstance(localized, list) else []
            ),
            WORKFLOW_STATE_PRESENTATION_VALIDATION_KEY: validation,
            WORKFLOW_STATE_PRESENTATION_POLICY_VERSION_KEY: policy_version,
        }
    if isinstance(localized, list):
        return {
            WORKFLOW_STATE_LOCALIZED_SLIDES_KEY: localized,
            WORKFLOW_STATE_PRESENTATION_VALIDATION_KEY: validation_report_to_dict(
                validate_localized_slides(
                    [slide for slide in localized if isinstance(slide, dict)],
                    policy_version=_state_policy_version(state),
                )
            ),
            WORKFLOW_STATE_PRESENTATION_POLICY_VERSION_KEY: policy_version,
        }
    slide_drafts = state.get("slide_drafts")
    if not isinstance(slide_drafts, list):
        return build_presentation_review_updates([])
    draft_dicts = [slide for slide in slide_drafts if isinstance(slide, dict)]
    translations = deserialize_translations_en(
        state.get(WORKFLOW_STATE_TRANSLATIONS_EN_KEY)
    )
    return build_presentation_review_updates(
        draft_dicts,
        translations_en=translations,
        policy_version=_state_policy_version(state),
    )


def has_blocking_presentation_validation(state: Mapping[str, object]) -> bool:
    """Return True when presentation validation blocks content approval."""
    validation = state.get(WORKFLOW_STATE_PRESENTATION_VALIDATION_KEY)
    if isinstance(validation, dict):
        return validation.get("blocking") is True
    review = resolve_presentation_review_from_state(state)
    derived = review.get(WORKFLOW_STATE_PRESENTATION_VALIDATION_KEY)
    if not isinstance(derived, dict):
        return False
    return derived.get("blocking") is True


__all__ = [
    "WORKFLOW_STATE_LOCALIZED_SLIDES_KEY",
    "WORKFLOW_STATE_PRESENTATION_POLICY_VERSION_KEY",
    "WORKFLOW_STATE_PRESENTATION_VALIDATION_KEY",
    "WORKFLOW_STATE_TRANSLATIONS_EN_KEY",
    "build_localized_slide",
    "build_localized_slides",
    "build_presentation_review_updates",
    "build_presentation_review_updates_async",
    "deserialize_translations_en",
    "has_blocking_presentation_validation",
    "repair_localized_slides",
    "resolve_presentation_review_from_state",
    "serialize_translations_en",
    "validate_localized_slides",
    "validation_report_to_dict",
]
