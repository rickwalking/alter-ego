"""Sanitize workflow outline and slide draft copy for API consumers and checkpoints."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass

from rag_backend.application.services.carousel.malformed_draft_builders import (
    _truncate_visible_copy,
)
from rag_backend.application.services.carousel.outline_normalize import (
    OUTLINE_FIELD_KEY_POINTS,
    OUTLINE_FIELD_TITLE,
    OUTLINE_FIELD_TLDR,
    normalize_editorial_outline,
)
from rag_backend.application.services.carousel.presentation_policy import (
    CarouselPresentationPolicy,
    load_presentation_policy,
)
from rag_backend.application.services.carousel.presentation_review import (
    build_presentation_review_updates,
)
from rag_backend.application.services.carousel.presentation_validation_fields import (
    body_budget_for_slide_type,
    heading_budget_for_slide_type,
)
from rag_backend.application.services.carousel.visible_copy_sanitize import (
    sanitize_visible_copy,
)
from rag_backend.domain.constants.carousel import LANGUAGE_PT
from rag_backend.domain.constants.presentation_policy import (
    DEFAULT_PRESENTATION_POLICY_VERSION,
)

_STATE_OUTLINE = "outline"
_STATE_SLIDE_DRAFTS = "slide_drafts"
_STATE_LOCALIZED_SLIDES = "localized_slides"
_STATE_POLICY_VERSION = "presentation_policy_version"
_PRESENTATION_PT_KEY = "presentation_pt"
_PRESENTATION_EN_KEY = "presentation_en"
_DRAFT_TEXT_KEY = "draft_text"
_SLIDE_TYPE_KEY = "slide_type"
_STRUCTURED_LIST_FIELDS = ("features", "summary_points", "actions")
_STRUCTURED_ITEM_TEXT_FIELDS = ("title", "body")
_PRESENTATION_TEXT_FIELDS = (
    "heading",
    "body",
    "tldr_strip",
    "creator_name",
    "creator_handle",
    "creator_website",
)
_BUDGET_KEY_SUMMARY_POINT_TITLE = "summary_point_title"
_BUDGET_KEY_SUMMARY_POINT_BODY = "summary_point_body"
_BUDGET_KEY_FEATURE_TITLE = "feature_title"
_BUDGET_KEY_FEATURE_BODY = "feature_body"
_BUDGET_KEY_CLOSING_ACTION_TITLE = "closing_action_title"
_BUDGET_KEY_CLOSING_ACTION_BODY = "closing_action_body"
_STRUCTURED_BUDGET_KEYS: dict[str, tuple[str, str]] = {
    "summary_points": (_BUDGET_KEY_SUMMARY_POINT_TITLE, _BUDGET_KEY_SUMMARY_POINT_BODY),
    "features": (_BUDGET_KEY_FEATURE_TITLE, _BUDGET_KEY_FEATURE_BODY),
    "actions": (_BUDGET_KEY_CLOSING_ACTION_TITLE, _BUDGET_KEY_CLOSING_ACTION_BODY),
}


def _sanitize_structured_items(
    items: object,
    *,
    list_field: str,
    policy: CarouselPresentationPolicy | None,
) -> list[dict[str, object]]:
    """Clean item copy; ``policy=None`` keeps the full text (no budget clamp)."""
    if not isinstance(items, list):
        return []
    title_key, body_key = _STRUCTURED_BUDGET_KEYS[list_field]
    title_budget = policy.copy_budgets.get(title_key) if policy else None
    body_budget = policy.copy_budgets.get(body_key) if policy else None
    sanitized: list[dict[str, object]] = []
    for item in items:
        if not isinstance(item, Mapping):
            continue
        row = dict(item)
        title = sanitize_visible_copy(row.get("title"))
        body = sanitize_visible_copy(row.get("body"))
        if title_budget is not None:
            title = _truncate_visible_copy(title, title_budget.max_characters)
        if body_budget is not None:
            body = _truncate_visible_copy(body, body_budget.max_characters)
        row["title"] = title
        row["body"] = body
        sanitized.append(row)
    return sanitized


def _sanitize_presentation_payload(
    payload: Mapping[str, object],
    *,
    policy: CarouselPresentationPolicy | None,
) -> dict[str, object]:
    """Clean payload copy; ``policy=None`` keeps the full text (no budget clamp)."""
    slide_type = str(payload.get(_SLIDE_TYPE_KEY) or payload.get("type") or "")
    result = dict(payload)
    heading_budget = (
        heading_budget_for_slide_type(slide_type, policy) if policy else None
    )
    body_budget = body_budget_for_slide_type(slide_type, policy) if policy else None

    for field in _PRESENTATION_TEXT_FIELDS:
        if field not in result:
            continue
        cleaned = sanitize_visible_copy(result.get(field))
        if field == "heading" and heading_budget is not None:
            cleaned = _truncate_visible_copy(cleaned, heading_budget.max_characters)
        if field == "body" and body_budget is not None:
            cleaned = _truncate_visible_copy(cleaned, body_budget.max_characters)
        result[field] = cleaned

    for list_field in _STRUCTURED_LIST_FIELDS:
        if list_field in result:
            result[list_field] = _sanitize_structured_items(
                result.get(list_field),
                list_field=list_field,
                policy=policy,
            )
    return result


def sanitize_outline_slides(
    raw_outline: list[dict[str, object]],
    *,
    locale: str = LANGUAGE_PT,
) -> list[dict[str, object]]:
    """Resolve localized outline strings to one locale and strip dash punctuation."""
    prepared: list[dict[str, object]] = []
    for item in raw_outline:
        if not isinstance(item, dict):
            continue
        slide = dict(item)
        slide[OUTLINE_FIELD_TITLE] = sanitize_visible_copy(
            slide.get(OUTLINE_FIELD_TITLE) or slide.get("heading"),
            locale=locale,
        )
        raw_points = slide.get(OUTLINE_FIELD_KEY_POINTS, [])
        key_points: list[str] = []
        if isinstance(raw_points, list):
            for point in raw_points:
                cleaned = sanitize_visible_copy(point, locale=locale)
                if cleaned:
                    key_points.append(cleaned)
        slide[OUTLINE_FIELD_KEY_POINTS] = key_points
        if OUTLINE_FIELD_TLDR in slide:
            slide[OUTLINE_FIELD_TLDR] = sanitize_visible_copy(
                slide.get(OUTLINE_FIELD_TLDR),
                locale=locale,
            )
        prepared.append(slide)
    return normalize_editorial_outline(prepared)


def sanitize_slide_drafts(
    slide_drafts: list[dict[str, object]],
    *,
    policy_version: str = DEFAULT_PRESENTATION_POLICY_VERSION,
    clamp_to_budgets: bool = True,
) -> list[dict[str, object]]:
    """Sanitize visible copy in slide drafts and fit text to presentation budgets.

    ``clamp_to_budgets=False`` (read paths) cleans the copy but never
    cuts it: the state GET clamped every draft to the v1 budgets, so the UI
    showed (and sent back) text cut mid-sentence.
    """
    policy = load_presentation_policy(policy_version) if clamp_to_budgets else None
    sanitized: list[dict[str, object]] = []
    for slide in slide_drafts:
        if not isinstance(slide, dict):
            continue
        updated = dict(slide)
        updated[OUTLINE_FIELD_TITLE] = sanitize_visible_copy(
            updated.get(OUTLINE_FIELD_TITLE) or updated.get("heading"),
        )
        presentation_pt = updated.get(_PRESENTATION_PT_KEY)
        presentation_en = updated.get(_PRESENTATION_EN_KEY)
        if isinstance(presentation_pt, Mapping):
            updated[_PRESENTATION_PT_KEY] = _sanitize_presentation_payload(
                presentation_pt,
                policy=policy,
            )
        if isinstance(presentation_en, Mapping):
            updated[_PRESENTATION_EN_KEY] = _sanitize_presentation_payload(
                presentation_en,
                policy=policy,
            )
        pt_body = updated.get(_PRESENTATION_PT_KEY)
        if isinstance(pt_body, Mapping):
            updated[_DRAFT_TEXT_KEY] = str(pt_body.get("body") or "")
        sanitized.append(updated)
    return sanitized


def _artifacts_changed(before: object, after: object) -> bool:
    return json.dumps(before, sort_keys=True, ensure_ascii=False) != json.dumps(
        after,
        sort_keys=True,
        ensure_ascii=False,
    )


@dataclass(frozen=True)
class SanitizeWorkflowStateCommand:
    """Inputs for sanitizing workflow outline and slide draft artifacts.

    Read paths set ``clamp_to_budgets`` to False to keep the stored copy whole.
    """

    state: Mapping[str, object]
    locale: str = LANGUAGE_PT
    policy_version: str = DEFAULT_PRESENTATION_POLICY_VERSION
    rebuild_validation: bool = True
    clamp_to_budgets: bool = True


def sanitize_workflow_state_artifacts(
    command: SanitizeWorkflowStateCommand,
) -> dict[str, object]:
    """Return workflow state with sanitized outline and slide draft copy."""
    updated = dict(command.state)
    raw_outline = updated.get(_STATE_OUTLINE)
    if isinstance(raw_outline, list):
        outline_dicts = [slide for slide in raw_outline if isinstance(slide, dict)]
        if outline_dicts:
            updated[_STATE_OUTLINE] = sanitize_outline_slides(
                outline_dicts,
                locale=command.locale,
            )

    raw_drafts = updated.get(_STATE_SLIDE_DRAFTS)
    if isinstance(raw_drafts, list):
        draft_dicts = [slide for slide in raw_drafts if isinstance(slide, dict)]
        if draft_dicts:
            updated[_STATE_SLIDE_DRAFTS] = sanitize_slide_drafts(
                draft_dicts,
                policy_version=command.policy_version,
                clamp_to_budgets=command.clamp_to_budgets,
            )
            if command.rebuild_validation:
                updated.update(
                    build_presentation_review_updates(
                        updated[_STATE_SLIDE_DRAFTS],
                        policy_version=command.policy_version,
                    )
                )
    return updated


def read_only_sanitize_command(
    state: Mapping[str, object],
) -> SanitizeWorkflowStateCommand:
    """The sanitize command of a READ path (the workflow state GET).

    The GET used the defaults: every read re-clamped the drafts to the v1
    budgets, rebuilt ``localized_slides`` and the validation report from those
    drafts (dropping repaired and hand-edited copy, EN falling back to PT) and
    relabelled the project v1. A read now keeps the stored localized slides,
    report and policy version; only a legacy state without localized slides
    gets them built, under the project's own policy version.
    """
    stored_version = state.get(_STATE_POLICY_VERSION)
    policy_version = (
        stored_version
        if isinstance(stored_version, str) and stored_version.strip()
        else DEFAULT_PRESENTATION_POLICY_VERSION
    )
    return SanitizeWorkflowStateCommand(
        state=state,
        policy_version=policy_version,
        rebuild_validation=not state.get(_STATE_LOCALIZED_SLIDES),
        clamp_to_budgets=False,
    )


def workflow_artifacts_differ(before: object, after: object) -> bool:
    """Return True when serialized workflow artifact payloads differ."""
    return _artifacts_changed(before, after)


def workflow_state_needs_sanitization(state: Mapping[str, object]) -> bool:
    """Return True when outline or slide drafts differ after sanitization."""
    sanitized = sanitize_workflow_state_artifacts(
        SanitizeWorkflowStateCommand(state=state, rebuild_validation=False),
    )
    outline_before = state.get(_STATE_OUTLINE)
    outline_after = sanitized.get(_STATE_OUTLINE)
    drafts_before = state.get(_STATE_SLIDE_DRAFTS)
    drafts_after = sanitized.get(_STATE_SLIDE_DRAFTS)
    return _artifacts_changed(outline_before, outline_after) or _artifacts_changed(
        drafts_before,
        drafts_after,
    )


__all__ = [
    "SanitizeWorkflowStateCommand",
    "read_only_sanitize_command",
    "sanitize_outline_slides",
    "sanitize_slide_drafts",
    "sanitize_workflow_state_artifacts",
    "workflow_artifacts_differ",
    "workflow_state_needs_sanitization",
]
