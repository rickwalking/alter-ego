"""Which slides the model fix rewrites, and why (AE-0401).

A slide is a target when its PT or EN copy has a blocking violation, or (at
the content gate) when its persona voice score is under the floor. Blocking
rules without a slide (the slide count) cannot be fixed per slide: they are
returned apart so the caller escalates them as they are.

Pure: no DB, no LLM.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from rag_backend.application.services.carousel.outline_normalize import (
    OUTLINE_FIELD_ROLE,
)
from rag_backend.application.services.carousel.presentation_review_pipeline import (
    validate_localized_slides,
)
from rag_backend.application.services.carousel.slide_fix_types import (
    SlideIssue,
    SlideTarget,
)
from rag_backend.domain.constants.carousel_workflow import PHASE_CONTENT
from rag_backend.domain.constants.slide_fix import (
    ISSUE_VOICE_SCORE_LOW,
    ISSUE_VOICE_SCORE_MESSAGE,
    PERSONA_SCORE_SLIDE_KEY,
)
from rag_backend.domain.constants.workflow_state_fields import (
    STATE_FIELD_OUTLINE,
    STATE_FIELD_PERSONA_SCORES,
    STATE_FIELD_SLIDE_INDEX,
)
from rag_backend.domain.models.carousel_presentation import SlideValidationViolation
from rag_backend.domain.persona_score import stored_overall


@dataclass(frozen=True)
class TargetQuery:
    """The checkpoint copy and state, the gate phase and the voice floor."""

    records: list[dict[str, object]]
    state: Mapping[str, object]
    policy_version: str
    phase: str
    voice_floor: float


@dataclass(frozen=True)
class TargetSelection:
    """Slides to fix, and the blocking rules no slide fix can clear."""

    targets: tuple[SlideTarget, ...]
    unfixable_rules: tuple[str, ...]


def slide_issues(
    records: list[dict[str, object]], policy_version: str
) -> dict[int, list[SlideIssue]]:
    """Blocking violations per slide index (carousel-wide ones under -1)."""
    report = validate_localized_slides(records, policy_version=policy_version)
    issues: dict[int, list[SlideIssue]] = {}
    for violation in report.violations:
        if violation.is_blocker:
            index = violation.slide_index if violation.slide_index else -1
            issues.setdefault(index, []).append(_issue(violation))
    return issues


def _issue(violation: SlideValidationViolation) -> SlideIssue:
    return SlideIssue(
        code=violation.code,
        message=violation.message,
        locale=violation.locale or "",
        field=violation.field or "",
    )


def overall_score(value: object) -> float | None:
    """A persona-score entry's ``overall`` on 0-100; None when unscored (AE-0407)."""
    return stored_overall(value)


def slide_scores(state: Mapping[str, object]) -> dict[int, float]:
    """Voice scores (0-100) by slide index; unscored slides are left out."""
    raw = state.get(STATE_FIELD_PERSONA_SCORES)
    if not isinstance(raw, Mapping):
        return {}
    scores: dict[int, float] = {}
    for key, value in raw.items():
        prefix = PERSONA_SCORE_SLIDE_KEY.format(index="")
        suffix = str(key).removeprefix(prefix)
        score = overall_score(value)
        if str(key).startswith(prefix) and suffix.isdigit() and score is not None:
            scores[int(suffix)] = score
    return scores


def _roles(state: Mapping[str, object]) -> dict[int, str]:
    raw = state.get(STATE_FIELD_OUTLINE)
    if not isinstance(raw, list):
        return {}
    roles: dict[int, str] = {}
    for position, item in enumerate(raw, start=1):
        if isinstance(item, Mapping):
            index = item.get(STATE_FIELD_SLIDE_INDEX)
            role = item.get(OUTLINE_FIELD_ROLE)
            roles[index if isinstance(index, int) else position] = str(role or "")
    return roles


def _voice_issue(score: float, floor: float) -> SlideIssue:
    message = ISSUE_VOICE_SCORE_MESSAGE.format(score=score, floor=floor)
    return SlideIssue(code=ISSUE_VOICE_SCORE_LOW, message=message)


def _voice_issues(query: TargetQuery) -> dict[int, tuple[float, SlideIssue]]:
    if query.phase != PHASE_CONTENT:
        return {}
    return {
        index: (score, _voice_issue(score, query.voice_floor))
        for index, score in slide_scores(query.state).items()
        if score < query.voice_floor
    }


def select_targets(query: TargetQuery) -> TargetSelection:
    """The failing slides, in slide order, each with every check it fails."""
    by_index = {record.get(STATE_FIELD_SLIDE_INDEX): record for record in query.records}
    rules = slide_issues(query.records, query.policy_version)
    voice = _voice_issues(query)
    scores = slide_scores(query.state)
    roles = _roles(query.state)
    targets: list[SlideTarget] = []
    for index in sorted(set(rules) | set(voice)):
        record = by_index.get(index)
        if index < 0 or record is None:
            continue
        issues = [*rules.get(index, [])]
        if index in voice:
            issues.append(voice[index][1])
        targets.append(
            SlideTarget(
                slide_index=index,
                record=dict(record),
                issues=tuple(issues),
                score=scores.get(index),
                role=roles.get(index, ""),
            )
        )
    unfixable = tuple(dict.fromkeys(issue.code for issue in rules.get(-1, [])))
    return TargetSelection(targets=tuple(targets), unfixable_rules=unfixable)


__all__ = [
    "TargetQuery",
    "TargetSelection",
    "overall_score",
    "select_targets",
    "slide_issues",
    "slide_scores",
]
