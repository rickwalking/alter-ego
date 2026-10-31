"""The owner's recent slide-1 openings, for hook diversity.

The POV hook prompt receives the headings as forbidden reuses, candidates that
repeat a recent opening are dropped before the owner ever sees them, and the
owner's opening count seeds the rotation: it grows by one per carousel, so
consecutive carousels never pick the same candidate. The read sits behind the
domain ``RecentHookReader`` port: the application layer stays free of
infrastructure imports (import-linter contract).
"""

from __future__ import annotations

from rag_backend.domain.protocols.recent_hooks import (
    RecentHookQuery,
    RecentHookReader,
    RecentHooks,
)

_EMPTY = RecentHooks(headings=(), total=0)


def _normalized(text: str) -> str:
    return " ".join(text.lower().split())


def drop_reused_openings(candidates: list[str], recent: tuple[str, ...]) -> list[str]:
    """Candidates that do not repeat a recent opening (all, when all repeat)."""
    blocked = {_normalized(opening) for opening in recent}
    fresh = [text for text in candidates if _normalized(text) not in blocked]
    return fresh or candidates


async def load_recent_hooks(
    reader: RecentHookReader | None, project_id: str
) -> RecentHooks:
    """The recent openings through the port; empty without a reader or id."""
    if reader is None or not project_id:
        return _EMPTY
    return await reader.recent_hooks(RecentHookQuery(project_id=project_id))


__all__ = ["drop_reused_openings", "load_recent_hooks"]
