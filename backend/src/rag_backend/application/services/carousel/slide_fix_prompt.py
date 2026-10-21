"""The slide-fix prompt and the model answer it expects.

The prompt itself lives in ``agents/prompts/carousel/v1/slide_fix.yaml``. The
answer is strict JSON ``{pt:{heading,body}, en:{heading,body}}``, read
fence-aware with ``parse_object_text``; item lists the model returns are
merged by position only when they keep the item count.

Summary and closing slides have no body budget in the contract, so a default body limit
applies.
"""

from __future__ import annotations

import copy
import json
from collections.abc import Mapping

from rag_backend.application.services.carousel.draft_blob_text import (
    parse_object_text,
)
from rag_backend.application.services.carousel.localized_slide_builder import (
    PRESENTATION_EN_KEY,
    PRESENTATION_PT_KEY,
    as_dict,
)
from rag_backend.application.services.carousel.owner_autofix_paths import ITEM_LISTS
from rag_backend.application.services.carousel.presentation_content_rules import (
    slide_type_of,
)
from rag_backend.application.services.carousel.presentation_policy_types import (
    CarouselPresentationPolicy,
)
from rag_backend.application.services.carousel.presentation_rubric import (
    RUBRIC_AUDIENCE_CONTENT,
    render_quality_rubric,
)
from rag_backend.application.services.carousel.presentation_validation_fields import (
    body_budget_for_slide_type,
    heading_budget_for_slide_type,
)
from rag_backend.application.services.carousel.slide_fix_types import (
    SlideIssue,
    SlideTarget,
)
from rag_backend.application.services.carousel_template.prompts import (
    build_slide_fix_prompt,
)
from rag_backend.domain.constants.carousel import LANGUAGE_EN, LANGUAGE_PT
from rag_backend.domain.constants.slide_fix import (
    ISSUE_LINE,
    VAR_BODY_MAX,
    VAR_HEADING_MAX,
    VAR_ISSUES,
    VAR_QUALITY_RUBRIC,
    VAR_ROLE,
    VAR_SLIDE_INDEX,
    VAR_SLIDE_JSON,
    VAR_SLIDE_TYPE,
    VAR_STYLE_GUIDE,
    VAR_VOICE_FLOOR,
)

_HEADING = "heading"
_BODY = "body"
_TITLE = "title"
_COPY_KEYS = (_HEADING, _BODY)
_ITEM_KEYS = (_TITLE, _BODY)
_DEFAULT_BODY_MAX = 200
_LOCALES: tuple[tuple[str, str], ...] = (
    (LANGUAGE_PT, PRESENTATION_PT_KEY),
    (LANGUAGE_EN, PRESENTATION_EN_KEY),
)


def _visible(payload: Mapping[str, object]) -> dict[str, object]:
    shown: dict[str, object] = {key: payload.get(key) or "" for key in _COPY_KEYS}
    for list_field in ITEM_LISTS:
        items = payload.get(list_field)
        if isinstance(items, list) and items:
            shown[list_field] = [
                {key: item.get(key) or "" for key in _ITEM_KEYS}
                for item in items
                if isinstance(item, Mapping)
            ]
    return shown


def slide_json(record: Mapping[str, object]) -> str:
    """The slide's visible PT/EN copy as the JSON the model sees."""
    copy_by_locale = {
        locale: _visible(as_dict(record.get(key)) or {}) for locale, key in _LOCALES
    }
    return json.dumps(copy_by_locale, ensure_ascii=False, indent=2)


def issue_lines(issues: tuple[SlideIssue, ...]) -> list[str]:
    """One prompt line per failing check."""
    return [
        ISSUE_LINE.format(
            code=issue.code,
            locale=issue.locale or "slide",
            field=issue.field or "copy",
            message=issue.message,
        )
        for issue in issues
    ]


def _max_chars(slide_type: str, policy: CarouselPresentationPolicy) -> tuple[int, int]:
    heading = heading_budget_for_slide_type(slide_type, policy)
    body = body_budget_for_slide_type(slide_type, policy)
    heading_max = heading.max_characters if heading else _DEFAULT_BODY_MAX
    return heading_max, body.max_characters if body else _DEFAULT_BODY_MAX


def render_slide_fix_prompt(
    target: SlideTarget,
    issues: tuple[SlideIssue, ...],
    guide: tuple[CarouselPresentationPolicy, str, float],
) -> str:
    """Render the versioned prompt for one attempt on one slide."""
    policy, style_guide, voice_floor = guide
    pt_payload = as_dict(target.record.get(PRESENTATION_PT_KEY)) or {}
    slide_type = slide_type_of(pt_payload)
    heading_max, body_max = _max_chars(slide_type, policy)
    return build_slide_fix_prompt({
        VAR_SLIDE_INDEX: target.slide_index,
        VAR_SLIDE_TYPE: slide_type,
        VAR_ROLE: target.role,
        VAR_SLIDE_JSON: slide_json(target.record),
        VAR_ISSUES: issue_lines(issues),
        VAR_STYLE_GUIDE: style_guide,
        VAR_HEADING_MAX: heading_max,
        VAR_BODY_MAX: body_max,
        VAR_VOICE_FLOOR: int(voice_floor),
        VAR_QUALITY_RUBRIC: render_quality_rubric(policy, RUBRIC_AUDIENCE_CONTENT),
    })


def _merged_items(current: object, answered: object) -> list[dict[str, object]] | None:
    if not isinstance(current, list) or not isinstance(answered, list):
        return None
    if len(current) != len(answered):
        return None
    merged: list[dict[str, object]] = []
    for item, answer in zip(current, answered, strict=True):
        if not isinstance(item, Mapping) or not isinstance(answer, Mapping):
            return None
        texts = {key: answer.get(key) for key in _ITEM_KEYS}
        merged.append({
            **item,
            **{k: v for k, v in texts.items() if isinstance(v, str) and v.strip()},
        })
    return merged


def _merged_payload(
    payload: Mapping[str, object], answer: Mapping[str, object]
) -> dict[str, object]:
    merged = copy.deepcopy(dict(payload))
    for key in _COPY_KEYS:
        value = answer.get(key)
        if isinstance(value, str):
            merged[key] = value.strip()
    for list_field in ITEM_LISTS:
        items = _merged_items(merged.get(list_field), answer.get(list_field))
        if items is not None:
            merged[list_field] = items
    return merged


def apply_answer(record: Mapping[str, object], answer: str) -> dict[str, object] | None:
    """The record with the model's PT/EN copy; None when the answer is unusable."""
    parsed = parse_object_text(answer)
    if parsed is None:
        return None
    updated = copy.deepcopy(dict(record))
    applied = False
    for locale, key in _LOCALES:
        locale_answer = parsed.get(locale)
        payload = as_dict(record.get(key))
        if not isinstance(locale_answer, Mapping) or payload is None:
            continue
        updated[key] = _merged_payload(payload, locale_answer)
        applied = True
    return updated if applied else None


__all__ = [
    "apply_answer",
    "issue_lines",
    "render_slide_fix_prompt",
    "slide_json",
]
