"""Composition-root factory for the stale-run reaper (AE-0315).

Builds the infrastructure reaper with its Settings-derived thresholds and a
checkpoint phase-status reader over the app's LangGraph checkpointer, so the
worker/application layer keeps depending only on the domain protocol.
"""

from __future__ import annotations

from rag_backend.agents.carousel_workflow import CarouselWorkflowEngine
from rag_backend.domain.protocols.carousel_run import (
    CarouselCheckpointPhaseStatusReader,
    CarouselStaleRunReaper,
)
from rag_backend.infrastructure.config.settings import Settings
from rag_backend.infrastructure.database.carousel_run_reaper import (
    CarouselRunReaperConfig,
    CarouselRunReaperRepository,
)


def _build_checkpoint_status_reader(
    checkpointer: object | None,
) -> CarouselCheckpointPhaseStatusReader | None:
    """Read-only engine over the shared checkpointer (parked-state mirror)."""
    if checkpointer is None:
        return None
    engine = CarouselWorkflowEngine(checkpointer=checkpointer)

    async def _read_phase_status(project_id: str) -> str | None:
        state = await engine.get_state(project_id)
        if state is None:
            return None
        return str(state.get("phase_status", "")) or None

    return _read_phase_status


def build_stale_run_reaper(
    settings: Settings,
    checkpointer: object | None,
) -> CarouselStaleRunReaper:
    """Assemble the reaper from Settings + the app checkpointer."""
    return CarouselRunReaperRepository(
        CarouselRunReaperConfig(
            heartbeat_stale_seconds=settings.workflow_run_heartbeat_stale_seconds,
            reap_observations=settings.workflow_run_reap_observations,
            overdue_minutes=settings.workflow_run_overdue_minutes,
        ),
        checkpoint_reader=_build_checkpoint_status_reader(checkpointer),
    )


__all__ = ["build_stale_run_reaper"]
