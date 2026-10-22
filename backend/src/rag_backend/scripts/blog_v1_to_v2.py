"""One-shot blog_posts.content v1 -> blog.v2 cutover command (ADR-0025).

Usage (in the freshly built backend image, Postgres up, app stack down):
    python -m rag_backend.scripts.blog_v1_to_v2 --dry-run
    python -m rag_backend.scripts.blog_v1_to_v2 --apply --verify
    python -m rag_backend.scripts.blog_v1_to_v2 --verify
    python -m rag_backend.scripts.blog_v1_to_v2 --rollback   # before a code revert

Exit codes: 0 ok, 1 ``--verify`` found a non-v2 row (the deploy aborts before
traffic), 2 usage error. Safe to re-run: ``--apply`` skips v2 rows.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from rag_backend.infrastructure.config.settings import get_settings
from rag_backend.infrastructure.database import blog_v2_cutover
from rag_backend.infrastructure.database.blog_v2_cutover import (
    CutoverReport,
    SessionMaker,
)
from rag_backend.scripts.cli_support import EXIT_USAGE as EXIT_USAGE
from rag_backend.scripts.cli_support import GuardedCli, run_guarded_cli

EXIT_OK = 0
EXIT_VERIFY_FAILED = 1


def build_parser() -> argparse.ArgumentParser:
    """CLI flags; ``--apply`` and ``--verify`` combine, the rest are exclusive."""
    parser = argparse.ArgumentParser(prog="blog_v1_to_v2", description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="report only")
    parser.add_argument("--apply", action="store_true", help="rewrite v1 rows")
    parser.add_argument("--verify", action="store_true", help="gate on zero non-v2")
    parser.add_argument("--rollback", action="store_true", help="re-join sections")
    return parser


def validate_modes(args: argparse.Namespace) -> str | None:
    """Return a usage error, or ``None`` when the flag combination is valid."""
    chosen = [args.dry_run, args.apply, args.verify, args.rollback]
    if not any(chosen):
        return "choose --dry-run, --apply, --verify or --rollback"
    exclusive = [args.dry_run, args.apply or args.verify, args.rollback]
    if sum(bool(flag) for flag in exclusive) > 1:
        return "--dry-run and --rollback cannot be combined with other modes"
    return None


def _print(report: CutoverReport) -> None:
    for line in blog_v2_cutover.format_report(report):
        print(line)


async def run_modes(maker: SessionMaker, args: argparse.Namespace) -> int:
    """Run the selected modes in order; the exit code reflects ``--verify``."""
    if args.dry_run:
        _print(await blog_v2_cutover.dry_run(maker))
    if args.rollback:
        _print(await blog_v2_cutover.rollback(maker))
    if args.apply:
        _print(await blog_v2_cutover.apply(maker))
    if not args.verify:
        return EXIT_OK
    report = await blog_v2_cutover.verify(maker)
    _print(report)
    return EXIT_VERIFY_FAILED if report.non_v2_ids else EXIT_OK


async def _main(args: argparse.Namespace) -> int:
    """Uses its own engine without ``create_all``: the cutover never creates or alters
    tables.
    """
    engine = create_async_engine(get_settings().database_url, pool_pre_ping=True)
    try:
        maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        return await run_modes(maker, args)
    finally:
        await engine.dispose()


def main(argv: Sequence[str] | None = None) -> int:
    """Parse flags, run the cutover, return the process exit code."""
    cli = GuardedCli(build_parser(), validate_modes, _main)
    return run_guarded_cli(cli, argv)


if __name__ == "__main__":
    sys.exit(main())
