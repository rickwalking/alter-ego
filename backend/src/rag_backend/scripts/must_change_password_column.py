"""One-shot: add ``users.must_change_password`` on prod.

Usage (in the freshly built backend image, Postgres up, app stack down):
    python -m rag_backend.scripts.must_change_password_column --apply --verify
    python -m rag_backend.scripts.must_change_password_column --verify

Exit codes: 0 ok, 1 ``--verify`` found the column missing on the existing
table, 2 usage error. Safe to re-run: an existing column is left alone, and a
database without ``users`` or that is not Postgres is a no-op.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncEngine

from rag_backend.infrastructure.database import must_change_password_column
from rag_backend.scripts.cli_support import (
    EXIT_USAGE,
    ApplyVerifyScript,
    apply_verify_main,
)

EXIT_OK = 0
EXIT_VERIFY_FAILED = 1

__all__ = ["EXIT_OK", "EXIT_USAGE", "EXIT_VERIFY_FAILED", "main", "run_modes"]


def _print(report: must_change_password_column.FlagColumnReport) -> bool:
    """Print the report; True when the column is still missing."""
    print("\n".join(must_change_password_column.format_report(report)))
    return report.missing


async def run_modes(engine: AsyncEngine, args: argparse.Namespace) -> int:
    """Apply then verify, as asked; only ``--verify`` can fail the exit code."""
    if args.apply:
        _print(await must_change_password_column.apply(engine))
    if args.verify and _print(await must_change_password_column.verify(engine)):
        return EXIT_VERIFY_FAILED
    return EXIT_OK


def main(argv: Sequence[str] | None = None) -> int:
    """Parse flags, run on an own engine, return the process exit code."""
    return apply_verify_main(
        ApplyVerifyScript("must_change_password_column", __doc__, run_modes), argv
    )


if __name__ == "__main__":
    sys.exit(main())
