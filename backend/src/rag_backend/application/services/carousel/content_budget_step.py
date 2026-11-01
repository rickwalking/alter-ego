"""How the content ensure runs the shorten step before the review build.

``llm_budget_fitter`` builds the fast-model fitter from the orchestrator's chat
model and Langfuse tracing (on exactly when the gate repair is). ``run_budget_step``
shortens the drafts' over-budget fields and writes the result into the ensure's
updates: the drafts, and the EN translations when the state has them.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

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
from rag_backend.domain.constants.workflow_state_fields import STATE_FIELD_SLIDE_DRAFTS

_TRANSLATIONS_EN_KEY = "translations_en"


def llm_budget_fitter(
    llm: BaseChatModel, tracing: Callable[[], RunnableConfig] | None
) -> CopyBudgetFitter | None:
    """The fast-model fitter, on when tracing is configured."""
    if tracing is None:
        return None
    return LlmCopyBudgetFitter(LlmCopyBudgetConfig(llm=llm, runnable_config=tracing))


@dataclass(frozen=True)
class BudgetStepInput:
    """The drafts and translations the review build would use, plus voice rules."""

    project_id: str
    slide_drafts: object
    translations_en: object
    policy_version: str | None = None
    style_guide: str = ""
    forbidden_phrases: tuple[str, ...] = ()
    scope: frozenset[int] | None = None


def _drafts(raw: object) -> list[dict[str, object]]:
    if not isinstance(raw, list):
        return []
    return [draft for draft in raw if isinstance(draft, dict)]


async def run_budget_step(
    fitter: CopyBudgetFitter | None,
    step: BudgetStepInput,
    updates: dict[str, object],
) -> DraftFitResult:
    """Shorten the over-budget fields; changed drafts land in ``updates``."""
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
        )
    )
    if not fit.changed_indices:
        return fit
    updates[STATE_FIELD_SLIDE_DRAFTS] = fit.slide_drafts
    if fit.translations_en is not None:
        updates[_TRANSLATIONS_EN_KEY] = fit.translations_en
    return fit


__all__ = ["BudgetStepInput", "llm_budget_fitter", "run_budget_step"]
