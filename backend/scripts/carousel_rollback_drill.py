"""Carousel scaled-down rollback drill helpers (AE-0113 / ADR-0009 §2, §7).

This module provides the *automatable* pieces of the scaled-down rollback drill
mandated by ADR-0009 for the carousel workflow data:

  1. ``snapshot_carousel_state`` — capture the rollback-critical carousel
     workflow state for a project: the persisted project row's workflow fields
     (``workflow_status``, ``phase_status``, ``phase_progress``, ``lock_version``)
     plus the trace-correlated audit-log event sequence (the workflow "trace",
     keyed by ``aggregate_id`` = project id, ordered by version).

  2. ``compare_snapshots`` — deterministic trace-correlated smoke comparison:
     assert a post-restore snapshot is byte-identical to the pre-change
     snapshot. This is the executable compatibility test ADR-0009 §7 requires
     ("a rollback plan ... without an executable compatibility test SHALL be
     considered invalid").

The DB *restore* itself (pg_dump / pg_restore against a live PostgreSQL
instance) is operator-run and documented in
``docs/architecture/carousel-rollback-drill.md`` — CI here has no live
Postgres, so the restore step is documented-for-operator while the
snapshot + smoke-comparison logic is fully runnable (and is exercised by
``tests/integration/test_carousel_rollback_smoke.py`` against SQLite).

Scaled-down scope (ADR-0009 §2, §7): this is a database restore drill plus a
trace-correlated smoke comparison. It is NOT a full production-traffic rollback
drill, mixed-version test, or parity-alerting exercise — those are explicitly
out of scope for the recorded scaled-down + migrate-in-place track.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel
from rag_backend.infrastructure.database.models.workflow_audit_log import (
    WorkflowAuditLogModel,
)

# Aggregate type used for carousel projects in the workflow audit log.
AGGREGATE_TYPE_CAROUSEL = "project"


@dataclass(frozen=True)
class AuditEventSnapshot:
    """One trace-correlated audit event, normalized for comparison."""

    event_type: str
    version: int
    payload: dict[str, object]
    metadata: dict[str, object]


@dataclass(frozen=True)
class CarouselStateSnapshot:
    """Rollback-critical state for one carousel project."""

    project_id: str
    workflow_status: str
    phase_status: str
    phase_progress: dict[str, object] | None
    lock_version: int
    audit_trace: list[AuditEventSnapshot] = field(default_factory=list)


def _coerce_mapping(value: object) -> dict[str, object]:
    if isinstance(value, dict):
        return dict(value)
    return {}


async def snapshot_carousel_state(
    db: AsyncSession,
    project_id: str,
) -> CarouselStateSnapshot | None:
    """Capture rollback-critical workflow state + trace for one project.

    Returns ``None`` when the project does not exist (e.g. comparing a
    pre-restore baseline against a post-restore DB where the row was dropped).
    """
    project = await db.get(CarouselProjectModel, project_id)
    if project is None:
        return None

    result = await db.execute(
        select(WorkflowAuditLogModel)
        .where(WorkflowAuditLogModel.aggregate_id == project_id)
        .where(WorkflowAuditLogModel.aggregate_type == AGGREGATE_TYPE_CAROUSEL)
        .order_by(
            WorkflowAuditLogModel.version.asc(),
            WorkflowAuditLogModel.event_id.asc(),
        )
    )
    audit_trace = [
        AuditEventSnapshot(
            event_type=str(row.event_type),
            version=int(row.version),
            payload=_coerce_mapping(row.payload),
            metadata=_coerce_mapping(row.metadata_json),
        )
        for row in result.scalars().all()
    ]

    phase_progress_value: object = project.phase_progress
    phase_progress = (
        _coerce_mapping(phase_progress_value)
        if isinstance(phase_progress_value, dict)
        else None
    )

    return CarouselStateSnapshot(
        project_id=str(project.id),
        workflow_status=str(project.workflow_status or ""),
        phase_status=str(project.phase_status or ""),
        phase_progress=phase_progress,
        lock_version=int(project.lock_version or 1),
        audit_trace=audit_trace,
    )


@dataclass(frozen=True)
class SnapshotComparison:
    """Result of a trace-correlated smoke comparison."""

    matched: bool
    differences: list[str]


def compare_snapshots(
    baseline: CarouselStateSnapshot | None,
    restored: CarouselStateSnapshot | None,
) -> SnapshotComparison:
    """Deterministic smoke comparison of two carousel state snapshots.

    The drill invariant: after a database restore, the carousel workflow state
    and its trace-correlated audit sequence MUST be byte-identical to the
    pre-change baseline. Any difference is a rollback-correctness failure.
    """
    differences: list[str] = []
    if baseline is None or restored is None:
        if baseline is not restored:
            differences.append(
                f"presence mismatch: baseline={baseline is not None} "
                f"restored={restored is not None}"
            )
        return SnapshotComparison(matched=not differences, differences=differences)

    scalar_fields: tuple[tuple[str, object, object], ...] = (
        ("project_id", baseline.project_id, restored.project_id),
        ("workflow_status", baseline.workflow_status, restored.workflow_status),
        ("phase_status", baseline.phase_status, restored.phase_status),
        ("lock_version", baseline.lock_version, restored.lock_version),
        ("phase_progress", baseline.phase_progress, restored.phase_progress),
    )
    for field_name, base_value, restored_value in scalar_fields:
        if base_value != restored_value:
            differences.append(
                f"{field_name}: baseline={base_value!r} restored={restored_value!r}"
            )
    _diff_trace(differences, baseline.audit_trace, restored.audit_trace)
    return SnapshotComparison(matched=not differences, differences=differences)


def _diff_trace(
    differences: list[str],
    baseline: list[AuditEventSnapshot],
    restored: list[AuditEventSnapshot],
) -> None:
    if len(baseline) != len(restored):
        differences.append(
            f"audit_trace length: baseline={len(baseline)} restored={len(restored)}"
        )
        return
    for index, (base_event, restored_event) in enumerate(
        zip(baseline, restored, strict=True)
    ):
        if base_event != restored_event:
            differences.append(
                f"audit_trace[{index}]: baseline={base_event!r} "
                f"restored={restored_event!r}"
            )


__all__ = [
    "AGGREGATE_TYPE_CAROUSEL",
    "AuditEventSnapshot",
    "CarouselStateSnapshot",
    "SnapshotComparison",
    "compare_snapshots",
    "snapshot_carousel_state",
]
