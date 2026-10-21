"""One-shot: make the palette timestamps timezone-aware (Pedro's decision).

Usage (in the freshly built backend image, Postgres up, app stack down):
    python -m rag_backend.scripts.palette_timestamptz --apply --verify
    python -m rag_backend.scripts.palette_timestamptz --verify

Exit codes: 0 ok, 1 ``--verify`` found a naive ``palettes`` timestamp column,
2 usage error. Safe to re-run: an aware column is left alone, and a database
that is not Postgres is a no-op.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from rag_backend.infrastructure.config.settings import get_settings
from rag_backend.infrastructure.database import palette_timestamptz

EXIT_OK = 0
EXIT_VERIFY_FAILED = 1
EXIT_USAGE = 2


def build_parser() -> argparse.ArgumentParser:
    """CLI flags; ``--apply`` and ``--verify`` combine."""
    parser = argparse.ArgumentParser(prog="palette_timestamptz", description=__doc__)
    parser.add_argument("--apply", action="store_true", help="ALTER naive columns")
    parser.add_argument("--verify", action="store_true", help="gate on zero naive")
    return parser


def _print(report: palette_timestamptz.TimestamptzReport) -> None:
    for line in palette_timestamptz.format_report(report):
        print(line)


async def run_modes(engine: AsyncEngine, args: argparse.Namespace) -> int:
    """Apply then verify, as asked; the exit code reflects ``--verify``."""
    if args.apply:
        _print(await palette_timestamptz.apply(engine))
    if not args.verify:
        return EXIT_OK
    report = await palette_timestamptz.verify(engine)
    _print(report)
    return EXIT_VERIFY_FAILED if report.still_naive else EXIT_OK


async def _main(args: argparse.Namespace) -> int:
    """Uses its own engine and no ``create_all``: only the two palette columns are
    altered.
    """
    engine = create_async_engine(get_settings().database_url, pool_pre_ping=True)
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
