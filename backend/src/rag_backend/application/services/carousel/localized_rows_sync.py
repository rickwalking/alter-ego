"""Keep the slide rows on the validated localized copy (AE-0401).

The renderer, the export and the Telegram issue list read the
``carousel_slides`` rows; the gates validate the checkpoint's
``localized_slides``. The rows were written from ``slide_drafts`` (whose body
falls back to the long multi-paragraph ``draft_text``) and the localized copy
was projected onto them only on owner edits, so prod 98a2e2f0 validated short
copy while it rendered 368-772 character bodies with em dashes.

``sync_rows_to_localized`` projects the localized copy onto the rows every
time it is (re)built or changed: content and design artifacts, the gate
repair and the slide model fix. The rows, ``localized_slides`` and the
validation report then describe the same text.
"""

from __future__ import annotations

from collections.abc import Mapping

from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.application.services.carousel.editorial_distribution_persist import (
    LocalizedCopyProjection,
    project_localized_copy_to_database,
)
from rag_backend.domain.constants.workflow_state_fields import (
    STATE_FIELD_LOCALIZED_SLIDES,
)


def localized_records(values: Mapping[str, object]) -> list[dict[str, object]]:
    """The localized slides of a state or a state patch (empty when absent)."""
    raw = values.get(STATE_FIELD_LOCALIZED_SLIDES)
    if not isinstance(raw, list):
        return []
    return [dict(slide) for slide in raw if isinstance(slide, Mapping)]


async def sync_rows_to_localized(
    db: AsyncSession | None, project_id: str, values: Mapping[str, object]
) -> tuple[int, ...]:
    """Project ``values``' localized copy onto the rows; the slides written."""
    records = localized_records(values)
    if db is None or not project_id or not records:
        return ()
    return await project_localized_copy_to_database(
        LocalizedCopyProjection(db=db, project_id=project_id, localized_slides=records)
    )


__all__ = ["localized_records", "sync_rows_to_localized"]
