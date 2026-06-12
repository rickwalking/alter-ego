"""Apply reviewer slide-copy edits to workflow state with re-validation."""

from __future__ import annotations

from collections.abc import Mapping

from rag_backend.application.services.carousel.editorial_distribution_constants import (
    OUTLINE_LEGACY_BODY_KEY,
    OUTLINE_LEGACY_HEADING_KEY,
    SLIDE_DRAFT_TEXT_KEY,
    SLIDE_INDEX_KEY,
)
from rag_backend.application.services.carousel.localized_slide_builder import (
    PRESENTATION_EN_KEY,
    PRESENTATION_PT_KEY,
    as_dict,
    resolve_slide_index,
)
from rag_backend.application.services.carousel.outline_normalize import (
    OUTLINE_FIELD_TITLE,
)
from rag_backend.application.services.carousel.presentation_review import (
    WORKFLOW_STATE_LOCALIZED_SLIDES_KEY,
    WORKFLOW_STATE_PRESENTATION_POLICY_VERSION_KEY,
    WORKFLOW_STATE_PRESENTATION_VALIDATION_KEY,
    WORKFLOW_STATE_TRANSLATIONS_EN_KEY,
    deserialize_translations_en,
    resolve_presentation_review_from_state,
    serialize_translations_en,
    validate_localized_slides,
    validation_report_to_dict,
)


def merge_localized_slide_edits(
    current_slides: list[dict[str, object]],
    edited_slides: list[dict[str, object]],
) -> list[dict[str, object]]:
    """Merge edited PT/EN payloads into current localized slides by slide index."""
    edits_by_index: dict[int, dict[str, object]] = {}
    for edit in edited_slides:
        index = edit.get(SLIDE_INDEX_KEY)
        if isinstance(index, int):
            edits_by_index[index] = edit
    merged: list[dict[str, object]] = []
    for slide in current_slides:
        index = slide.get(SLIDE_INDEX_KEY)
        edit = edits_by_index.get(index) if isinstance(index, int) else None
        if edit is None:
            merged.append(dict(slide))
            continue
        updated = dict(slide)
        for locale_key in (PRESENTATION_PT_KEY, PRESENTATION_EN_KEY):
            payload = as_dict(edit.get(locale_key))
            if payload:
                updated[locale_key] = dict(payload)
        merged.append(updated)
    return merged


def _safe_str(value: object, default: str = "") -> str:
    """Return value as string if not None, else default."""
    if value is None:
        return default
    return str(value)


def _locale_heading_body(payload: Mapping[str, object] | None) -> tuple[str, str]:
    if payload is None:
        return "", ""
    heading = _safe_str(payload.get(OUTLINE_LEGACY_HEADING_KEY))
    body = _safe_str(payload.get(OUTLINE_LEGACY_BODY_KEY))
    return heading, body


def _apply_pt_edits(
    updated: dict[str, object],
    pt_payload: dict[str, object] | None,
) -> dict[str, object]:
    """Apply PT locale edits to the updated draft."""
    if pt_payload is None:
        heading = ""
        body = ""
    else:
        heading = _safe_str(pt_payload.get(OUTLINE_LEGACY_HEADING_KEY))
        body = _safe_str(pt_payload.get(OUTLINE_LEGACY_BODY_KEY))
    if heading:
        updated[OUTLINE_FIELD_TITLE] = heading
        updated[OUTLINE_LEGACY_HEADING_KEY] = heading
    if body:
        updated[SLIDE_DRAFT_TEXT_KEY] = body
        updated[OUTLINE_LEGACY_BODY_KEY] = body
    if pt_payload is not None and as_dict(updated.get(PRESENTATION_PT_KEY)) is not None:
        updated[PRESENTATION_PT_KEY] = dict(pt_payload)
    return updated


def _merge_one_draft(
    draft: dict[str, object],
    localized: dict[str, object],
) -> dict[str, object]:
    """Merge localized edits into a single draft."""
    updated = dict(draft)
    pt_payload = as_dict(localized.get(PRESENTATION_PT_KEY))
    updated = _apply_pt_edits(updated, pt_payload)
    en_payload = as_dict(localized.get(PRESENTATION_EN_KEY))
    if en_payload is not None and as_dict(updated.get(PRESENTATION_EN_KEY)) is not None:
        updated[PRESENTATION_EN_KEY] = dict(en_payload)
    return updated


