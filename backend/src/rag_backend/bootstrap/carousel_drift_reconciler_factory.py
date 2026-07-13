"""Composition-root factory for the AE-0311 drift reconciler.

Adapts the shared LangGraph checkpointer into a read/write gateway (the engine
``update_state`` wrapper is preserved) so the reconciler converges the
checkpoint without the application/infrastructure layer importing the agents
engine directly.
"""

from __future__ import annotations

from rag_backend.agents.carousel_workflow import CarouselWorkflowEngine
from rag_backend.domain.protocols.carousel_run import CarouselDriftReconciler
from rag_backend.infrastructure.database.carousel_drift_reconciler import (
    CarouselDriftReconcilerRepository,
)


class _EngineCheckpointGateway:
    """Checkpoint read/write over ``CarouselWorkflowEngine`` (as_node inferred)."""

    def __init__(self, engine: CarouselWorkflowEngine) -> None:
        self._engine = engine

    async def read_state(self, project_id: str) -> dict[str, object] | None:
        state = await self._engine.get_state(project_id)
        return dict(state) if state is not None else None

    async def write_state(self, project_id: str, values: dict[str, object]) -> None:
        await self._engine.update_state(project_id, values)


def build_drift_reconciler(
    checkpointer: object | None,
) -> CarouselDriftReconciler | None:
    """Assemble the reconciler over the app checkpointer (None when disabled)."""
    if checkpointer is None:
        return None
    engine = CarouselWorkflowEngine(checkpointer=checkpointer)
    return CarouselDriftReconcilerRepository(_EngineCheckpointGateway(engine))


__all__ = ["build_drift_reconciler"]
