"""Which fields the content-gate repair rewrites, and how answers are applied (AE-0430).

Pure: no DB, no LLM. A target is one visible text (``heading``, ``body``,
``tldr_strip`` or ``<list>[<n>].title|body``) of one locale of one slide that
a blocking violation names. It carries the current text, the exact budget the
validator enforces, the problems found and the PT source text, so the model
rewrites only that field. Fields that pass are never targets, and answers for
ids nobody asked for are ignored.

A ``translation_shape_mismatch`` has no field: the EN payload first receives
every structured field PT has and EN lacks (copied from PT), and each copied
text becomes a "translate this" target.
"""

from __future__ import annotations

import copy
import re
from collections.abc import Mapping
from dataclasses import dataclass

from rag_backend.application.services.carousel.localized_slide_builder import (
    PRESENTATION_EN_KEY,
    PRESENTATION_PT_KEY,
    STRUCTURED_EXTRA_KEYS,
    as_dict,
)
from rag_backend.application.services.carousel.owner_autofix_paths import (
    text_at,
    visible_paths,
    with_text,
)
from rag_backend.application.services.carousel.presentation_casing_markers import (
    drop_casing_repair_markers,
)
from rag_backend.application.services.carousel.presentation_policy_types import (
    CarouselPresentationPolicy,
    TextBudget,
)
from rag_backend.application.services.carousel.presentation_validation_fields import (
    body_budget_for_slide_type,
    heading_budget_for_slide_type,
)
from rag_backend.application.services.carousel.slide_parse_failures import (
    drop_parse_failure_marker,
)
from rag_backend.domain.constants.carousel import LANGUAGE_EN, LANGUAGE_PT
from rag_backend.domain.constants.content_gate_repair import (
    GATE_REPAIR_MAX_TARGETS,
    GATE_REPAIR_PROBLEM_LINE,
    GATE_REPAIR_PROBLEM_MISSING_EN,
    GATE_REPAIR_TARGET_ID,
)
from rag_backend.domain.constants.workflow_state_fields import (
    STATE_FIELD_SLIDE_INDEX,
)
from rag_backend.domain.models.carousel_presentation import SlideValidationViolation

_HEADING = "heading"
_BODY = "body"
_ITEM_PATH = re.compile(r"^(\w+)\[\d+\]\.(title|body)$")
# Item list -> (title budget key, body budget key), as the validator reads them.
_ITEM_BUDGET_KEYS: dict[str, tuple[str, str]] = {
    "features": ("feature_title", "feature_body"),
    "summary_points": ("summary_point_title", "summary_point_body"),
    "actions": ("closing_action_title", "closing_action_body"),
}
_LOCALE_KEYS: dict[str, str] = {
    LANGUAGE_PT: PRESENTATION_PT_KEY,
    LANGUAGE_EN: PRESENTATION_EN_KEY,
}


@dataclass(frozen=True)
class FieldRepairTarget:
    """One failing visible text the model rewrites."""

    target_id: str
    slide_index: int
    locale: str
    field: str
    text: str
    problems: tuple[str, ...]
    slide_heading: str = ""
    source_text: str = ""
    max_characters: int | None = None
    max_lines: int | None = None


@dataclass(frozen=True)
class _SlideView:
    """One slide's payloads, for target building."""

    slide_index: int
    payloads: dict[str, dict[str, object]]


def target_id(slide_index: int, locale: str, field: str) -> str:
    """The id a target and its answer share."""
    return GATE_REPAIR_TARGET_ID.format(slide=slide_index, locale=locale, field=field)


def field_budget(
    payload: Mapping[str, object],
    field: str,
    policy: CarouselPresentationPolicy,
) -> TextBudget | None:
    """The budget the validator enforces on one field path (None: no budget)."""
    slide_type = str(payload.get("slide_type") or "")
    if field == _HEADING:
        return heading_budget_for_slide_type(slide_type, policy)
    if field == _BODY:
        return body_budget_for_slide_type(slide_type, policy)
    match = _ITEM_PATH.match(field)
    keys = _ITEM_BUDGET_KEYS.get(match.group(1)) if match else None
    if match is None or keys is None:
        return None
    return policy.copy_budgets.get(keys[0] if match.group(2) == "title" else keys[1])


def _missing(pt_value: object, en_value: object) -> bool:
    if en_value is None or en_value in ("", []):
        return True
    if isinstance(pt_value, list) and isinstance(en_value, list):
        return len(pt_value) != len(en_value)
    return False


def fill_missing_en_structure(
    slide: Mapping[str, object],
) -> tuple[dict[str, object], tuple[str, ...]]:
    """Copy PT structured fields EN lacks into EN; return the copied text paths."""
    pt = as_dict(slide.get(PRESENTATION_PT_KEY))
    en = as_dict(slide.get(PRESENTATION_EN_KEY))
    if pt is None or en is None:
        return dict(slide), ()
    filled = copy.deepcopy(dict(en))
    keys = [
        key
        for key in STRUCTURED_EXTRA_KEYS
        if pt.get(key) not in (None, "", []) and _missing(pt.get(key), en.get(key))
    ]
    for key in keys:
        filled[key] = copy.deepcopy(pt[key])
    if not keys:
        return dict(slide), ()
    paths = tuple(
        path
        for path in visible_paths(filled)
        if path.split("[")[0] in keys and text_at(filled, path)
    )
    return {**slide, PRESENTATION_EN_KEY: filled}, paths


