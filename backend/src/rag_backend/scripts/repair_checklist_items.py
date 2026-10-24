"""Move edited checklist text from the hidden item body into the displayed line.

One-off operator action for one carousel. A checklist slide shows each item's
title; the editor used to write the body, so an edited item kept its old text on
the slide. For every checklist slide item (PT and EN) whose non-empty body differs
from its title, the repair sets the title to the body and clears the body.

    python -m rag_backend.scripts.repair_checklist_items --project <id> --dry-run
    python -m rag_backend.scripts.repair_checklist_items --project <id> --apply

The default is ``--dry-run`` (lists the moves, writes nothing). ``--apply`` writes
through the same slide-edit service as ``PATCH /api/carousels/{id}/slides`` (the
checkpoint follows), then republishes the carousel. Idempotent: a repaired item
has an empty body, so a second run finds nothing to move. Run it inside the prod
backend container.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from rag_backend.scripts.cli_support import (
    EXIT_USAGE,
    GuardedCli,
    run_guarded_cli,
    run_on_own_engine,
)

if TYPE_CHECKING:
    from rag_backend.bootstrap.carousel_checklist_repair import ChecklistRepairReport

EXIT_OK = 0
EXIT_FAILED = 1
ERR_BAD_PROJECT_ID = "--project must be a carousel UUID"

__all__ = ["EXIT_FAILED", "EXIT_OK", "EXIT_USAGE", "format_report", "main"]


def build_parser() -> argparse.ArgumentParser:
    """CLI flags; the default is the read-only ``--dry-run``."""
    parser = argparse.ArgumentParser(prog="repair_checklist_items", description=__doc__)
    parser.add_argument("--project", required=True, metavar="ID", help="carousel id")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--apply", action="store_true", help="edit and republish")
    mode.add_argument("--dry-run", action="store_true", help="list only (default)")
    return parser


def format_report(report: ChecklistRepairReport) -> list[str]:
    """Human-readable lines of a dry run or an apply."""
    lines = [
        f"summary: project={report.project_id} moves={len(report.moves)} "
        f"applied={report.applied} republished={report.republished} "
        f"errors={len(report.errors)}"
    ]
    lines.extend(
        f"  slide {move.slide_index} {move.locale} {move.list_key}[{move.item_index}]"
        f": {move.old_title!r} -> {move.new_title!r}"
        for move in report.moves
    )
    lines.extend(f"  error {error}" for error in report.errors)
    return lines


def _mode_error(args: argparse.Namespace) -> str | None:
    """The usage error when ``--project`` is not a UUID."""
    try:
        UUID(args.project)
    except ValueError:
        return ERR_BAD_PROJECT_ID
    return None


async def _run_modes(engine: AsyncEngine, args: argparse.Namespace) -> int:
    """Plan or apply on the given engine, print the report, return the exit code."""
    from rag_backend.bootstrap.carousel_checklist_repair import (
        ChecklistRepairRequest,
        repair_checklist_items,
    )

    maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    report = await repair_checklist_items(
        maker, ChecklistRepairRequest(project_id=UUID(args.project), apply=args.apply)
    )
    for line in format_report(report):
        print(line)
    return EXIT_FAILED if report.errors else EXIT_OK


async def _run_on_own_engine(args: argparse.Namespace) -> int:
    """Run on a dedicated engine (no ``create_all``)."""
    return await run_on_own_engine(lambda engine: _run_modes(engine, args))


def main(argv: Sequence[str] | None = None) -> int:
    """Parse flags, plan or repair, return the process exit code."""
    return run_guarded_cli(
        GuardedCli(parser=build_parser(), validate=_mode_error, run=_run_on_own_engine),
        argv,
    )


if __name__ == "__main__":
    sys.exit(main())
