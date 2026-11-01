"""Shorten every over-budget field before the presentation validation.

The validator (unchanged) finds the fields over their copy budget
(``heading_too_long``, ``body_too_long``, ``copy_too_many_lines``) in PT and EN,
headings, bodies and item titles/bodies. Only those fields go to the fast model,
one call per attempt, at most ``max_attempts``. Every answer is checked by code
before it replaces the field:

- non-empty, different, and (EN) not Portuguese;
- shorter than the current text, or on fewer lines;
- no persona forbidden phrase the current text did not already have;
- re-validating the whole deck adds no new violation anywhere (a lone ``**``, a
  body without final punctuation, a body under the minimum words, a hook over
  its word limit, a heading repeated in the body...).

A rejected answer leaves the field as it was. An accepted answer that is still
over budget is kept as the best effort (the shortest accepted text) and asked
again on the next attempt. Nothing is ever cut mechanically; what still does
not fit goes to the normal validation, which is not loosened. Never raises: a
failing model leaves the copy as it was.
"""

from __future__ import annotations

import asyncio
import copy
from dataclasses import dataclass, field

import structlog

from rag_backend.application.services.carousel.content_gate_repair_targets import (
    FieldRepairTarget,
    TargetPlan,
    apply_fixes,
    plan_targets,
)
from rag_backend.application.services.carousel.copy_budget_fit_llm import (
    CopyBudgetFitter,
    FitRequest,
    FitTarget,
)
from rag_backend.application.services.carousel.copy_budget_limits import (
    field_limit,
)
from rag_backend.application.services.carousel.localized_slide_builder import (
    PRESENTATION_EN_KEY,
    PRESENTATION_PT_KEY,
    as_dict,
)
from rag_backend.application.services.carousel.owner_autofix_text import (
    looks_portuguese,
)
from rag_backend.application.services.carousel.presentation_policy import (
    load_presentation_policy,
)
from rag_backend.application.services.carousel.presentation_review_pipeline import (
    validate_localized_slides,
)
from rag_backend.application.services.carousel.presentation_validation_fields import (
    count_rendered_lines,
)
from rag_backend.domain.constants.carousel import LANGUAGE_EN, LANGUAGE_PT
from rag_backend.domain.constants.carousel_presentation import (
    VIOLATION_BODY_TOO_LONG,
    VIOLATION_COPY_TOO_MANY_LINES,
    VIOLATION_HEADING_TOO_LONG,
)
from rag_backend.domain.constants.copy_budget_fit import (
    COPY_BUDGET_FIT_MAX_ATTEMPTS,
    COPY_BUDGET_FIT_TIMEOUT_SECONDS,
    LOG_COPY_BUDGET_FIT_ATTEMPT,
    LOG_COPY_BUDGET_FIT_DONE,
    LOG_COPY_BUDGET_FIT_MODEL_FAILED,
)
from rag_backend.domain.constants.presentation_policy import (
    DEFAULT_PRESENTATION_POLICY_VERSION,
)
from rag_backend.domain.constants.workflow_state_fields import STATE_FIELD_SLIDE_INDEX

logger = structlog.get_logger(__name__)

LENGTH_VIOLATION_CODES: frozenset[str] = frozenset({
    VIOLATION_HEADING_TOO_LONG,
    VIOLATION_BODY_TOO_LONG,
    VIOLATION_COPY_TOO_MANY_LINES,
})
_LOCALE_KEYS: dict[str, str] = {
    LANGUAGE_PT: PRESENTATION_PT_KEY,
    LANGUAGE_EN: PRESENTATION_EN_KEY,
}

ViolationKey = tuple[int | None, str | None, str | None, str]


@dataclass(frozen=True)
class BudgetFitCommand:
    """The localized slides to fit and how.

    ``only_slides`` limits the step to these slide indices (a scoped revision,
    or the slides without an unrecovered parse failure); None means every slide.
    """

    slides: list[dict[str, object]]
    fitter: CopyBudgetFitter
    policy_version: str | None = None
    style_guide: str = ""
    forbidden_phrases: tuple[str, ...] = ()
    project_id: str = ""
    only_slides: frozenset[int] | None = None
    max_attempts: int = COPY_BUDGET_FIT_MAX_ATTEMPTS


@dataclass
class BudgetFitOutcome:
    """Where the step ended, with the counts it logs."""

    slides: list[dict[str, object]]
    changed_indices: frozenset[int] = frozenset()
    attempts: int = 0
    asked: int = 0
    accepted: int = 0
    rejected: int = 0
    still_over: int = 0
    requested: list[tuple[str, ...]] = field(default_factory=list)


def _violation_keys(
    slides: list[dict[str, object]], command: BudgetFitCommand
) -> set[ViolationKey]:
    report = validate_localized_slides(slides, policy_version=command.policy_version)
    return {
        (violation.slide_index, violation.locale, violation.field, violation.code)
        for violation in report.violations
    }


def _over_budget_targets(
    slides: list[dict[str, object]], command: BudgetFitCommand
) -> tuple[FitTarget, ...]:
    """Every over-budget field of the allowed slides, with its full limit."""
    policy = load_presentation_policy(
        command.policy_version or DEFAULT_PRESENTATION_POLICY_VERSION
    )
    report = validate_localized_slides(slides, policy_version=command.policy_version)
    over = [
        violation
        for violation in report.violations
        if violation.code in LENGTH_VIOLATION_CODES
        and (
            command.only_slides is None or violation.slide_index in command.only_slides
        )
    ]
    targets = plan_targets(TargetPlan(slides, over, policy, {}))
    payloads = _payloads(slides)
    found: list[FitTarget] = []
    for target in targets:
        payload = payloads.get((target.slide_index, target.locale), {})
        limit = field_limit(payload, target.field, policy)
        if limit is not None:
            found.append(FitTarget(target=target, limit=limit))
    return tuple(found)


