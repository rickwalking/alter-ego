"""One-shot: hand the generation queue's pending work back before a revert.

Usage (on the droplet, with the CURRENT image, after
``docker compose stop -t 300 generation-worker`` and before the revert deploys):
    python -m rag_backend.scripts.generation_queue_rollback --verify
    python -m rag_backend.scripts.generation_queue_rollback --apply

``--verify`` only counts what ``--apply`` would hand back. Exit codes: 0 ok,
2 usage error. Safe to re-run.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncEngine

from rag_backend.modules.generation_queue.public import (
    count_queue_hand_back,
    hand_back_queue,
)
from rag_backend.scripts.cli_support import (
    EXIT_USAGE,
    ApplyVerifyScript,
    apply_verify_main,
)

if TYPE_CHECKING:
    from rag_backend.modules.generation_queue.infrastructure.rollback import (
        RollbackReport,
    )

EXIT_OK = 0
_REPORT = (
    "generation queue rollback ({mode}): {projects} project(s) back at their gate,"
    " {runs} run(s) cancelled"
)
_APPLIED = "applied"
_PENDING = "would hand back"

__all__ = ["EXIT_OK", "EXIT_USAGE", "main", "run_modes"]


def _print(mode: str, report: RollbackReport) -> None:
    print(
        _REPORT.format(
            mode=mode, projects=report.projects_released, runs=report.runs_cancelled
        )
    )


async def run_modes(engine: AsyncEngine, args: argparse.Namespace) -> int:
    """Count, or hand back, as asked."""
    if args.verify and not args.apply:
        _print(_PENDING, await count_queue_hand_back(engine))
    if args.apply:
        _print(_APPLIED, await hand_back_queue(engine))
    return EXIT_OK


def main(argv: Sequence[str] | None = None) -> int:
    """Parse flags, run, return the process exit code."""
    return apply_verify_main(
        ApplyVerifyScript("generation_queue_rollback", __doc__, run_modes), argv
    )


if __name__ == "__main__":
    sys.exit(main())
