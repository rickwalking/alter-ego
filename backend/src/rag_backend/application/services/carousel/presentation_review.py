"""Presentation validation and workflow review updates for content gates.

The core build/validate pipeline lives in ``presentation_review_pipeline``
(AE-0309); this module keeps the read-path resolvers and the approval
blocking checks, and re-exports the pipeline API for existing callers.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping

from rag_backend.application.services.carousel.localized_slide_builder import (
    build_localized_slide,
    build_localized_slides,
)
from rag_backend.application.services.carousel.presentation_review_pipeline import (
    WORKFLOW_STATE_LOCALIZED_SLIDES_KEY,
    WORKFLOW_STATE_PRESENTATION_POLICY_VERSION_KEY,
    WORKFLOW_STATE_PRESENTATION_VALIDATION_KEY,
    WORKFLOW_STATE_TRANSLATIONS_EN_KEY,
    build_presentation_review_updates,
    build_presentation_review_updates_async,
    deserialize_translations_en,
    serialize_translations_en,
    validate_localized_slides,
    validation_report_to_dict,
)
from rag_backend.application.services.carousel.presentation_review_repair import (
    repair_localized_slides,
    repair_localized_slides_sync,
)
from rag_backend.domain.constants.presentation_policy import (
    DEFAULT_PRESENTATION_POLICY_VERSION,
)


def _state_policy_version(state: Mapping[str, object]) -> str | None:
    raw = state.get(WORKFLOW_STATE_PRESENTATION_POLICY_VERSION_KEY)
    return str(raw) if raw else None


# Chain-of-Responsibility: resolvers are tried in registration order;
# the first to return a non-None dict wins.  The terminal fallback
# (no resolver matched) returns an empty review.

_RESOLVERS: list[Callable[[Mapping[str, object]], dict[str, object] | None]] = []


def _register_resolver(
    func: Callable[[Mapping[str, object]], dict[str, object] | None],
) -> Callable[[Mapping[str, object]], dict[str, object] | None]:
    """Register a resolver function in the CoR chain."""
    _RESOLVERS.append(func)
    return func


@_register_resolver
def _resolve_from_validation(
    state: Mapping[str, object],
) -> dict[str, object] | None:
    """Resolve review from existing presentation_validation."""
    validation = state.get(WORKFLOW_STATE_PRESENTATION_VALIDATION_KEY)
    if not isinstance(validation, dict):
        return None
    localized = state.get(WORKFLOW_STATE_LOCALIZED_SLIDES_KEY)
    policy_version = _state_policy_version(state) or DEFAULT_PRESENTATION_POLICY_VERSION
    return {
        WORKFLOW_STATE_LOCALIZED_SLIDES_KEY: (
            localized if isinstance(localized, list) else []
        ),
        WORKFLOW_STATE_PRESENTATION_VALIDATION_KEY: validation,
        WORKFLOW_STATE_PRESENTATION_POLICY_VERSION_KEY: policy_version,
    }


@_register_resolver
def _resolve_from_localized_slides(
    state: Mapping[str, object],
) -> dict[str, object] | None:
    """Resolve review by validating existing localized_slides."""
    localized = state.get(WORKFLOW_STATE_LOCALIZED_SLIDES_KEY)
    if not isinstance(localized, list):
        return None
    policy_version = _state_policy_version(state) or DEFAULT_PRESENTATION_POLICY_VERSION
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


@_register_resolver
def _resolve_from_slide_drafts(
    state: Mapping[str, object],
) -> dict[str, object] | None:
    """Resolve review by building from legacy slide_drafts."""
    slide_drafts = state.get("slide_drafts")
    if not isinstance(slide_drafts, list):
        return None
    draft_dicts = [slide for slide in slide_drafts if isinstance(slide, dict)]
    translations = deserialize_translations_en(
        state.get(WORKFLOW_STATE_TRANSLATIONS_EN_KEY)
    )
    return build_presentation_review_updates(
        draft_dicts,
        translations_en=translations,
        policy_version=_state_policy_version(state),
    )


def resolve_presentation_review_from_state(
    state: Mapping[str, object],
) -> dict[str, object]:
    """Ensure presentation review fields exist via Chain-of-Responsibility.

    Tries each registered resolver in order:
      1. Existing presentation_validation (fast path)
      2. Existing localized_slides (re-validate on read)
      3. Legacy slide_drafts (build from scratch)
    Falls back to an empty review when none match.
    """
    for resolver in _RESOLVERS:
        result = resolver(state)
        if result is not None:
            return result
    return build_presentation_review_updates([])


def _blocking_from_repaired_localized(
    localized: list[object],
    policy_version: str | None,
) -> bool:
    """Validate the REPAIRED localized slides so the deterministic trim counts."""
    slides = [slide for slide in localized if isinstance(slide, dict)]
    repaired = repair_localized_slides_sync(slides, policy_version=policy_version)
    report = validation_report_to_dict(
        validate_localized_slides(repaired, policy_version=policy_version)
    )
    return report.get("blocking") is True


def _blocking_from_drafts(
    slide_drafts: list[object],
    state: Mapping[str, object],
    policy_version: str | None,
) -> bool:
    """Build + repair + validate from raw drafts (the build path applies the trim)."""
    review = build_presentation_review_updates(
        [draft for draft in slide_drafts if isinstance(draft, dict)],
        translations_en=deserialize_translations_en(
            state.get(WORKFLOW_STATE_TRANSLATIONS_EN_KEY)
        ),
        policy_version=policy_version,
    )
    derived = review.get(WORKFLOW_STATE_PRESENTATION_VALIDATION_KEY)
    return isinstance(derived, dict) and derived.get("blocking") is True


def has_blocking_presentation_validation(state: Mapping[str, object]) -> bool:
    """Return True when presentation validation blocks content approval.

    Validates the REPAIRED slides (AE-0286): the deterministic copy trim is
    applied before the check, so over-budget drafts a model produced do not keep
    blocking approval once they have been trimmed to fit. Prefers the localized
    slides, then raw drafts, and only falls back to a stored validation when there
    is nothing to repair. Parse-failure markers on stored localized slides
    (AE-0309) surface here as blocking ``slide_parse_failed`` violations.
    """
    policy_version = _state_policy_version(state)
    localized = state.get(WORKFLOW_STATE_LOCALIZED_SLIDES_KEY)
    if isinstance(localized, list) and localized:
        return _blocking_from_repaired_localized(localized, policy_version)
    slide_drafts = state.get("slide_drafts")
    if isinstance(slide_drafts, list) and slide_drafts:
        return _blocking_from_drafts(slide_drafts, state, policy_version)
    validation = state.get(WORKFLOW_STATE_PRESENTATION_VALIDATION_KEY)
    return isinstance(validation, dict) and validation.get("blocking") is True


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
