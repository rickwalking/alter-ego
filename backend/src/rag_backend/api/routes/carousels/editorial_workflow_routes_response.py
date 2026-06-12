"""Response building and mapping helpers for editorial workflow HTTP routes."""

from __future__ import annotations

from collections.abc import Callable

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
    STATE_FIELD_WORKFLOW_STATUS,
)

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
            try:
                return int(val)
            except ValueError:
                return 0
        return 0

    return extractor


def _optional_field(key: str) -> Callable[[dict[str, object]], object | None]:
    """Build an extractor that returns the value or ``None`` for *key*."""

    def extractor(state: dict[str, object]) -> object | None:
        val = state.get(key)
        return val if val is not None else None

    return extractor


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


# ── Field mapping ─────────────────────────────────────────────────────────────

_FIELD_MAPPING: list[tuple[str, Callable[[dict[str, object]], object]]] = [
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
]


# ── Public builder ────────────────────────────────────────────────────────────


def build_workflow_state_response(
    state: dict[str, object],
    *,
    phase_progress: dict[str, object] | None = None,
    lock_version: int = 1,
) -> EditorialWorkflowStateResponse:
    """Build a typed API response from a raw workflow state dictionary."""
    state = sanitize_workflow_state_artifacts(
        SanitizeWorkflowStateCommand(state=state),
    )
    kwargs: dict[str, object] = {}
    for field_name, extractor in _FIELD_MAPPING:
        kwargs[field_name] = extractor(state)
    kwargs[STATE_FIELD_LOCALIZED_SLIDES] = _localized_slide_reviews(
        state.get(STATE_FIELD_LOCALIZED_SLIDES),
    )
    kwargs[STATE_FIELD_PRESENTATION_VALIDATION] = _presentation_validation_response(
        state.get(STATE_FIELD_PRESENTATION_VALIDATION),
    )
    kwargs[STATE_FIELD_PHASE_FEEDBACK] = _string_list_map(
        state.get(STATE_FIELD_PHASE_FEEDBACK)
    )
    kwargs[STATE_FIELD_REVISION_COUNT] = _int_map(state.get(STATE_FIELD_REVISION_COUNT))
    raw_progress = (
        phase_progress
        if phase_progress is not None
        else state.get(STATE_FIELD_PHASE_PROGRESS)
    )
    kwargs[STATE_FIELD_PHASE_PROGRESS] = (
        raw_progress if isinstance(raw_progress, dict) else None
    )
    kwargs[STATE_FIELD_STATUS] = str(
        state.get(STATE_FIELD_STATUS, STATE_DEFAULT_STATUS)
    )
    kwargs[STATE_FIELD_LOCK_VERSION] = lock_version
    raw_policy = state.get(STATE_FIELD_PRESENTATION_POLICY_VERSION)
    kwargs[STATE_FIELD_PRESENTATION_POLICY_VERSION] = (
        str(raw_policy) if raw_policy is not None else None
    )
    return EditorialWorkflowStateResponse(**kwargs)


# ── Helper builders ───────────────────────────────────────────────────────────


def _localized_slide_reviews(raw: object) -> list[LocalizedSlideReview]:
    if not isinstance(raw, list):
        return []
    reviews: list[LocalizedSlideReview] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        slide_index = item.get(STATE_FIELD_SLIDE_INDEX)
        slide_type = item.get(STATE_FIELD_SLIDE_TYPE)
        presentation_pt = item.get(STATE_FIELD_PRESENTATION_PT)
        presentation_en = item.get(STATE_FIELD_PRESENTATION_EN)
        if not isinstance(slide_index, int) or not isinstance(slide_type, str):
            continue
        reviews.append(
            LocalizedSlideReview(
                slide_index=slide_index,
                slide_type=slide_type,
                presentation_pt=(
                    dict(presentation_pt) if isinstance(presentation_pt, dict) else {}
                ),
                presentation_en=(
                    dict(presentation_en) if isinstance(presentation_en, dict) else {}
                ),
            )
        )
    return reviews


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
    violations_raw = raw.get(STATE_FIELD_VIOLATIONS)
    violations: list[SlideValidationViolationResponse] = []
    if isinstance(violations_raw, list):
        for item in violations_raw:
            if not isinstance(item, dict):
                continue
            code = item.get(STATE_FIELD_VIOLATION_CODE)
            message = item.get(STATE_FIELD_VIOLATION_MESSAGE)
            if not isinstance(code, str) or not isinstance(message, str):
                continue
            slide_index = item.get(STATE_FIELD_SLIDE_INDEX)
            locale = item.get(STATE_FIELD_VIOLATION_LOCALE)
            field = item.get(STATE_FIELD_VIOLATION_FIELD)
            violations.append(
                SlideValidationViolationResponse(
                    code=code,
                    message=message,
                    slide_index=slide_index if isinstance(slide_index, int) else None,
                    locale=locale if isinstance(locale, str) else None,
                    field=field if isinstance(field, str) else None,
                )
            )
    return SlideValidationReportResponse(
        validation_status=validation_status,
        validated_at=str(validated_at),
        blocking=blocking,
        violations=violations,
    )


def _string_list_map(raw: object) -> dict[str, list[str]]:
    if not isinstance(raw, dict):
        return {}
    result: dict[str, list[str]] = {}
    for key, value in raw.items():
        if isinstance(value, list):
            result[str(key)] = [str(item) for item in value]
    return result


def _int_map(raw: object) -> dict[str, int]:
    if not isinstance(raw, dict):
        return {}
    result: dict[str, int] = {}
    for key, value in raw.items():
        if isinstance(value, int):
            result[str(key)] = value
        elif isinstance(value, str) and value.isdigit():
            result[str(key)] = int(value)
    return result


__all__ = [
    "build_workflow_state_response",
]
