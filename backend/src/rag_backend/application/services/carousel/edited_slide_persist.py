"""Persist reviewer-edited slide copy onto the rendered slide rows.

Prod carousel 8e350d6e: the reviewer fixed slide copy at the content gate via
``edited_localized_slides``, but the ``carousel_slides`` rows (what the renderer,
finalize and republish read) kept the old copy. The graph applies edits to the
workflow state only, and nothing re-projected them onto the rows.

Before the workflow resumes, the edited ``presentation_pt``/``presentation_en``
copy of every edited slide is projected onto its row (heading, body, structured
items and ``translation_en``), so the next render uses it. Images, image
prompts and long-form notes are untouched.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.application.services.carousel.editorial_distribution_persist import (
    LocalizedCopyProjection,
    project_localized_copy_to_database,
)
from rag_backend.application.services.carousel.presentation_review import (
    WORKFLOW_STATE_LOCALIZED_SLIDES_KEY,
)
from rag_backend.application.services.carousel.presentation_review_edits import (
    apply_localized_slide_edits,
)
from rag_backend.domain.constants.carousel_workflow import (
    EDITED_SLIDES_ALLOWED_PHASES,
    STRUCTURED_FEEDBACK_EDITED_SLIDES_KEY,
)
from rag_backend.domain.constants.workflow_state_fields import STATE_FIELD_SLIDE_INDEX

_CURRENT_PHASE_KEY = "current_phase"


@dataclass(frozen=True)
class EditedSlidePersistCommand:
    """A resume submission that may carry reviewer slide edits."""

    db: AsyncSession | None
    project_id: str
    prior: Mapping[str, object] | None
    structured_feedback: Mapping[str, object] | None


def _edited_slides(
    structured_feedback: Mapping[str, object] | None,
) -> list[dict[str, object]]:
    if structured_feedback is None:
        return []
    raw = structured_feedback.get(STRUCTURED_FEEDBACK_EDITED_SLIDES_KEY)
    if not isinstance(raw, list):
        return []
    return [dict(slide) for slide in raw if isinstance(slide, Mapping)]


async def persist_edited_slide_copy(
    command: EditedSlidePersistCommand,
) -> tuple[int, ...]:
    """Project edited slide copy onto the slide rows; return updated numbers."""
    edited = _edited_slides(command.structured_feedback)
    if command.db is None or command.prior is None or not edited:
        return ()
    phase = str(command.prior.get(_CURRENT_PHASE_KEY) or "")
    if phase not in EDITED_SLIDES_ALLOWED_PHASES:
        return ()
    updates = apply_localized_slide_edits(command.prior, edited)
    localized = updates.get(WORKFLOW_STATE_LOCALIZED_SLIDES_KEY)
    if not isinstance(localized, list):
        return ()
    edited_indices = {slide.get(STATE_FIELD_SLIDE_INDEX) for slide in edited}
    return await project_localized_copy_to_database(
        LocalizedCopyProjection(
            db=command.db,
            project_id=command.project_id,
            localized_slides=[
                slide
                for slide in localized
                if isinstance(slide, dict)
                and slide.get(STATE_FIELD_SLIDE_INDEX) in edited_indices
            ],
        )
    )


__all__ = ["EditedSlidePersistCommand", "persist_edited_slide_copy"]
