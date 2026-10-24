"""One-shot: create the carousel generation queue's tables on prod.

Usage (in the freshly built backend image, Postgres up, app stack down):
    python -m rag_backend.scripts.generation_queue_schema --apply --verify
    python -m rag_backend.scripts.generation_queue_schema --verify

Creates ``generation_runs`` and its indexes, then installs PgQueuer's tables (or
upgrades them to the pinned version). Exit codes: 0 ok, 1 ``--verify`` found an
object missing, 2 usage error. Safe to re-run; a database that is not Postgres is
a no-op.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncEngine

from rag_backend.modules.generation_queue.public import (
    QueueSchemaReport,
    apply_queue_schema,
    format_queue_schema_report,
    verify_queue_schema,
)
from rag_backend.scripts.cli_support import (
    EXIT_USAGE,
    ApplyVerifyScript,
    apply_verify_main,
)

EXIT_OK = 0
EXIT_VERIFY_FAILED = 1

__all__ = ["EXIT_OK", "EXIT_USAGE", "EXIT_VERIFY_FAILED", "main", "run_modes"]


def _print(report: QueueSchemaReport) -> None:
    for line in format_queue_schema_report(report):
        print(line)


async def run_modes(engine: AsyncEngine, args: argparse.Namespace) -> int:
    """Apply then verify, as asked; the exit code reflects ``--verify``."""
    if args.apply:
        _print(await apply_queue_schema(engine))
    if not args.verify:
        return EXIT_OK
    report = await verify_queue_schema(engine)
    _print(report)
    return EXIT_VERIFY_FAILED if report.missing else EXIT_OK


def main(argv: Sequence[str] | None = None) -> int:
    """Parse flags, run, return the process exit code."""
    return apply_verify_main(
        ApplyVerifyScript("generation_queue_schema", __doc__, run_modes), argv
    )


if __name__ == "__main__":
    sys.exit(main())
