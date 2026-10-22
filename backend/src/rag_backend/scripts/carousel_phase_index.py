"""One-shot: create the carousel_projects (phase_status, current_phase) index.

Usage (in the freshly built backend image, Postgres up, app stack down):
    python -m rag_backend.scripts.carousel_phase_index --apply --verify
    python -m rag_backend.scripts.carousel_phase_index --verify

Exit codes: 0 ok, 1 ``--verify`` found no valid index, 2 usage error. Safe to
re-run: an existing index is left alone, and a database
that is not Postgres is a no-op.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from rag_backend.infrastructure.config.settings import get_settings
from rag_backend.infrastructure.database import carousel_phase_index

EXIT_OK = 0
EXIT_VERIFY_FAILED = 1
EXIT_USAGE = 2


def build_parser() -> argparse.ArgumentParser:
    """CLI flags; ``--apply`` and ``--verify`` combine."""
    parser = argparse.ArgumentParser(prog="carousel_phase_index", description=__doc__)
    parser.add_argument("--apply", action="store_true", help="create the index")
    parser.add_argument("--verify", action="store_true", help="gate on a valid index")
    return parser


def _print(report: carousel_phase_index.PhaseIndexReport) -> None:
    for line in carousel_phase_index.format_report(report):
        print(line)


async def run_modes(engine: AsyncEngine, args: argparse.Namespace) -> int:
    """Apply then verify, as asked; the exit code reflects ``--verify``."""
    if args.apply:
        _print(await carousel_phase_index.apply(engine))
    if not args.verify:
        return EXIT_OK
    report = await carousel_phase_index.verify(engine)
    _print(report)
    if report.supported and not report.present:
        return EXIT_VERIFY_FAILED
    return EXIT_OK


async def _main(args: argparse.Namespace) -> int:
    """Uses its own engine and no ``create_all``: only the index is touched."""
    engine = create_async_engine(
        get_settings().database_url, pool_pre_ping=True, hide_parameters=True
    )
    try:
        return await run_modes(engine, args)
    finally:
        await engine.dispose()


def main(argv: Sequence[str] | None = None) -> int:
    """Parse flags, run, return the process exit code."""
    args = build_parser().parse_args(argv)
    if not (args.apply or args.verify):
        print("ERROR: choose --apply and/or --verify", file=sys.stderr)
        return EXIT_USAGE
    return asyncio.run(_main(args))


if __name__ == "__main__":
    sys.exit(main())
