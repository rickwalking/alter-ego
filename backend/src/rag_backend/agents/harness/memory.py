"""Shared Deep Agents harness — per-agent memory loading (AE-0248).

Resolves the per-agent ``AGENTS.md`` memory files passed to
``create_deep_agent(memory=...)``. Today this is a thin, generic resolver: it
keeps only the paths that actually exist, so a missing memory file degrades to
"no memory" instead of failing the build. Per-agent wiring of concrete memory
paths lands in AE-0250; the harness just provides the resolver surface.

Kept generic — no carousel/chat domain coupling.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path


def resolve_memory_paths(paths: Sequence[str]) -> list[str]:
    """Return the subset of ``paths`` that point at existing files.

    Missing memory files are dropped rather than raising, so an agent without a
    provisioned ``AGENTS.md`` still builds (with no memory).
    """
    return [path for path in paths if Path(path).is_file()]


__all__ = ["resolve_memory_paths"]
