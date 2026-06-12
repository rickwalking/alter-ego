"""Response building and mapping helpers for editorial workflow HTTP routes.

Implements a Field Descriptor Mapping pattern (lightweight Builder): each
response field is described by a ``(field_name, extractor)`` pair in
``_FIELD_MAPPING``. Extractors are pure functions over the sanitized workflow
state dictionary, keeping the public builder declarative and trivial to extend.
"""

from __future__ import annotations

import warnings
from collections.abc import Callable

from typing_extensions import deprecated

from rag_backend.api.schemas.carousel_workflow import (
    EditorialWorkflowStateResponse,
    LocalizedSlideReview,
    SlideValidationReportResponse,
    SlideValidationViolationResponse,
)
from rag_backend.application.services.carousel.workflow_state_sanitize import (
    SanitizeWorkflowStateCommand,
    sanitize_workflow_state_artifacts,
)
from rag_backend.domain.constants.workflow_state_fields import (
    STATE_DEFAULT_STATUS,
    STATE_FIELD_BLOCKING,
    STATE_FIELD_BLOG_MARKDOWN,
    STATE_FIELD_CAPTION,
    STATE_FIELD_CURRENT_PHASE,
    STATE_FIELD_DESIGN_APPLIED,
    STATE_FIELD_ERROR_MESSAGE,
    STATE_FIELD_IMAGE_ASSETS,
    STATE_FIELD_LINKEDIN_POST_EN,
    STATE_FIELD_LINKEDIN_POST_PT,
    STATE_FIELD_LOCALIZED_SLIDES,
    STATE_FIELD_LOCK_VERSION,
    STATE_FIELD_OUTLINE,
    STATE_FIELD_PERSONA_SCORES,
    STATE_FIELD_PHASE_FEEDBACK,
    STATE_FIELD_PHASE_PROGRESS,
    STATE_FIELD_PHASE_STATUS,
    STATE_FIELD_PRESENTATION_EN,
    STATE_FIELD_PRESENTATION_POLICY_VERSION,
    STATE_FIELD_PRESENTATION_PT,
    STATE_FIELD_PRESENTATION_VALIDATION,
    STATE_FIELD_PROJECT_ID,
    STATE_FIELD_RESEARCH_FINDINGS,
    STATE_FIELD_REVISION_COUNT,
    STATE_FIELD_RUBRIC_SCORES,
    STATE_FIELD_SLIDE_DRAFTS,
    STATE_FIELD_SLIDE_INDEX,
    STATE_FIELD_SLIDE_TYPE,
    STATE_FIELD_STATUS,
    STATE_FIELD_VALIDATED_AT,
    STATE_FIELD_VALIDATION_STATUS,
    STATE_FIELD_VIOLATION_CODE,
    STATE_FIELD_VIOLATION_FIELD,
    STATE_FIELD_VIOLATION_LOCALE,
    STATE_FIELD_VIOLATION_MESSAGE,
    STATE_FIELD_VIOLATIONS,
    STATE_FIELD_WORKFLOW_ERROR,
    STATE_FIELD_WORKFLOW_STATUS,
)

# Deprecation message for the legacy ``build_workflow_state_response`` name.
_DEPRECATION_MESSAGE = (
    "build_workflow_state_response is deprecated; "
    "use build_editorial_workflow_state_response instead."
)

# Extractor signature: a pure function from sanitized state to a response value.
StateExtractor = Callable[[dict[str, object]], object]


# ── Field extractors ──────────────────────────────────────────────────────────


def _string_field(key: str) -> Callable[[dict[str, object]], str]:
    """Build an extractor that returns the string value for *key*."""

    def extractor(state: dict[str, object]) -> str:
        return str(state.get(key) or "")

    return extractor


def _list_field(key: str) -> Callable[[dict[str, object]], list[object]]:
    """Build an extractor that returns the list value for *key*."""

    def extractor(state: dict[str, object]) -> list[object]:
        val = state.get(key)
        return list(val) if isinstance(val, list) else []

    return extractor


