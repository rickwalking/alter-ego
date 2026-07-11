"""Run-epoch fencing primitives for carousel runs (AE-0315).

The monotonic ``run_epoch`` column on ``carousel_projects`` is the fencing
token that serializes a reaped (zombie) run against its replacement: every
run-owned execution context captures the row's epoch at run start into the
``carousel_run_epoch_var`` contextvar; enforcement layers compare the captured
epoch against the row's *current* epoch and reject on mismatch. The contextvar
is set ONLY inside run-owned contexts (the background resume task and its
heartbeat task) — user/API/admin/operator writes never set it, so they can
never be falsely rejected by a concurrent reap (pinned cold-critic r6).

This module is dependency-free (domain layer) so every layer — agents
(checkpoint-commit boundary), infrastructure (flush guard, raw-SQL guards),
application (run task) — can import the same fence without violating the
architecture ratchet. The checkpoint-commit boundary additionally needs a
DB read of the current epoch; the concrete async reader is *registered* here
by the infrastructure layer at import time (dependency inversion — the domain
holds only the seam).
"""

from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass
from typing import Protocol

from rag_backend.domain.constants.carousel_run import ERR_STALE_RUN_EPOCH


@dataclass(frozen=True)
class CarouselRunContext:
    """The run-ownership token: project + the epoch captured at run start."""

    project_id: str
    epoch: int


carousel_run_epoch_var: ContextVar[CarouselRunContext | None] = ContextVar(
    "carousel_run_epoch",
    default=None,
)


class StaleRunEpochError(Exception):
    """A run-owned write was rejected because the row's epoch moved on."""

    def __init__(self, project_id: str) -> None:
        super().__init__(ERR_STALE_RUN_EPOCH)
        self.project_id = project_id


def current_run_context() -> CarouselRunContext | None:
    """Return the run-ownership token for the current execution context."""
    return carousel_run_epoch_var.get()


class RunEpochReader(Protocol):
    """Async reader of a project's current ``run_epoch`` (None when absent)."""

    async def __call__(self, project_id: str) -> int | None:
        """Return the row's current epoch, or ``None`` when the row is gone."""
        ...


class _EpochReaderRegistry:
    """Module-level DI seam holding the registered epoch reader."""

    reader: RunEpochReader | None = None


def register_run_epoch_reader(reader: RunEpochReader | None) -> None:
    """Register the concrete epoch reader (called by infrastructure on import)."""
    _EpochReaderRegistry.reader = reader


async def ensure_checkpoint_commit_allowed(project_id: str) -> None:
    """Fence the workflow engine's checkpoint-commit boundary (layer b).

    No-op when the current context is not run-owned, owns a different
    project, or no reader is registered (e.g. unit tests exercising the
    engine directly). Raises :class:`StaleRunEpochError` when the captured
    epoch no longer matches the row's current epoch.
    """
    ctx = carousel_run_epoch_var.get()
    reader = _EpochReaderRegistry.reader
    if ctx is None or ctx.project_id != project_id or reader is None:
        return
    current = await reader(project_id)
    if current is not None and current != ctx.epoch:
        raise StaleRunEpochError(project_id)


__all__ = [
    "CarouselRunContext",
    "RunEpochReader",
    "StaleRunEpochError",
    "carousel_run_epoch_var",
    "current_run_context",
    "ensure_checkpoint_commit_allowed",
    "register_run_epoch_reader",
]
