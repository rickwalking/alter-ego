"""In-process registry of the coarse run stage per project (AE-0315).

The coarse stage (``generating`` → ``validating`` → ``persisting``) is
deliberately NOT persisted (only ``run_started_at``/``run_heartbeat_at``/
``run_epoch`` are columns): it is emitted at stage boundaries by the
background resume task and mirrored here so the workflow state response can
report it while ``phase_status == in_progress``. After a process restart the
registry is empty and readers fall back to ``generating`` — the reload path
reconstructs the banner from ``run_started_at`` alone, so no client depends
on having witnessed the ``run.started`` SSE event.
"""

from __future__ import annotations

from rag_backend.domain.constants.carousel_run import RUN_STAGE_GENERATING

_run_stages: dict[str, str] = {}


def set_run_stage(project_id: str, stage: str) -> None:
    """Record the current coarse stage for an active run."""
    _run_stages[project_id] = stage


def get_run_stage(project_id: str) -> str:
    """Current coarse stage; ``generating`` when unknown (restart/reload)."""
    return _run_stages.get(project_id, RUN_STAGE_GENERATING)


def clear_run_stage(project_id: str) -> None:
    """Drop the stage entry when a run finishes (any reason)."""
    _run_stages.pop(project_id, None)


__all__ = ["clear_run_stage", "get_run_stage", "set_run_stage"]
