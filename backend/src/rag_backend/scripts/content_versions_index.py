"""One-shot: make the ``content_versions`` unique index per content (Pedro's decision).

Usage (in the freshly built backend image, Postgres up, app stack down):
    python -m rag_backend.scripts.content_versions_index --apply --verify
    python -m rag_backend.scripts.content_versions_index --verify

Exit codes: 0 ok, 1 ``--verify`` found the global index or no per-content one,
2 usage error. Safe to re-run: a fixed schema is left alone, and a database
that is not Postgres is a no-op.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from rag_backend.infrastructure.config.settings import get_settings
from rag_backend.infrastructure.database import content_versions_index

EXIT_OK = 0
EXIT_VERIFY_FAILED = 1
EXIT_USAGE = 2


def build_parser() -> argparse.ArgumentParser:
    """CLI flags; ``--apply`` and ``--verify`` combine."""
    parser = argparse.ArgumentParser(prog="content_versions_index", description=__doc__)
    parser.add_argument("--apply", action="store_true", help="fix the unique index")
    parser.add_argument("--verify", action="store_true", help="gate on the fix")
    return parser


def _print(report: content_versions_index.IndexReport) -> None:
    for line in content_versions_index.format_report(report):
        print(line)


async def run_modes(engine: AsyncEngine, args: argparse.Namespace) -> int:
    """Apply then verify, as asked; the exit code reflects ``--verify``."""
    if args.apply:
        _print(await content_versions_index.apply(engine))
    if not args.verify:
        return EXIT_OK
    report = await content_versions_index.verify(engine)
    _print(report)
    if not report.supported or content_versions_index.is_fixed(report):
        return EXIT_OK
    return EXIT_VERIFY_FAILED


async def _main(args: argparse.Namespace) -> int:
    """Uses its own engine and no ``create_all``: only the index changes."""
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