def _int_field(key: str) -> Callable[[dict[str, object]], int]:
    """Build an extractor that returns the integer value for *key*."""

    def extractor(state: dict[str, object]) -> int:
        val = state.get(key)
        if isinstance(val, int):
            return val
        if isinstance(val, str) and val.strip():
            return _coerce_int_str(val)
        return 0

    return extractor


def _coerce_int_str(val: str) -> int:
    """Coerce a numeric string to ``int``, defaulting to ``0`` on failure."""
    try:
        return int(val)
    except ValueError:
        return 0


def _bool_field(key: str) -> Callable[[dict[str, object]], bool]:
    """Build an extractor that returns the boolean value for *key*."""

    def extractor(state: dict[str, object]) -> bool:
        return bool(state.get(key))

    return extractor


def _dict_field(key: str) -> Callable[[dict[str, object]], dict[str, object]]:
    """Build an extractor that returns the dict value or ``{}`` for *key*."""

    def extractor(state: dict[str, object]) -> dict[str, object]:
        val = state.get(key)
        return dict(val) if isinstance(val, dict) else {}

    return extractor


def _string_list_map_field(
    key: str,
) -> Callable[[dict[str, object]], dict[str, list[str]]]:
    """Build an extractor mapping *key* to a ``{str: [str, ...]}`` dict."""

    def extractor(state: dict[str, object]) -> dict[str, list[str]]:
        raw = state.get(key)
        if not isinstance(raw, dict):
            return {}
        return {
            str(name): [str(item) for item in value]
            for name, value in raw.items()
            if isinstance(value, list)
        }

    return extractor


def _int_map_field(key: str) -> Callable[[dict[str, object]], dict[str, int]]:
    """Build an extractor mapping *key* to a ``{str: int}`` dict."""

    def extractor(state: dict[str, object]) -> dict[str, int]:
        raw = state.get(key)
        if not isinstance(raw, dict):
            return {}
        result: dict[str, int] = {}
        for name, value in raw.items():
            if isinstance(value, int):
                result[str(name)] = value
            elif isinstance(value, str) and value.isdigit():
                result[str(name)] = int(value)
        return result

    return extractor


def _localized_reviews_field(
    key: str,
) -> Callable[[dict[str, object]], list[LocalizedSlideReview]]:
    """Build an extractor returning localized slide reviews for *key*."""

    def extractor(state: dict[str, object]) -> list[LocalizedSlideReview]:
        return _localized_slide_reviews(state.get(key))

    return extractor


def _validation_field(
    key: str,
) -> Callable[[dict[str, object]], SlideValidationReportResponse | None]:
    """Build an extractor returning the validation report for *key*."""

    def extractor(state: dict[str, object]) -> SlideValidationReportResponse | None:
        return _presentation_validation_response(state.get(key))

    return extractor


def _status_field(state: dict[str, object]) -> str:
    """Extract the workflow status, defaulting to the draft status."""
    return str(state.get(STATE_FIELD_STATUS, STATE_DEFAULT_STATUS))


def _policy_version_field(state: dict[str, object]) -> str | None:
    """Extract the presentation policy version or ``None`` when absent."""
    raw = state.get(STATE_FIELD_PRESENTATION_POLICY_VERSION)
    return str(raw) if raw is not None else None


def _error_message_field(state: dict[str, object]) -> str | None:
    """Extract the persisted failure message (AE-0009).

    Additive, optional response field. Raw state stores the message under
    ``workflow_error``; an explicit ``error_message`` key is also honored as a
    fallback. Returns ``None`` (field omitted by default) when no error is set.
    """
    raw = state.get(STATE_FIELD_WORKFLOW_ERROR) or state.get(STATE_FIELD_ERROR_MESSAGE)
    return str(raw) if raw else None


# ── Field mapping ─────────────────────────────────────────────────────────────