def _payloads(
    slides: list[dict[str, object]],
) -> dict[tuple[int, str], dict[str, object]]:
    payloads: dict[tuple[int, str], dict[str, object]] = {}
    for slide in slides:
        index = slide.get(STATE_FIELD_SLIDE_INDEX)
        if not isinstance(index, int):
            continue
        for locale, key in _LOCALE_KEYS.items():
            payload = as_dict(slide.get(key))
            if payload is not None:
                payloads[index, locale] = payload
    return payloads


def _adds_forbidden_phrase(before: str, after: str, phrases: tuple[str, ...]) -> bool:
    old, new = before.casefold(), after.casefold()
    return any(
        phrase.strip() and phrase.casefold() in new and phrase.casefold() not in old
        for phrase in phrases
    )


def _plausible(item: FitTarget, text: str, command: BudgetFitCommand) -> bool:
    """Cheap checks before re-validation: new, shorter, right language, on-voice."""
    current = item.target.text
    if not text or text == current:
        return False
    if item.target.locale == LANGUAGE_EN and looks_portuguese(text):
        return False
    shorter = len(text) < len(current)
    fewer_lines = count_rendered_lines(text) < count_rendered_lines(current)
    if not (shorter or fewer_lines):
        return False
    return not _adds_forbidden_phrase(current, text, command.forbidden_phrases)


def _own_length_keys(target: FieldRepairTarget) -> set[ViolationKey]:
    return {
        (target.slide_index, target.locale, target.field, code)
        for code in LENGTH_VIOLATION_CODES
    }


def _try_answer(
    slides: list[dict[str, object]],
    item: FitTarget,
    answer: tuple[str, BudgetFitCommand],
) -> list[dict[str, object]] | None:
    """The slides with the answer patched in, or None when it is rejected."""
    text, command = answer
    if not _plausible(item, text, command):
        return None
    patched = apply_fixes(slides, (item.target,), {item.target.target_id: text})
    own = _own_length_keys(item.target)
    before = _violation_keys(slides, command) - own
    after = _violation_keys(patched, command) - own
    if after - before:
        return None
    return patched


async def _ask(
    command: BudgetFitCommand, targets: tuple[FitTarget, ...]
) -> dict[str, str] | None:
    """Ask the model once; any provider or parse failure keeps the copy."""
    try:
        return await asyncio.wait_for(
            command.fitter.fit(FitRequest(targets, command.style_guide)),
            timeout=COPY_BUDGET_FIT_TIMEOUT_SECONDS,
        )
    except Exception as exc:
        logger.warning(
            LOG_COPY_BUDGET_FIT_MODEL_FAILED,
            project_id=command.project_id,
            error=type(exc).__name__,
        )
        return None


def _apply_answers(
    slides: list[dict[str, object]],
    answer: tuple[tuple[FitTarget, ...], dict[str, str], BudgetFitCommand],
    outcome: BudgetFitOutcome,
) -> list[dict[str, object]]:
    targets, texts, command = answer
    for item in targets:
        text = texts.get(item.target.target_id, "").strip()
        patched = _try_answer(slides, item, (text, command))
        if patched is None:
            outcome.rejected += 1
            continue
        outcome.accepted += 1
        slides = patched
    return slides


def _visible(slide: dict[str, object]) -> tuple[object, object]:
    return slide.get(PRESENTATION_PT_KEY), slide.get(PRESENTATION_EN_KEY)


def _changed(
    before: list[dict[str, object]], after: list[dict[str, object]]
) -> frozenset[int]:
    original = {slide.get(STATE_FIELD_SLIDE_INDEX): _visible(slide) for slide in before}
    return frozenset(
        index
        for slide in after
        if isinstance(index := slide.get(STATE_FIELD_SLIDE_INDEX), int)
        and original.get(index) != _visible(slide)
    )


def _log_done(command: BudgetFitCommand, outcome: BudgetFitOutcome) -> None:
    logger.info(
        LOG_COPY_BUDGET_FIT_DONE,
        project_id=command.project_id,
        attempts=outcome.attempts,
        asked=outcome.asked,
        accepted=outcome.accepted,
        rejected=outcome.rejected,
        still_over=outcome.still_over,
        changed_slides=sorted(outcome.changed_indices),
    )


async def fit_slides_to_budgets(command: BudgetFitCommand) -> BudgetFitOutcome:
    """Shorten the over-budget fields, at most ``max_attempts`` model calls."""
    original = copy.deepcopy(command.slides)
    slides = copy.deepcopy(command.slides)
    outcome = BudgetFitOutcome(slides=slides)
    for _ in range(command.max_attempts):
        targets = _over_budget_targets(slides, command)
        if not targets:
            break
        ids = tuple(item.target.target_id for item in targets)
        outcome.attempts += 1
        outcome.asked += len(ids)
        outcome.requested.append(ids)
        logger.info(
            LOG_COPY_BUDGET_FIT_ATTEMPT,
            project_id=command.project_id,
            fields=len(ids),
            ids=ids,
        )
        texts = await _ask(command, targets)
        if texts is None:
            break
        slides = _apply_answers(slides, (targets, texts, command), outcome)
    outcome.slides = slides
    outcome.still_over = len(_over_budget_targets(slides, command))
    outcome.changed_indices = _changed(original, slides)
    _log_done(command, outcome)
    return outcome


__all__ = [
    "LENGTH_VIOLATION_CODES",
    "BudgetFitCommand",
    "BudgetFitOutcome",
    "fit_slides_to_budgets",
]
