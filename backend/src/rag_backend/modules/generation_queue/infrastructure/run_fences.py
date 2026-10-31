"""SQL fences over the generation runs that own a carousel's LangGraph thread.

Writers and the checkpoint prune fence their statements on these ``EXISTS``
expressions atomically, not only with a read before them.
"""

from __future__ import annotations

from collections.abc import Collection

from sqlalchemy import ColumnElement, exists, select

from rag_backend.modules.generation_queue.constants import (
    ACTIVE_STATUSES,
    HELD_STATUSES,
)
from rag_backend.modules.generation_queue.infrastructure.models import (
    GenerationRunModel,
)

__all__ = ["project_has_active_run", "project_has_held_run"]


def _project_has_run_in(
    project_id: ColumnElement[str], statuses: Collection[str]
) -> ColumnElement[bool]:
    return exists(
        select(GenerationRunModel.id).where(
            GenerationRunModel.carousel_project_id == project_id,
            GenerationRunModel.status.in_(list(statuses)),
        )
    )


def project_has_active_run(project_id: ColumnElement[str]) -> ColumnElement[bool]:
    """SQL ``EXISTS`` an active generation run for ``project_id`` (a column).

    Lets a writer fence its own UPDATE on the queue's ownership atomically
    (``WHERE NOT project_has_active_run(...)``), not only with a read before it.
    """
    return _project_has_run_in(project_id, ACTIVE_STATUSES)


def project_has_held_run(project_id: ColumnElement[str]) -> ColumnElement[bool]:
    """SQL ``EXISTS`` a queued, running, waiting or dead-lettered run.

    Each of those runs resumes the carousel's LangGraph thread from its
    checkpoint later, so the checkpoint prune keeps such a thread whole.
    """
    return _project_has_run_in(project_id, HELD_STATUSES)