_FIELD_MAPPING: list[tuple[str, StateExtractor]] = [
    (STATE_FIELD_PROJECT_ID, _string_field(STATE_FIELD_PROJECT_ID)),
    (STATE_FIELD_CURRENT_PHASE, _string_field(STATE_FIELD_CURRENT_PHASE)),
    (STATE_FIELD_PHASE_STATUS, _string_field(STATE_FIELD_PHASE_STATUS)),
    (STATE_FIELD_RESEARCH_FINDINGS, _list_field(STATE_FIELD_RESEARCH_FINDINGS)),
    (STATE_FIELD_OUTLINE, _list_field(STATE_FIELD_OUTLINE)),
    (STATE_FIELD_SLIDE_DRAFTS, _list_field(STATE_FIELD_SLIDE_DRAFTS)),
    (STATE_FIELD_IMAGE_ASSETS, _list_field(STATE_FIELD_IMAGE_ASSETS)),
    (STATE_FIELD_DESIGN_APPLIED, _bool_field(STATE_FIELD_DESIGN_APPLIED)),
    (STATE_FIELD_WORKFLOW_STATUS, _string_field(STATE_FIELD_WORKFLOW_STATUS)),
    (STATE_FIELD_PERSONA_SCORES, _dict_field(STATE_FIELD_PERSONA_SCORES)),
    (STATE_FIELD_CAPTION, _string_field(STATE_FIELD_CAPTION)),
    (STATE_FIELD_BLOG_MARKDOWN, _string_field(STATE_FIELD_BLOG_MARKDOWN)),
    (STATE_FIELD_LINKEDIN_POST_PT, _string_field(STATE_FIELD_LINKEDIN_POST_PT)),
    (STATE_FIELD_LINKEDIN_POST_EN, _string_field(STATE_FIELD_LINKEDIN_POST_EN)),
    (STATE_FIELD_RUBRIC_SCORES, _dict_field(STATE_FIELD_RUBRIC_SCORES)),
    (STATE_FIELD_PHASE_FEEDBACK, _string_list_map_field(STATE_FIELD_PHASE_FEEDBACK)),
    (STATE_FIELD_REVISION_COUNT, _int_map_field(STATE_FIELD_REVISION_COUNT)),
    (
        STATE_FIELD_LOCALIZED_SLIDES,
        _localized_reviews_field(STATE_FIELD_LOCALIZED_SLIDES),
    ),
    (
        STATE_FIELD_PRESENTATION_VALIDATION,
        _validation_field(STATE_FIELD_PRESENTATION_VALIDATION),
    ),
    (STATE_FIELD_STATUS, _status_field),
    (STATE_FIELD_PRESENTATION_POLICY_VERSION, _policy_version_field),
    (STATE_FIELD_ERROR_MESSAGE, _error_message_field),
]


# ── Public builder ────────────────────────────────────────────────────────────


def build_editorial_workflow_state_response(
    state: dict[str, object],
    *,
    phase_progress: dict[str, object] | None = None,
    lock_version: int = 1,
) -> EditorialWorkflowStateResponse:
    """Build a typed API response from a raw workflow state dictionary."""
    command = SanitizeWorkflowStateCommand(state=state)
    sanitized = sanitize_workflow_state_artifacts(command)
    kwargs: dict[str, object] = {name: get(sanitized) for name, get in _FIELD_MAPPING}
    kwargs[STATE_FIELD_PHASE_PROGRESS] = _resolve_phase_progress(
        sanitized, phase_progress
    )
    kwargs[STATE_FIELD_LOCK_VERSION] = lock_version
    return EditorialWorkflowStateResponse(**kwargs)


def _resolve_phase_progress(
    state: dict[str, object],
    override: dict[str, object] | None,
) -> dict[str, object] | None:
    """Choose the explicit phase-progress override or the state value."""
    raw = override if override is not None else state.get(STATE_FIELD_PHASE_PROGRESS)
    return raw if isinstance(raw, dict) else None


