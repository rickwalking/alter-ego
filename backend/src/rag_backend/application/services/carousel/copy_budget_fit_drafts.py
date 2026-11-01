"""The shorten step on the content drafts, right before the review build.

The drafts and EN translations are built into localized slides exactly as the
review build does (build + deterministic parse recovery), the over-budget
fields are shortened (``fit_slides_to_budgets``), and the slides that changed
are written back to the drafts and translations through the owner-edit path
(``apply_localized_slide_edits``), so the fail-closed review chain that runs
next validates the shortened copy. Slides with an unrecovered parse failure
are left to that chain; a scoped revision only touches its scoped slides; the
owner's PT hook heading is never rewritten.
"""

from __future__ import annotations

from dataclasses import dataclass

from rag_backend.application.services.carousel.copy_budget_fit import (
    BudgetFitCommand,
    FieldAddress,
    fit_slides_to_budgets,
)
from rag_backend.application.services.carousel.copy_budget_fit_llm import (
    CopyBudgetFitter,
)
from rag_backend.application.services.carousel.localized_slide_builder import (
    PRESENTATION_PT_KEY,
    as_dict,
    build_localized_slides_with_failures,
    resolve_policy_version,
)
from rag_backend.application.services.carousel.owner_autofix_paths import text_at
from rag_backend.application.services.carousel.presentation_policy import (
    load_presentation_policy,
)
from rag_backend.application.services.carousel.presentation_review import (
    WORKFLOW_STATE_LOCALIZED_SLIDES_KEY,
    WORKFLOW_STATE_PRESENTATION_POLICY_VERSION_KEY,
    WORKFLOW_STATE_PRESENTATION_VALIDATION_KEY,
    WORKFLOW_STATE_TRANSLATIONS_EN_KEY,
    deserialize_translations_en,
)
from rag_backend.application.services.carousel.presentation_review_edits import (
    apply_localized_slide_edits,
)
from rag_backend.application.services.carousel.slide_scaffold_recovery import (
    recover_parse_failures,
)
from rag_backend.domain.constants.carousel import LANGUAGE_PT
from rag_backend.domain.constants.presentation_roles import ROLE_HOOK
from rag_backend.domain.constants.workflow_state_fields import (
    STATE_FIELD_SLIDE_DRAFTS,
    STATE_FIELD_SLIDE_INDEX,
)

_HEADING = "heading"


@dataclass(frozen=True)
class DraftFitCommand:
    """The drafts to fit, their EN translations, the model and the voice rules."""

    slide_drafts: list[dict[str, object]]
    fitter: CopyBudgetFitter
    translations_en: object = None
    policy_version: str | None = None
    style_guide: str = ""
    forbidden_phrases: tuple[str, ...] = ()
    project_id: str = ""
    scope: frozenset[int] | None = None
    hook_text: str = ""
    approved_hook_title: str = ""


@dataclass(frozen=True)
class DraftFitResult:
    """The (possibly) shortened drafts and translations, and what changed."""

    slide_drafts: list[dict[str, object]]
    translations_en: object
    changed_indices: frozenset[int] = frozenset()


def _allowed(
    slides: list[dict[str, object]],
    blocked: set[int],
    scope: frozenset[int] | None,
) -> frozenset[int]:
    indices = {
        index
        for slide in slides
        if isinstance(index := slide.get(STATE_FIELD_SLIDE_INDEX), int)
    }
    allowed = indices - blocked
    return frozenset(allowed if scope is None else allowed & scope)


def _owner_hook_fields(
    slides: list[dict[str, object]],
    command: DraftFitCommand,
    policy_version: str,
) -> frozenset[FieldAddress]:
    """The PT hook heading the owner chose or approved: never rewritten.

    The hook slide is the one whose contract role is ``hook``. Its PT heading is
    the owner's when a hook was picked, or when it is still the approved outline
    title; an over-budget one blocks instead of being reworded. EN may be shortened.
    """
    policy = load_presentation_policy(policy_version)
    hooks = {slide.slide_number for slide in policy.slides if slide.role == ROLE_HOOK}
    picked = command.hook_text.strip()
    approved = command.approved_hook_title.strip()
    owned: set[FieldAddress] = set()
    for slide in slides:
        index = slide.get(STATE_FIELD_SLIDE_INDEX)
        if not isinstance(index, int) or index not in hooks:
            continue
        heading = text_at(as_dict(slide.get(PRESENTATION_PT_KEY)) or {}, _HEADING)
        if picked or (approved and heading.strip() == approved):
            owned.add((index, LANGUAGE_PT, _HEADING))
    return frozenset(owned)


def _unchanged(command: DraftFitCommand) -> DraftFitResult:
    return DraftFitResult(command.slide_drafts, command.translations_en)


async def fit_drafts_to_budgets(command: DraftFitCommand) -> DraftFitResult:
    """Shorten the drafts' over-budget fields; unchanged input when none changed."""
    drafts = command.slide_drafts
    if not drafts:
        return _unchanged(command)
    translations = (
        deserialize_translations_en(command.translations_en)
        if command.translations_en is not None
        else None
    )
    policy_version = command.policy_version or resolve_policy_version(drafts)
    built, failures = build_localized_slides_with_failures(
        drafts, translations_en=translations
    )
    slides, remaining = recover_parse_failures(built, failures)
    outcome = await fit_slides_to_budgets(
        BudgetFitCommand(
            slides=slides,
            fitter=command.fitter,
            policy_version=policy_version,
            style_guide=command.style_guide,
            forbidden_phrases=command.forbidden_phrases,
            project_id=command.project_id,
            only_slides=_allowed(
                slides, {failure.slide_index for failure in remaining}, command.scope
            ),
            excluded_fields=_owner_hook_fields(slides, command, policy_version),
        )
    )
    if not outcome.changed_indices:
        return _unchanged(command)
    edited = [
        slide
        for slide in outcome.slides
        if slide.get(STATE_FIELD_SLIDE_INDEX) in outcome.changed_indices
    ]
    state: dict[str, object] = {
        STATE_FIELD_SLIDE_DRAFTS: drafts,
        WORKFLOW_STATE_LOCALIZED_SLIDES_KEY: slides,
        WORKFLOW_STATE_PRESENTATION_VALIDATION_KEY: {},
        WORKFLOW_STATE_PRESENTATION_POLICY_VERSION_KEY: policy_version,
    }
    if command.translations_en is not None:
        state[WORKFLOW_STATE_TRANSLATIONS_EN_KEY] = command.translations_en
    updates = apply_localized_slide_edits(state, edited)
    fitted = updates.get(STATE_FIELD_SLIDE_DRAFTS)
    return DraftFitResult(
        slide_drafts=fitted if isinstance(fitted, list) else drafts,
        translations_en=(
            updates.get(WORKFLOW_STATE_TRANSLATIONS_EN_KEY)
            if command.translations_en is not None
            else None
        ),
        changed_indices=outcome.changed_indices,
    )


__all__ = [
    "DraftFitCommand",
    "DraftFitResult",
    "fit_drafts_to_budgets",
]