def _views(slides: list[dict[str, object]]) -> dict[int, _SlideView]:
    views: dict[int, _SlideView] = {}
    for slide in slides:
        index = slide.get(STATE_FIELD_SLIDE_INDEX)
        if not isinstance(index, int):
            continue
        payloads = {
            locale: as_dict(slide.get(key)) or {}
            for locale, key in _LOCALE_KEYS.items()
        }
        views[index] = _SlideView(slide_index=index, payloads=payloads)
    return views


def _problems_by_field(
    violations: list[SlideValidationViolation],
) -> dict[tuple[int, str, str], list[str]]:
    grouped: dict[tuple[int, str, str], list[str]] = {}
    for violation in violations:
        if violation.slide_index is None or not violation.locale or not violation.field:
            continue
        key = (violation.slide_index, violation.locale, violation.field)
        line = GATE_REPAIR_PROBLEM_LINE.format(
            code=violation.code, message=violation.message
        )
        grouped.setdefault(key, []).append(line)
    return grouped


@dataclass(frozen=True)
class TargetPlan:
    """Inputs for planning one round's targets."""

    slides: list[dict[str, object]]
    violations: list[SlideValidationViolation]
    policy: CarouselPresentationPolicy
    filled: Mapping[int, tuple[str, ...]]


def _target(
    view: _SlideView,
    address: tuple[str, str],
    context: tuple[tuple[str, ...], CarouselPresentationPolicy],
) -> FieldRepairTarget | None:
    locale, field = address
    problems, policy = context
    payload = view.payloads.get(locale) or {}
    if field not in visible_paths(payload):
        return None
    pt_payload = view.payloads.get(LANGUAGE_PT) or {}
    budget = field_budget(payload, field, policy)
    return FieldRepairTarget(
        target_id=target_id(view.slide_index, locale, field),
        slide_index=view.slide_index,
        locale=locale,
        field=field,
        text=text_at(payload, field),
        problems=problems,
        slide_heading=text_at(pt_payload, _HEADING),
        source_text=text_at(pt_payload, field) if locale == LANGUAGE_EN else "",
        max_characters=budget.max_characters if budget else None,
        max_lines=budget.max_lines if budget else None,
    )


def _wanted(plan: TargetPlan) -> dict[tuple[int, str, str], list[str]]:
    wanted = _problems_by_field(plan.violations)
    for slide_index, paths in plan.filled.items():
        for path in paths:
            key = (slide_index, LANGUAGE_EN, path)
            wanted.setdefault(key, []).insert(0, GATE_REPAIR_PROBLEM_MISSING_EN)
    return wanted


def plan_targets(plan: TargetPlan) -> tuple[FieldRepairTarget, ...]:
    """The round's targets: every addressable failing text, in slide order."""
    views = _views(plan.slides)
    targets: list[FieldRepairTarget] = []
    for (slide_index, locale, field), problems in sorted(_wanted(plan).items()):
        view = views.get(slide_index)
        if view is None:
            continue
        target = _target(view, (locale, field), (tuple(problems), plan.policy))
        if target is not None:
            targets.append(target)
    return tuple(targets[:GATE_REPAIR_MAX_TARGETS])


def _patched_slide(
    slide: dict[str, object],
    fixes: list[tuple[FieldRepairTarget, str]],
) -> dict[str, object]:
    updated = dict(slide)
    for target, text in fixes:
        key = _LOCALE_KEYS[target.locale]
        payload = as_dict(updated.get(key)) or {}
        updated[key] = with_text(payload, target.field, text)
        # The rewritten copy supersedes the stored parse/casing markers (as an
        # owner edit does), so a fixed field can clear inside the loop.
        drop_parse_failure_marker(updated, target.locale)
        drop_casing_repair_markers(updated, target.locale)
    return updated


def apply_fixes(
    slides: list[dict[str, object]],
    targets: tuple[FieldRepairTarget, ...],
    texts: Mapping[str, str],
) -> list[dict[str, object]]:
    """Slides with the answered texts patched in by path (asked ids only)."""
    by_slide: dict[int, list[tuple[FieldRepairTarget, str]]] = {}
    for target in targets:
        text = texts.get(target.target_id, "").strip()
        if text and text != target.text:
            by_slide.setdefault(target.slide_index, []).append((target, text))
    patched: list[dict[str, object]] = []
    for slide in slides:
        index = slide.get(STATE_FIELD_SLIDE_INDEX)
        fixes = by_slide.get(index) if isinstance(index, int) else None
        patched.append(_patched_slide(slide, fixes) if fixes else slide)
    return patched


__all__ = [
    "FieldRepairTarget",
    "TargetPlan",
    "apply_fixes",
    "field_budget",
    "fill_missing_en_structure",
    "plan_targets",
    "target_id",
]