@deprecated(_DEPRECATION_MESSAGE)
def build_workflow_state_response(
    state: dict[str, object],
    *,
    phase_progress: dict[str, object] | None = None,
    lock_version: int = 1,
) -> EditorialWorkflowStateResponse:
    """Deprecated alias for :func:`build_editorial_workflow_state_response`.

    Retained for one migration sprint (AE-0050 window) so existing callers and
    tests keep working. Removed before the editorial HTTP adapter (Phase 4)
    lifts the response mapping unit.
    """
    warnings.warn(_DEPRECATION_MESSAGE, DeprecationWarning, stacklevel=2)
    return build_editorial_workflow_state_response(
        state,
        phase_progress=phase_progress,
        lock_version=lock_version,
    )


# ── Helper builders ───────────────────────────────────────────────────────────


def _localized_slide_reviews(raw: object) -> list[LocalizedSlideReview]:
    if not isinstance(raw, list):
        return []
    reviews: list[LocalizedSlideReview] = []
    for item in raw:
        review = _localized_slide_review(item)
        if review is not None:
            reviews.append(review)
    return reviews


def _localized_slide_review(item: object) -> LocalizedSlideReview | None:
    if not isinstance(item, dict):
        return None
    slide_index = item.get(STATE_FIELD_SLIDE_INDEX)
    slide_type = item.get(STATE_FIELD_SLIDE_TYPE)
    if not isinstance(slide_index, int) or not isinstance(slide_type, str):
        return None
    return LocalizedSlideReview(
        slide_index=slide_index,
        slide_type=slide_type,
        presentation_pt=_as_dict(item.get(STATE_FIELD_PRESENTATION_PT)),
        presentation_en=_as_dict(item.get(STATE_FIELD_PRESENTATION_EN)),
    )


def _as_dict(value: object) -> dict[str, object]:
    return dict(value) if isinstance(value, dict) else {}


def _presentation_validation_response(
    raw: object,
) -> SlideValidationReportResponse | None:
    if not isinstance(raw, dict):
        return None
    validation_status = raw.get(STATE_FIELD_VALIDATION_STATUS)
    validated_at = raw.get(STATE_FIELD_VALIDATED_AT)
    blocking = raw.get(STATE_FIELD_BLOCKING)
    if (
        not isinstance(validation_status, str)
        or validated_at is None
        or not isinstance(blocking, bool)
    ):
        return None
    return SlideValidationReportResponse(
        validation_status=validation_status,
        validated_at=str(validated_at),
        blocking=blocking,
        violations=_validation_violations(raw.get(STATE_FIELD_VIOLATIONS)),
    )


def _validation_violations(raw: object) -> list[SlideValidationViolationResponse]:
    if not isinstance(raw, list):
        return []
    violations: list[SlideValidationViolationResponse] = []
    for item in raw:
        violation = _validation_violation(item)
        if violation is not None:
            violations.append(violation)
    return violations


def _validation_violation(item: object) -> SlideValidationViolationResponse | None:
    if not isinstance(item, dict):
        return None
    code = item.get(STATE_FIELD_VIOLATION_CODE)
    message = item.get(STATE_FIELD_VIOLATION_MESSAGE)
    if not isinstance(code, str) or not isinstance(message, str):
        return None
    slide_index = item.get(STATE_FIELD_SLIDE_INDEX)
    locale = item.get(STATE_FIELD_VIOLATION_LOCALE)
    field = item.get(STATE_FIELD_VIOLATION_FIELD)
    return SlideValidationViolationResponse(
        code=code,
        message=message,
        slide_index=slide_index if isinstance(slide_index, int) else None,
        locale=locale if isinstance(locale, str) else None,
        field=field if isinstance(field, str) else None,
    )


__all__ = [
    "build_editorial_workflow_state_response",
    "build_workflow_state_response",
]