def _apply_edits_to_drafts(
    slide_drafts: list[dict[str, object]],
    merged_by_index: dict[int, dict[str, object]],
) -> list[dict[str, object]]:
    updated_drafts: list[dict[str, object]] = []
    for position, draft in enumerate(slide_drafts):
        if not isinstance(draft, dict):
            continue
        index = resolve_slide_index(draft, position + 1)
        localized = merged_by_index.get(index)
        if localized is None:
            updated_drafts.append(dict(draft))
            continue
        updated_drafts.append(_merge_one_draft(draft, localized))
    return updated_drafts


def _apply_edits_to_translations(
    state: Mapping[str, object],
    merged_by_index: dict[int, dict[str, object]],
) -> dict[str, object]:
    existing = (
        deserialize_translations_en(state.get(WORKFLOW_STATE_TRANSLATIONS_EN_KEY)) or {}
    )
    result: dict[int, dict[str, object]] = {
        index: dict(payload) for index, payload in existing.items()
    }
    for index, localized in merged_by_index.items():
        heading, body = _locale_heading_body(
            as_dict(localized.get(PRESENTATION_EN_KEY))
        )
        if not heading and not body:
            continue
        entry = dict(result.get(index) or {})
        if heading:
            entry[OUTLINE_LEGACY_HEADING_KEY] = heading
        if body:
            entry[OUTLINE_LEGACY_BODY_KEY] = body
        result[index] = entry
    return serialize_translations_en(result)


def apply_localized_slide_edits(
    state: Mapping[str, object],
    edited_slides: list[dict[str, object]],
) -> dict[str, object]:
    """Apply reviewer edits and return re-validated workflow state updates."""
    review = resolve_presentation_review_from_state(state)
    current_raw = review.get(WORKFLOW_STATE_LOCALIZED_SLIDES_KEY)
    current = [slide for slide in (current_raw or []) if isinstance(slide, dict)]
    policy_version_raw = review.get(WORKFLOW_STATE_PRESENTATION_POLICY_VERSION_KEY)
    policy_version = str(policy_version_raw) if policy_version_raw else None
    merged = merge_localized_slide_edits(current, edited_slides)
    merged_by_index: dict[int, dict[str, object]] = {}
    for slide in merged:
        index = slide.get(SLIDE_INDEX_KEY)
        if isinstance(index, int):
            merged_by_index[index] = slide
    report = validate_localized_slides(merged, policy_version=policy_version)
    updates: dict[str, object] = {
        WORKFLOW_STATE_LOCALIZED_SLIDES_KEY: merged,
        WORKFLOW_STATE_PRESENTATION_VALIDATION_KEY: validation_report_to_dict(report),
    }
    if policy_version:
        updates[WORKFLOW_STATE_PRESENTATION_POLICY_VERSION_KEY] = policy_version
    slide_drafts = state.get("slide_drafts")
    if isinstance(slide_drafts, list) and slide_drafts:
        updates["slide_drafts"] = _apply_edits_to_drafts(slide_drafts, merged_by_index)
    translations = _apply_edits_to_translations(state, merged_by_index)
    if translations:
        updates[WORKFLOW_STATE_TRANSLATIONS_EN_KEY] = translations
    return updates


def edited_slides_block_approval(
    state: Mapping[str, object],
    edited_slides: list[dict[str, object]],
) -> bool:
    """Return True when edited slides still carry blocking violations."""
    updates = apply_localized_slide_edits(state, edited_slides)
    validation = updates.get(WORKFLOW_STATE_PRESENTATION_VALIDATION_KEY)
    if not isinstance(validation, dict):
        return False
    return validation.get("blocking") is True


__all__ = [
    "apply_localized_slide_edits",
    "edited_slides_block_approval",
    "merge_localized_slide_edits",
]
