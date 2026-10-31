"""One-shot: add the four ``instagram_post_insights`` insight columns on prod.

Usage (in the freshly built backend image, Postgres up, app stack down):
    python -m rag_backend.scripts.ig_insight_columns --apply --verify
    python -m rag_backend.scripts.ig_insight_columns --verify

Exit codes: 0 ok, 1 ``--verify`` found a column missing on the existing table,
2 usage error. Safe to re-run: existing columns are left alone, and a database
without the table or that is not Postgres is a no-op.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncEngine

from rag_backend.infrastructure.database import ig_insight_columns
from rag_backend.scripts.cli_support import (
    EXIT_USAGE,
    ApplyVerifyScript,
    apply_verify_main,
)

EXIT_OK = 0
EXIT_VERIFY_FAILED = 1

__all__ = ["EXIT_OK", "EXIT_USAGE", "EXIT_VERIFY_FAILED", "main", "run_modes"]


def _report(report: ig_insight_columns.InsightColumnsReport) -> bool:
    """Print the report; True when a column is still missing."""
    print("\n".join(ig_insight_columns.format_report(report)))
    return bool(report.missing)


async def run_modes(engine: AsyncEngine, args: argparse.Namespace) -> int:
    """Apply then verify, as asked; only ``--verify`` can fail the exit code."""
    if args.apply:
        _report(await ig_insight_columns.apply(engine))
    if args.verify and _report(await ig_insight_columns.verify(engine)):
        return EXIT_VERIFY_FAILED
    return EXIT_OK


def main(argv: Sequence[str] | None = None) -> int:
    """Parse flags, run on an own engine, return the process exit code."""
    return apply_verify_main(
        ApplyVerifyScript("ig_insight_columns", __doc__, run_modes), argv
    )


if __name__ == "__main__":
    sys.exit(main())
