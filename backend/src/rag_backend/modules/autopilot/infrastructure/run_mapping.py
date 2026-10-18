"""Row <-> aggregate mapping for ``autopilot_runs``.

Split from ``repository.py`` so the adapter stays under 400 lines.
"""

from __future__ import annotations

from datetime import UTC, datetime

from rag_backend.modules.autopilot.domain.models import AutopilotRun, AutopilotRunState
from rag_backend.modules.autopilot.domain.notice_log import (
    dump_log,
    notice_log_is_empty,
    parse_stored,
)
from rag_backend.modules.autopilot.infrastructure.models import AutopilotRunModel


def run_row(run: AutopilotRun) -> AutopilotRunModel:
    """ORM row for a new run."""
    return AutopilotRunModel(
        id=run.run_id,
        carousel_project_id=run.carousel_project_id,
        topic_candidate_id=run.topic_candidate_id,
        state=run.state.value,
        state_reason=run.state_reason,
        publish_attempts=run.publish_attempts,
        start_attempts=run.start_attempts,
        telegram_message_ids=_stored_messages(run),
        ig_container_id=run.ig_container_id,
        ig_post_id=run.ig_post_id,
        ig_permalink=run.ig_permalink,
        ig_container_created_at=run.ig_container_created_at,
        rework_phase=run.rework_phase,
        rework_feedback=run.rework_feedback,
        escalated_version=run.escalated_version,
        pov_thesis=run.pov_thesis,
        scheduled_at=run.scheduled_at,
        cover_chosen=run.cover_chosen,
    )


def run_from_row(row: AutopilotRunModel) -> AutopilotRun:
    """Aggregate for a stored row. Timestamps come back timezone-aware."""
    log = parse_stored(row.telegram_message_ids)
    return AutopilotRun(
        run_id=row.id,
        topic_candidate_id=row.topic_candidate_id,
        carousel_project_id=row.carousel_project_id,
        state=AutopilotRunState(row.state),
        state_reason=row.state_reason,
        publish_attempts=row.publish_attempts,
        start_attempts=row.start_attempts,
        telegram_message_ids=log.message_ids,
        notice_log=log,
        ig_container_id=row.ig_container_id,
        ig_post_id=row.ig_post_id,
        ig_permalink=row.ig_permalink,
        ig_container_created_at=aware(row.ig_container_created_at),
        updated_at=aware(row.updated_at),
        rework_phase=row.rework_phase,
        rework_feedback=row.rework_feedback,
        escalated_version=row.escalated_version,
        pov_thesis=row.pov_thesis,
        scheduled_at=aware(row.scheduled_at),
        cover_chosen=bool(row.cover_chosen),
    )


def aware(value: datetime | None) -> datetime | None:
    """Treat a naive timestamp (SQLite) as UTC."""
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


def _stored_messages(run: AutopilotRun) -> list[int] | dict[str, object]:
    if notice_log_is_empty(run.notice_log):
        return list(run.telegram_message_ids)
    return dump_log(run.notice_log)
