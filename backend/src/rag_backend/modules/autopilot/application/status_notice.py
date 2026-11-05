"""Build the owner's status notice from its outbox event. Pure."""

from __future__ import annotations

from dataclasses import dataclass

from rag_backend.modules.autopilot.domain.dead_letter import status_body
from rag_backend.modules.autopilot.domain.escalation_detail import detail_of
from rag_backend.modules.autopilot.domain.messages import (
    StatusCopy,
    days_remaining_of,
    owner_ui_link,
    permalink_of,
    reason_of,
)
from rag_backend.modules.autopilot.domain.models import AutopilotRun
from rag_backend.modules.autopilot.domain.notify import (
    AutopilotOutboxEvent,
    StatusNotice,
)
from rag_backend.modules.autopilot.domain.published_copy import post_extras_of
from rag_backend.modules.autopilot.domain.status_keyboard import status_keyboard


@dataclass(frozen=True, kw_only=True)
class StatusJob:
    """One status event, its run and the notice kind it asks for."""

    event: AutopilotOutboxEvent
    run: AutopilotRun
    kind: str


def status_notice(chat_id: str, base_url: str, job: StatusJob) -> StatusNotice:
    """The notice ``job`` sends to ``chat_id``."""
    return StatusNotice(
        chat_id=chat_id,
        run_id=job.run.run_id,
        text=status_body(job.kind, _copy(base_url, job.event, job.run)),
        keyboard=status_keyboard(job.kind, job.run.run_id, job.event.payload),
    )


def _copy(base_url: str, event: AutopilotOutboxEvent, run: AutopilotRun) -> StatusCopy:
    project_id = run.carousel_project_id or ""
    return StatusCopy(
        reason=reason_of(event.payload),
        link=owner_ui_link(base_url, project_id),
        permalink=permalink_of(event.payload),
        days_remaining=days_remaining_of(event.payload),
        extras=post_extras_of(event.payload),
        detail=detail_of(event.payload),
    )


__all__ = ["StatusJob", "status_notice"]
