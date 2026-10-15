"""Langfuse trace scope for one run-owned resume (AE-0390).

The application-layer run wrapper reaches the tracing scope through the
editorial facade, like the run fence, so no application -> infrastructure
edge is added for the architecture ratchet.
"""

from __future__ import annotations

from contextlib import AbstractContextManager

from rag_backend.infrastructure.monitoring_langfuse import (
    WorkflowTraceScope,
    workflow_trace_scope,
)
from rag_backend.modules.editorial.infrastructure.carousel_run_progress import (
    read_project_owner_id,
)


async def open_run_trace_scope(
    project_id: str,
    fallback_user_id: str,
) -> AbstractContextManager[None]:
    """Scope the run's phase traces to the project and its owner.

    The agent name is left to the caller's enclosing scope (the autopilot
    driver sets ``autopilot``; the HTTP path takes the default).
    """
    owner = await read_project_owner_id(project_id)
    return workflow_trace_scope(
        WorkflowTraceScope(project_id=project_id, user_id=owner or fallback_user_id)
    )


__all__ = ["open_run_trace_scope"]
