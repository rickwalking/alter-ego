"""Response building and mapping helpers for editorial workflow HTTP routes."""

from __future__ import annotations

from rag_backend.api.schemas.carousel_workflow import (
    EditorialWorkflowStateResponse,
    LocalizedSlideReview,
    SlideValidationReportResponse,
    SlideValidationViolationResponse,
)
from rag_backend.application.services.carousel.presentation_review import (
    WORKFLOW_STATE_LOCALIZED_SLIDES_KEY,
    WORKFLOW_STATE_PRESENTATION_POLICY_VERSION_KEY,
    WORKFLOW_STATE_PRESENTATION_VALIDATION_KEY,
    resolve_presentation_review_from_state,
)
from rag_backend.domain.constants.carousel_workflow import (
    CAROUSEL_EDITORIAL_WORKFLOW_STATUS_DRAFT,
)


def build_workflow_state_response(
    state: dict[str, object],
    *,
    phase_progress: dict[str, object] | None = None,
    lock_version: int = 1,
) -> EditorialWorkflowStateResponse:
    """Map workflow state dict to API response model."""
    raw_progress = (
        phase_progress if phase_progress is not None else state.get("phase_progress")
    )
    progress = raw_progress if isinstance(raw_progress, dict) else None
    review = resolve_presentation_review_from_state(state)
    localized_raw = review.get(WORKFLOW_STATE_LOCALIZED_SLIDES_KEY)
    validation_raw = review.get(WORKFLOW_STATE_PRESENTATION_VALIDATION_KEY)
    localized_slides = _localized_slide_reviews(localized_raw)
    presentation_validation = _presentation_validation_response(validation_raw)
    policy_version = review.get(WORKFLOW_STATE_PRESENTATION_POLICY_VERSION_KEY)
    return EditorialWorkflowStateResponse(
        project_id=str(state.get("project_id", "")),
        current_phase=str(state.get("current_phase", "")),
        phase_status=str(state.get("phase_status", "")),
        research_findings=list(state.get("research_findings") or []),
        outline=list(state.get("outline") or []),
        slide_drafts=list(state.get("slide_drafts") or []),
        image_assets=[str(asset) for asset in (state.get("image_assets") or [])],
        design_applied=bool(state.get("design_applied")),
        phase_progress=progress,
        status=str(state.get("status", CAROUSEL_EDITORIAL_WORKFLOW_STATUS_DRAFT)),
        lock_version=lock_version,
        workflow_status=str(state.get("workflow_status", "")),
        persona_scores=(
            dict(state.get("persona_scores"))
            if isinstance(state.get("persona_scores"), dict)
            else {}
        ),
        caption=str(state.get("caption")) if state.get("caption") else None,
        blog_markdown=(
            str(state.get("blog_markdown")) if state.get("blog_markdown") else None
        ),
        linkedin_post_pt=(
            str(state.get("linkedin_post_pt"))
            if state.get("linkedin_post_pt")
            else None
        ),
        linkedin_post_en=(
            str(state.get("linkedin_post_en"))
            if state.get("linkedin_post_en")
            else None
        ),
        rubric_scores=(
            dict(state.get("rubric_scores"))
            if isinstance(state.get("rubric_scores"), dict)
            else {}
        ),
        phase_feedback=_string_list_map(state.get("phase_feedback")),
        revision_count=_int_map(state.get("revision_count")),
        presentation_policy_version=(
            str(policy_version) if isinstance(policy_version, str) else None
        ),
        localized_slides=localized_slides,
        presentation_validation=presentation_validation,
    )


def _localized_slide_reviews(raw: object) -> list[LocalizedSlideReview]:
    if not isinstance(raw, list):
        return []
    reviews: list[LocalizedSlideReview] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        slide_index = item.get("slide_index")
        slide_type = item.get("slide_type")
        presentation_pt = item.get("presentation_pt")
        presentation_en = item.get("presentation_en")
        if not isinstance(slide_index, int) or not isinstance(slide_type, str):
            continue
        reviews.append(
            LocalizedSlideReview(
                slide_index=slide_index,
                slide_type=slide_type,
                presentation_pt=(
                    dict(presentation_pt)
                    if isinstance(presentation_pt, dict)
                    else {}
                ),
                presentation_en=(
                    dict(presentation_en)
                    if isinstance(presentation_en, dict)
                    else {}
                ),
            )
        )
    return reviews


def _presentation_validation_response(
    raw: object,
) -> SlideValidationReportResponse | None:
    if not isinstance(raw, dict):
        return None
    validation_status = raw.get("validation_status")
    validated_at = raw.get("validated_at")
    blocking = raw.get("blocking")
    if (
        not isinstance(validation_status, str)
        or validated_at is None
        or not isinstance(blocking, bool)
    ):
        return None
    violations_raw = raw.get("violations")
    violations: list[SlideValidationViolationResponse] = []
    if isinstance(violations_raw, list):
        for item in violations_raw:
            if not isinstance(item, dict):
                continue
            code = item.get("code")
            message = item.get("message")
            if not isinstance(code, str) or not isinstance(message, str):
                continue
            slide_index = item.get("slide_index")
            locale = item.get("locale")
            field = item.get("field")
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
