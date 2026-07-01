"""Sanitization helpers for editorial workflow HTTP routes."""

from __future__ import annotations

from rag_backend.agents.input_sanitizer import (
    sanitize_display_input,
    sanitize_llm_input,
)
from rag_backend.api.schemas.carousel_workflow import (
    EditorialStructuredFeedback,
    LocalizedSlideReview,
)
from rag_backend.domain.constants.carousel_workflow import (
    FINAL_REVIEW_SEND_BACK_PHASES,
    STRUCTURED_FEEDBACK_EDITED_SLIDES_KEY,
    STRUCTURED_FEEDBACK_TARGET_PHASE_KEY,
)


def _sanitize_payload_strings(value: object) -> object:
    # AE-0289: edited slide copy is FINAL published content, so preserve case
    # (sanitize_display_input) instead of lowercasing it (sanitize_llm_input),
    # which corrupted headings and broke heading_not_sentence_case_en validation.
    if isinstance(value, str):
        return sanitize_display_input(value)
    if isinstance(value, list):
        return [_sanitize_payload_strings(item) for item in value]
    if isinstance(value, dict):
        return {
            str(key): _sanitize_payload_strings(item) for key, item in value.items()
        }
    return value


def _sanitize_edited_slides(
    edited_slides: list[LocalizedSlideReview],
) -> list[dict[str, object]]:
    sanitized: list[dict[str, object]] = []
    for slide in edited_slides:
        payload = slide.model_dump()
        sanitized.append({
            "slide_index": payload["slide_index"],
            "slide_type": sanitize_llm_input(str(payload["slide_type"])),
            "presentation_pt": _sanitize_payload_strings(payload["presentation_pt"]),
            "presentation_en": _sanitize_payload_strings(payload["presentation_en"]),
        })
    return sanitized


def sanitize_structured_feedback(
    feedback: EditorialStructuredFeedback | None,
) -> dict[str, object] | None:
    """Sanitize optional structured feedback from resume requests."""
    if feedback is None:
        return None
    raw = feedback.model_dump(exclude_none=True)
    sanitized: dict[str, object] = {}
    target = raw.get(STRUCTURED_FEEDBACK_TARGET_PHASE_KEY)
    if isinstance(target, str) and target in FINAL_REVIEW_SEND_BACK_PHASES:
        sanitized[STRUCTURED_FEEDBACK_TARGET_PHASE_KEY] = target
    edited = raw.get("edited_text")
    if isinstance(edited, str):
        safe_edited = sanitize_llm_input(edited)
        if safe_edited:
            sanitized["edited_text"] = safe_edited
    if feedback.edited_localized_slides:
        sanitized[STRUCTURED_FEEDBACK_EDITED_SLIDES_KEY] = _sanitize_edited_slides(
            feedback.edited_localized_slides
        )
    return sanitized or None


__all__ = [
    "sanitize_structured_feedback",
]
