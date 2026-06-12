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

# State field keys
_STATE_PROJECT_ID = "project_id"
_STATE_CURRENT_PHASE = "current_phase"
_STATE_PHASE_STATUS = "phase_status"
_STATE_RESEARCH_FINDINGS = "research_findings"
_STATE_OUTLINE = "outline"
_STATE_SLIDE_DRAFTS = "slide_drafts"
_STATE_IMAGE_ASSETS = "image_assets"
_STATE_DESIGN_APPLIED = "design_applied"
_STATE_PHASE_PROGRESS = "phase_progress"
_STATE_STATUS = "status"
_STATE_WORKFLOW_STATUS = "workflow_status"
_STATE_CAPTION = "caption"
_STATE_BLOG_MARKDOWN = "blog_markdown"
_STATE_LINKEDIN_POST_PT = "linkedin_post_pt"
_STATE_LINKEDIN_POST_EN = "linkedin_post_en"
_STATE_PERSONA_SCORES = "persona_scores"
_STATE_RUBRIC_SCORES = "rubric_scores"
_STATE_PHASE_FEEDBACK = "phase_feedback"
_STATE_REVISION_COUNT = "revision_count"
_STATE_PRESENTATION_POLICY_VERSION = "presentation_policy_version"

# Localized slide review keys
_REVIEW_SLIDE_INDEX = "slide_index"
_REVIEW_SLIDE_TYPE = "slide_type"
_REVIEW_PRESENTATION_PT = "presentation_pt"
_REVIEW_PRESENTATION_EN = "presentation_en"

# Validation report keys
_REPORT_VALIDATION_STATUS = "validation_status"
_REPORT_VALIDATED_AT = "validated_at"
_REPORT_BLOCKING = "blocking"
_REPORT_VIOLATIONS = "violations"

# Violation item keys
_VIOLATION_CODE = "code"
_VIOLATION_MESSAGE = "message"
_VIOLATION_SLIDE_INDEX = "slide_index"
_VIOLATION_LOCALE = "locale"
_VIOLATION_FIELD = "field"


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
    ("project_id", _string_field(_STATE_PROJECT_ID)),
    ("current_phase", _string_field(_STATE_CURRENT_PHASE)),
    ("phase_status", _string_field(_STATE_PHASE_STATUS)),
    ("research_findings", _list_field(_STATE_RESEARCH_FINDINGS)),
    ("outline", _list_field(_STATE_OUTLINE)),
    ("slide_drafts", _list_field(_STATE_SLIDE_DRAFTS)),
    ("image_assets", _list_field(_STATE_IMAGE_ASSETS)),
    ("design_applied", _bool_field(_STATE_DESIGN_APPLIED)),
    ("workflow_status", _string_field(_STATE_WORKFLOW_STATUS)),
    ("persona_scores", _dict_field(_STATE_PERSONA_SCORES)),
    ("caption", _string_field(_STATE_CAPTION)),
    ("blog_markdown", _string_field(_STATE_BLOG_MARKDOWN)),
    ("linkedin_post_pt", _string_field(_STATE_LINKEDIN_POST_PT)),
    ("linkedin_post_en", _string_field(_STATE_LINKEDIN_POST_EN)),
    ("rubric_scores", _dict_field(_STATE_RUBRIC_SCORES)),
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
    kwargs["localized_slides"] = _localized_slide_reviews(
        state.get("localized_slides"),
    )
    kwargs["presentation_validation"] = _presentation_validation_response(
        state.get("presentation_validation"),
    )
    kwargs["phase_feedback"] = _string_list_map(state.get(_STATE_PHASE_FEEDBACK))
    kwargs["revision_count"] = _int_map(state.get(_STATE_REVISION_COUNT))
    raw_progress = (
        phase_progress
        if phase_progress is not None
        else state.get(_STATE_PHASE_PROGRESS)
    )
    kwargs["phase_progress"] = raw_progress if isinstance(raw_progress, dict) else None
    kwargs["status"] = str(state.get(_STATE_STATUS, "draft"))
    kwargs["lock_version"] = lock_version
    raw_policy = state.get(_STATE_PRESENTATION_POLICY_VERSION)
    kwargs["presentation_policy_version"] = (
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
        slide_index = item.get(_REVIEW_SLIDE_INDEX)
        slide_type = item.get(_REVIEW_SLIDE_TYPE)
        presentation_pt = item.get(_REVIEW_PRESENTATION_PT)
        presentation_en = item.get(_REVIEW_PRESENTATION_EN)
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
    validation_status = raw.get(_REPORT_VALIDATION_STATUS)
    validated_at = raw.get(_REPORT_VALIDATED_AT)
    blocking = raw.get(_REPORT_BLOCKING)
    if (
        not isinstance(validation_status, str)
        or validated_at is None
        or not isinstance(blocking, bool)
    ):
        return None
    violations_raw = raw.get(_REPORT_VIOLATIONS)
    violations: list[SlideValidationViolationResponse] = []
    if isinstance(violations_raw, list):
        for item in violations_raw:
            if not isinstance(item, dict):
                continue
            code = item.get(_VIOLATION_CODE)
            message = item.get(_VIOLATION_MESSAGE)
            if not isinstance(code, str) or not isinstance(message, str):
                continue
            slide_index = item.get(_VIOLATION_SLIDE_INDEX)
            locale = item.get(_VIOLATION_LOCALE)
            field = item.get(_VIOLATION_FIELD)
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
