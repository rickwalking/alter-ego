"""The content phase's fail-closed review step.

The review runs the fail-closed chain over the fitted drafts. Its retry may re-draft
slides after the distribution wrote the slide rows, so a re-drafted slide gets its
EN copy from the same translation call the distribution uses, and the review's
slides reach the rows here, before the slower gate repair and the end of the phase.
"""

from __future__ import annotations

from dataclasses import dataclass

from langchain_core.language_models import BaseChatModel
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.application.services.carousel.content_fail_closed import (
    FailClosedReviewCommand,
    SlideDraftRetryFn,
    build_fail_closed_review_updates,
)
from rag_backend.application.services.carousel.editorial_distribution_generation import (
    _generate_en_translations,
)
from rag_backend.application.services.carousel.json_answers import JsonAnswers
from rag_backend.application.services.carousel.localized_rows_sync import (
    sync_rows_to_localized,
)
from rag_backend.application.services.carousel.presentation_review import (
    deserialize_translations_en,
)
from rag_backend.application.services.carousel.redrafted_translation import (
    SlideTranslateFn,
)
from rag_backend.application.services.carousel.revision_scope import (
    keep_unscoped_slides,
)
from rag_backend.application.services.carousel.workflow_state import (
    CarouselWorkflowState,
)
from rag_backend.domain.constants.workflow_state_fields import (
    STATE_FIELD_SLIDE_DRAFTS,
)


@dataclass(frozen=True)
class RedraftTranslator:
    """The EN translation of re-drafted slides, as the distribution makes it."""

    llm: BaseChatModel
    answers: JsonAnswers | None

    async def __call__(
        self, slide_drafts: list[dict[str, object]]
    ) -> dict[int, dict[str, object]]:
        """The EN copy of ``slide_drafts`` by slide index."""
        return await _generate_en_translations(self.llm, slide_drafts, self.answers)


@dataclass(frozen=True)
class ContentReviewContext:
    """Inputs for building the fail-closed content review updates."""

    project_id: str
    slide_drafts: object
    translations_en: object
    retry_draft: SlideDraftRetryFn | None
    policy_version: str | None = None
    translate_slides: SlideTranslateFn | None = None
    scope: frozenset[int] | None = None


@dataclass(frozen=True)
class ContentPhaseUpdates:
    """The content phase's state and the updates it is building."""

    state: CarouselWorkflowState
    updates: dict[str, object]


async def build_presentation_review_updates(
    context: ContentReviewContext,
) -> dict[str, object]:
    """Build content review updates through the fail-closed chain."""
    slide_drafts = context.slide_drafts
    draft_dicts = (
        [slide for slide in slide_drafts if isinstance(slide, dict)]
        if isinstance(slide_drafts, list)
        else []
    )
    translations = (
        deserialize_translations_en(context.translations_en)
        if context.translations_en is not None
        else None
    )
    return await build_fail_closed_review_updates(
        FailClosedReviewCommand(
            project_id=context.project_id,
            slide_drafts=draft_dicts,
            translations_en=translations,
            policy_version=context.policy_version,
            retry_draft=context.retry_draft,
            translate_slides=context.translate_slides,
        )
    )


async def review_content(
    db: AsyncSession | None,
    phase: ContentPhaseUpdates,
    context: ContentReviewContext,
) -> None:
    """Build the content review into ``phase.updates`` (in place).

    A retry changes slides after the distribution wrote the rows, so its slides
    reach the rows here, before the slower gate repair and the end of the phase.
    """
    review = await build_presentation_review_updates(context)
    updates = phase.updates
    updates.update(review)
    if context.scope is not None:
        updates.update(keep_unscoped_slides(phase.state, updates, context.scope))
    if STATE_FIELD_SLIDE_DRAFTS in review:
        await sync_rows_to_localized(db, context.project_id, updates)


__all__ = [
    "ContentPhaseUpdates",
    "ContentReviewContext",
    "RedraftTranslator",
    "build_presentation_review_updates",
    "review_content",
]
