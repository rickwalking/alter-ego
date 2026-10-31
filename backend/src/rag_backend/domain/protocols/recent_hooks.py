"""The owner's recent slide-1 openings port (hook voice diversity).

The POV hook prompt receives the headings as forbidden reuses so consecutive
carousels stop opening with the same formulas and phrases, and ``total`` (the
owner's slide-1 hook count, current project excluded) seeds the candidate
rotation: it grows by one per carousel, so consecutive picks never repeat. The
reader is implemented in infrastructure and injected at the composition edge.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from rag_backend.domain.constants.pov_prompts import RECENT_HOOK_LIMIT


@dataclass(frozen=True)
class RecentHookQuery:
    """One project asking for the openings of the owner's other carousels."""

    project_id: str
    limit: int = RECENT_HOOK_LIMIT


@dataclass(frozen=True)
class RecentHooks:
    """The owner's recent slide-1 openings (newest first) and their count."""

    headings: tuple[str, ...]
    total: int


class RecentHookReader(Protocol):
    """The owner's recent slide-1 openings, newest first."""

    async def recent_hooks(self, query: RecentHookQuery) -> RecentHooks:
        """Newest openings and the total; empty when the project is unknown."""
        ...


__all__ = ["RecentHookQuery", "RecentHookReader", "RecentHooks"]
