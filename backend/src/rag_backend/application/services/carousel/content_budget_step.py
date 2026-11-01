"""How the content ensure runs the shorten step before the review build.

``llm_budget_fitter`` builds the fast-model fitter from the orchestrator's chat
model and its Langfuse tracing (the orchestrator names the trace
``copy budget fit``). ``run_budget_step`` shortens the drafts' over-budget
fields, writes the result into the ensure's updates (the drafts, and the EN
translations when the state has them) and re-scores the persona voice of the
slides that changed.

Voice guard: a shortened slide whose new voice score falls below
``VOICE_MATCH_MIN_SCORE`` while its old score met it goes back to its
pre-shortening draft, translation and score entry. The old entry still carries
the fingerprint of the old text, so the restore needs no model call; the slide
then reaches the validation with its original (over-budget) copy.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field, replace

from langchain_core.language_models import BaseChatModel
from langchain_core.runnables import RunnableConfig

from rag_backend.application.services.carousel.copy_budget_fit_drafts import (
    DraftFitCommand,
    DraftFitResult,
    fit_drafts_to_budgets,
)
from rag_backend.application.services.carousel.copy_budget_fit_llm import (
    CopyBudgetFitter,
    LlmCopyBudgetConfig,
    LlmCopyBudgetFitter,
)
from rag_backend.application.services.carousel.localized_slide_builder import (
    resolve_slide_index,
)
from rag_backend.domain.constants.persona import VOICE_MATCH_MIN_SCORE
from rag_backend.domain.constants.slide_fix import PERSONA_SCORE_SLIDE_KEY
from rag_backend.domain.constants.workflow_state_fields import (
    STATE_FIELD_PERSONA_SCORES,
    STATE_FIELD_SLIDE_DRAFTS,
)
from rag_backend.domain.models.persona import PersonaProfile
from rag_backend.domain.persona_score import stored_overall

_TRANSLATIONS_EN_KEY = "translations_en"
_OUTLINE_TITLE_KEY = "title"
_POLICY_VERSION_KEY = "presentation_policy_version"
_PROJECT_ID_KEY = "project_id"

VoiceScorer = Callable[[list[object], object], Awaitable[dict[str, object]]]


def llm_budget_fitter(
    llm: BaseChatModel, tracing: Callable[[], RunnableConfig] | None
) -> CopyBudgetFitter | None:
    """The fast-model fitter, on when tracing is configured."""
    if tracing is None:
        return None
    return LlmCopyBudgetFitter(LlmCopyBudgetConfig(llm=llm, runnable_config=tracing))


@dataclass(frozen=True)
class BudgetStepInput:
    """The drafts and translations the review build would use, plus voice rules.

    ``scorer`` re-scores the persona voice (``{"persona_scores": ...}`` or ``{}``
    without a persona) from the drafts and the previous scores. ``hook_text`` is
    the owner's chosen hook and ``approved_hook_title`` the slide-1 title of the
    approved outline: the PT hook heading they name is never rewritten.
    """

    project_id: str
    slide_drafts: object
    translations_en: object
    policy_version: str | None = None
    style_guide: str = ""
    forbidden_phrases: tuple[str, ...] = ()
    scope: frozenset[int] | None = None
    hook_text: str = ""
    approved_hook_title: str = ""
    scorer: VoiceScorer | None = None
    previous_scores: object = field(default=None)


def _drafts(raw: object) -> list[dict[str, object]]:
    if not isinstance(raw, list):
        return []
    return [draft for draft in raw if isinstance(draft, dict)]


def _dropped_voice(old: object, new: object, key: str) -> bool:
    """True when the slide met the voice floor before and falls under it now."""
    before = stored_overall(old.get(key)) if isinstance(old, Mapping) else None
    after = stored_overall(new.get(key)) if isinstance(new, Mapping) else None
    if before is None or after is None:
        return False
    return before >= VOICE_MATCH_MIN_SCORE > after


@dataclass(frozen=True)
class _Guard:
    """What the voice guard compares: the inputs, the fit and both score maps."""

    original: list[dict[str, object]]
    fit: DraftFitResult
    old_scores: object
    new_scores: dict[str, object]


def _reverted_positions(guard: _Guard) -> list[int]:
    return [
        position
        for position, draft in enumerate(guard.fit.slide_drafts)
        if resolve_slide_index(draft, position + 1) in guard.fit.changed_indices
        and position < len(guard.original)
        and _dropped_voice(
            guard.old_scores,
            guard.new_scores,
            PERSONA_SCORE_SLIDE_KEY.format(index=position + 1),
        )
    ]


def _restored_translations(
    fitted: object, original: object, indices: set[int]
) -> object:
    if not isinstance(fitted, dict) or not isinstance(original, Mapping):
        return fitted
    restored = dict(fitted)
    for index in indices:
        key = str(index)
        if key in original:
            restored[key] = original[key]
    return restored


def _apply_guard(
    guard: _Guard, step: BudgetStepInput
) -> tuple[DraftFitResult, dict[str, object]]:
    """The fit and scores with the voice-dropping slides put back."""
    positions = _reverted_positions(guard)
    if not positions:
        return guard.fit, guard.new_scores
    drafts = list(guard.fit.slide_drafts)
    scores = dict(guard.new_scores)
    old = guard.old_scores if isinstance(guard.old_scores, Mapping) else {}
    indices: set[int] = set()
    for position in positions:
        drafts[position] = guard.original[position]
        indices.add(resolve_slide_index(drafts[position], position + 1))
        key = PERSONA_SCORE_SLIDE_KEY.format(index=position + 1)
        scores[key] = old[key]
    translations = _restored_translations(
        guard.fit.translations_en, step.translations_en, indices
    )
    fit = replace(
        guard.fit,
        slide_drafts=drafts,
        translations_en=translations,
        changed_indices=guard.fit.changed_indices - indices,
    )
    return fit, scores


async def _rescore(
    step: BudgetStepInput,
    fit: DraftFitResult,
    context: tuple[list[dict[str, object]], dict[str, object]],
) -> DraftFitResult:
    """Re-score the changed slides, then undo the shortening that cost the voice."""
    original, updates = context
    if step.scorer is None:
        return fit
    previous = updates.get(STATE_FIELD_PERSONA_SCORES) or step.previous_scores
    rescored = await step.scorer(list(fit.slide_drafts), previous)
    new_scores = rescored.get(STATE_FIELD_PERSONA_SCORES)
    if not isinstance(new_scores, dict):
        return fit
    guarded, scores = _apply_guard(_Guard(original, fit, previous, new_scores), step)
    updates[STATE_FIELD_PERSONA_SCORES] = scores
    return guarded


def _write(fit: DraftFitResult, updates: dict[str, object]) -> None:
    updates[STATE_FIELD_SLIDE_DRAFTS] = fit.slide_drafts
    if fit.translations_en is not None:
        updates[_TRANSLATIONS_EN_KEY] = fit.translations_en


async def run_budget_step(
    fitter: CopyBudgetFitter | None,
    step: BudgetStepInput,
    updates: dict[str, object],
) -> DraftFitResult:
    """Shorten the over-budget fields; changed drafts and scores land in ``updates``."""
    drafts = _drafts(step.slide_drafts)
    if fitter is None:
        return DraftFitResult(drafts, step.translations_en)
    fit = await fit_drafts_to_budgets(
        DraftFitCommand(
            slide_drafts=drafts,
            fitter=fitter,
            translations_en=step.translations_en,
            policy_version=step.policy_version,
            style_guide=step.style_guide,
            forbidden_phrases=step.forbidden_phrases,
            project_id=step.project_id,
            scope=step.scope,
            hook_text=step.hook_text,
            approved_hook_title=step.approved_hook_title,
        )
    )
    if not fit.changed_indices:
        return fit
    guarded = await _rescore(step, fit, (drafts, updates))
    _write(guarded, updates)
    return guarded


@dataclass(frozen=True)
class ContentBudgetContext:
    """What the content ensure hands the step (``updates`` is changed in place).

    ``slide_drafts`` are the sanitized drafts; ``hook_text`` is the content mode's
    chosen hook; ``scorer`` is the runner's persona scoring bound to this run.
    """

    state: Mapping[str, object]
    updates: dict[str, object]
    slide_drafts: object
    style_guide: str = ""
    persona: PersonaProfile | None = None
    hook_text: str = ""
    outline: object = None
    scope: frozenset[int] | None = None
    scorer: VoiceScorer | None = None


def review_translations(
    state: Mapping[str, object], updates: Mapping[str, object]
) -> object:
    """EN translations for the content review build.

    Fresh translations win. When the drafts were NOT regenerated the stored
    translations still match them: dropping them made the builder fall back to the
    PT draft, so the EN copy silently became Portuguese.
    """
    fresh = updates.get(_TRANSLATIONS_EN_KEY)
    if fresh is not None or STATE_FIELD_SLIDE_DRAFTS in updates:
        return fresh
    return state.get(_TRANSLATIONS_EN_KEY)


def _approved_hook_title(outline: object) -> str:
    """The slide-1 title of the approved outline ("" when there is none)."""
    if not isinstance(outline, list):
        return ""
    for position, slide in enumerate(outline):
        if isinstance(slide, Mapping) and resolve_slide_index(slide, position + 1) == 1:
            title = slide.get(_OUTLINE_TITLE_KEY)
            return title if isinstance(title, str) else ""
    return ""


def _policy_version(state: Mapping[str, object]) -> str | None:
    value = state.get(_POLICY_VERSION_KEY)
    return value if isinstance(value, str) and value.strip() else None


async def run_content_budget_step(
    fitter: CopyBudgetFitter | None, context: ContentBudgetContext
) -> DraftFitResult:
    """The shorten step of one content ensure, with the persona voice guard."""
    state = context.state
    return await run_budget_step(
        fitter,
        BudgetStepInput(
            project_id=str(state.get(_PROJECT_ID_KEY, "")),
            slide_drafts=context.slide_drafts,
            translations_en=review_translations(state, context.updates),
            policy_version=_policy_version(state),
            style_guide=context.style_guide,
            forbidden_phrases=(
                tuple(context.persona.forbidden_phrases) if context.persona else ()
            ),
            scope=context.scope,
            hook_text=context.hook_text,
            approved_hook_title=_approved_hook_title(context.outline),
            scorer=context.scorer,
            previous_scores=state.get(STATE_FIELD_PERSONA_SCORES),
        ),
        context.updates,
    )


__all__ = [
    "BudgetStepInput",
    "ContentBudgetContext",
    "VoiceScorer",
    "llm_budget_fitter",
    "review_translations",
    "run_budget_step",
    "run_content_budget_step",
]
