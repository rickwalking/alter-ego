"""One-shot: add ``carousel_projects.archived_at`` on prod.

Usage (in the freshly built backend image, Postgres up, app stack down):
    python -m rag_backend.scripts.carousel_archived_at --apply --verify
    python -m rag_backend.scripts.carousel_archived_at --verify

Exit codes: 0 ok, 1 ``--verify`` found the column or its index missing,
2 usage error. Safe to re-run: an existing column and index are left alone, and
a database that is not Postgres is a no-op.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncEngine

from rag_backend.infrastructure.database import carousel_archived_at
from rag_backend.scripts.cli_support import (
    EXIT_USAGE,
    GuardedCli,
    run_guarded_cli,
    run_on_own_engine,
)

EXIT_OK = 0
EXIT_VERIFY_FAILED = 1
_ERR_NO_MODE = "choose --apply and/or --verify"

__all__ = ["EXIT_OK", "EXIT_USAGE", "EXIT_VERIFY_FAILED", "main", "run_modes"]


def build_parser() -> argparse.ArgumentParser:
    """CLI flags; ``--apply`` and ``--verify`` combine."""
    parser = argparse.ArgumentParser(prog="carousel_archived_at", description=__doc__)
    parser.add_argument("--apply", action="store_true", help="add the column and index")
    parser.add_argument("--verify", action="store_true", help="gate on both existing")
    return parser


def _print(report: carousel_archived_at.ArchivedAtReport) -> None:
    for line in carousel_archived_at.format_report(report):
        print(line)


async def run_modes(engine: AsyncEngine, args: argparse.Namespace) -> int:
    """Apply then verify, as asked; the exit code reflects ``--verify``."""
    if args.apply:
        _print(await carousel_archived_at.apply(engine))
    if not args.verify:
        return EXIT_OK
    report = await carousel_archived_at.verify(engine)
    _print(report)
    return EXIT_VERIFY_FAILED if report.missing else EXIT_OK


def _mode_error(args: argparse.Namespace) -> str | None:
    """The usage error when neither mode is chosen."""
    if args.apply or args.verify:
        return None
    return _ERR_NO_MODE


async def _run_on_own_engine(args: argparse.Namespace) -> int:
    """Run the modes on a dedicated engine; only the column and index change."""
    return await run_on_own_engine(lambda engine: run_modes(engine, args))


def main(argv: Sequence[str] | None = None) -> int:
    """Parse flags, run, return the process exit code."""
    return run_guarded_cli(
        GuardedCli(parser=build_parser(), validate=_mode_error, run=_run_on_own_engine),
        argv,
    )


if __name__ == "__main__":
    sys.exit(main())
