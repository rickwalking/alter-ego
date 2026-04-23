"""Shared progress-publishing helper.

Every phase calls `set_progress` at its entry point so the frontend's
polling `/status` endpoint shows a human-readable label ("Drafting
bilingual slide content") instead of the raw enum value.
"""

from __future__ import annotations

from rag_backend.domain.models import CarouselProject
from rag_backend.domain.protocols import CarouselRepository


async def set_progress(
    project: CarouselProject,
    *,
    repo: CarouselRepository,
    label: str,
    current: int | None = None,
    total: int | None = None,
    detail: str | None = None,
) -> CarouselProject:
    """Persist a fine-grained progress payload and return the updated project."""
    payload: dict[str, str | int] = {
        "phase": project.status.value,
        "label": label,
    }
    if current is not None:
        payload["current"] = current
    if total is not None:
        payload["total"] = total
    if detail:
        payload["detail"] = detail
    project.phase_progress = payload
    return await repo.update_project(project)
