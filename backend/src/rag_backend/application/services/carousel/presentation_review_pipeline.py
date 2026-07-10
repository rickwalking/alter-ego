"""Core build/validate pipeline for localized presentation review updates.

Split out of ``presentation_review`` (AE-0309) so the write path can compose
the granular steps — build with typed parse failures, deterministic scaffold
recovery, bounded repair, validation with parse-failure injection — while the
resolvers/blocking checks stay in ``presentation_review``.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime

from rag_backend.application.services.carousel.editorial_distribution_constants import (
    SLIDE_INDEX_KEY,
)
from rag_backend.application.services.carousel.localized_slide_builder import (
    PRESENTATION_EN_KEY,
    PRESENTATION_PT_KEY,
    as_dict,
    build_localized_slides_with_failures,
    resolve_policy_version,
)
from rag_backend.application.services.carousel.presentation_policy import (
    CarouselPresentationPolicy,
    load_presentation_policy,
)
from rag_backend.application.services.carousel.presentation_review_repair import (
    repair_localized_slides,
    repair_localized_slides_sync,
)
from rag_backend.application.services.carousel.presentation_validation import (
    ValidatePayloadCommand,
    build_validation_report,
    validate_bilingual_shape_parity,
    validate_slide_payload,
)
from rag_backend.application.services.carousel.slide_parse_failures import (
    SlideParseFailure,
    marker_violations,
)
from rag_backend.application.services.carousel.slide_scaffold_recovery import (
    recover_parse_failures,
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


@dataclass(frozen=True)
class PresentationReviewBuildResult:
    """Review updates plus the typed parse failures observed while building."""

    updates: dict[str, object]
    parse_failures: tuple[SlideParseFailure, ...] = ()
    unrecovered_failures: tuple[SlideParseFailure, ...] = ()


def _validate_single_slide(
    slide: dict[str, object],
    policy: CarouselPresentationPolicy,
) -> list[SlideValidationViolation]:
    """Validate PT and EN locales of one slide, including bilingual parity."""
    slide_index_value = slide.get(SLIDE_INDEX_KEY)
    slide_index = slide_index_value if isinstance(slide_index_value, int) else None
    presentation_pt = as_dict(slide.get(PRESENTATION_PT_KEY))
    presentation_en = as_dict(slide.get(PRESENTATION_EN_KEY))
    violations: list[SlideValidationViolation] = list(marker_violations(slide))
    if presentation_pt is not None:
        violations.extend(
            validate_slide_payload(
                ValidatePayloadCommand(
                    presentation_pt,
                    locale=LANGUAGE_PT,
                    policy=policy,
                    slide_index=slide_index,
                )
            )
        )
    if presentation_en is not None:
        violations.extend(
            validate_slide_payload(
                ValidatePayloadCommand(
                    presentation_en,
                    locale=LANGUAGE_EN,
                    policy=policy,
                    slide_index=slide_index,
                )
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
    return violations


def validate_localized_slides(
    localized_slides: list[dict[str, object]],
    *,
    policy_version: str | None = None,
) -> SlideValidationReport:
    """Validate PT/EN presentation payloads and return a blocking report.

    Parse-failure markers stored on the slides (AE-0309) are folded in as
    blocking ``slide_parse_failed`` violations so every read path stays
    fail-closed.
    """
    active_version = policy_version or DEFAULT_PRESENTATION_POLICY_VERSION
    policy = load_presentation_policy(active_version)
    violations: list[SlideValidationViolation] = []
    for slide in localized_slides:
        violations.extend(_validate_single_slide(slide, policy))
    # AE-0312: blocking is severity-derived inside build_validation_report so the
    # stored report agrees with the approval-gate decision (no hardcoded literal).
    return build_validation_report(violations)


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


def _build_and_recover(
    slide_drafts: list[dict[str, object]],
    translations_en: Mapping[int, dict[str, object]] | None,
) -> tuple[
    list[dict[str, object]],
    tuple[SlideParseFailure, ...],
    tuple[SlideParseFailure, ...],
]:
    """Build localized slides, then run deterministic parse-failure recovery."""
    built, failures = build_localized_slides_with_failures(
        slide_drafts,
        translations_en=translations_en,
    )
    recovered, remaining = recover_parse_failures(built, failures)
    return recovered, tuple(failures), tuple(remaining)


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
    localized, _, _ = _build_and_recover(slide_drafts, translations_en)
    localized = repair_localized_slides_sync(localized, policy_version=resolved_policy)
    return _review_updates_for(
        localized,
        resolved_policy=resolved_policy,
        translations_en=translations_en,
    )


async def build_presentation_review_result_async(
    slide_drafts: list[dict[str, object]],
    *,
    translations_en: Mapping[int, dict[str, object]] | None = None,
    policy_version: str | None = None,
) -> PresentationReviewBuildResult:
    """Async build that also reports typed parse failures (AE-0309)."""
    if not slide_drafts:
        return PresentationReviewBuildResult(_empty_review_updates(policy_version))
    resolved_policy = policy_version or resolve_policy_version(slide_drafts)
    localized, all_failures, remaining = _build_and_recover(
        slide_drafts, translations_en
    )
    localized = await repair_localized_slides(localized, policy_version=resolved_policy)
    updates = _review_updates_for(
        localized,
        resolved_policy=resolved_policy,
        translations_en=translations_en,
    )
    return PresentationReviewBuildResult(
        updates=updates,
        parse_failures=all_failures,
        unrecovered_failures=remaining,
    )


async def build_presentation_review_updates_async(
    slide_drafts: list[dict[str, object]],
    *,
    translations_en: Mapping[int, dict[str, object]] | None = None,
    policy_version: str | None = None,
) -> dict[str, object]:
    """Async workflow variant that routes repair through run_bounded_repair."""
    result = await build_presentation_review_result_async(
        slide_drafts,
        translations_en=translations_en,
        policy_version=policy_version,
    )
    return result.updates


__all__ = [
    "WORKFLOW_STATE_LOCALIZED_SLIDES_KEY",
    "WORKFLOW_STATE_PRESENTATION_POLICY_VERSION_KEY",
    "WORKFLOW_STATE_PRESENTATION_VALIDATION_KEY",
    "WORKFLOW_STATE_TRANSLATIONS_EN_KEY",
    "PresentationReviewBuildResult",
    "build_presentation_review_result_async",
    "build_presentation_review_updates",
    "build_presentation_review_updates_async",
    "deserialize_translations_en",
    "serialize_translations_en",
    "validate_localized_slides",
    "validation_report_to_dict",
]
