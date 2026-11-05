"""The final-review refresh part of the generation queue fakes."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from uuid import UUID

from rag_backend.modules.generation_queue.constants import (
    PAYLOAD_MANUAL_PRIORITY,
    WAITING_STATUSES,
)
from rag_backend.modules.generation_queue.domain.models import GenerationRun


class RaisingStore:
    """``GenerationRunStore.raise_priority`` over a store's ``runs``."""

    runs: dict[UUID, GenerationRun]

    async def raise_priority(
        self, dedupe_key: str, priority: int
    ) -> GenerationRun | None:
        """Raise the waiting run with the key; a running one is left alone."""
        for run in self.runs.values():
            if run.dedupe_key == dedupe_key and run.status.value in WAITING_STATUSES:
                payload = {**run.payload, PAYLOAD_MANUAL_PRIORITY: priority}
                self.runs[run.id] = replace(run, payload=payload)
                return self.runs[run.id]
        return None


@dataclass(kw_only=True)
class RaisingQueue:
    """``JobQueue.raise_priority``, recording the raised runs."""

    raised: list[UUID] = field(default_factory=list)

    async def raise_priority(self, run: GenerationRun) -> None:
        """Record the raised job."""
        self.raised.append(run.id)


@dataclass(kw_only=True)
class RefreshSource:
    """``ActiveAutopilotSource.review_refresh_run_ids`` from a configured list."""

    refreshes: list[tuple[str, str | None]] = field(default_factory=list)

    async def review_refresh_run_ids(self, limit: int) -> list[tuple[str, str | None]]:
        """The configured final-review refreshes."""
        return self.refreshes[:limit]
