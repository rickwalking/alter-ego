"""Find / repair blog posts whose ``translations.en`` reads as Portuguese.

One-off operator action. The default (no flag or ``--dry-run``) is a
read-only scan that lists every ``blog.v2`` post whose EN sections read as
Portuguese. ``--apply --only <post-id>`` (repeatable, required with
``--apply``) translates that post's PT document to English and replaces only
``translations.en`` (versioned write; PT, images and cover unchanged). A post
whose EN already reads as English is skipped.

    python -m rag_backend.scripts.regenerate_blog_en
    python -m rag_backend.scripts.regenerate_blog_en --apply --only <post-id>

Run it inside the prod backend container (the translation uses its LLM
settings). Never publishes.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from collections.abc import Sequence
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from rag_backend.infrastructure.config.settings import get_settings

if TYPE_CHECKING:
    from rag_backend.application.services.blog.blog_en_repair import (
        BlogEnRepairService,
        EnRepairReport,
    )

EXIT_OK = 0
EXIT_FAILED = 1
EXIT_USAGE = 2
ERR_APPLY_NEEDS_ONLY = "--apply needs at least one --only <post-id>"


def build_parser() -> argparse.ArgumentParser:
    """CLI flags; the default is the read-only scan."""
    parser = argparse.ArgumentParser(prog="regenerate_blog_en", description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--apply", action="store_true", help="repair the --only posts")
    mode.add_argument("--dry-run", action="store_true", help="scan only (default)")
    parser.add_argument(
        "--only",
        action="append",
        default=[],
        metavar="POST_ID",
        help="post id to repair (repeatable; required with --apply)",
    )
    return parser


def format_report(report: EnRepairReport) -> list[str]:
    """Human-readable lines of a scan or repair."""
    lines = [
        f"summary: wrong_en={len(report.wrong)} repaired={len(report.repaired)} "
        f"skipped={len(report.skipped)} failed={len(report.failed)}"
    ]
    lines.extend(
        f"  wrong-en {item.post_id} sections={','.join(item.sections)} {item.title}"
        for item in report.wrong
    )
    lines.extend(f"  repaired {post_id}" for post_id in report.repaired)
    lines.extend(f"  skipped  {post_id} ({why})" for post_id, why in report.skipped)
    lines.extend(f"  failed   {post_id} ({why})" for post_id, why in report.failed)
    return lines


async def run_mode(
    service: BlogEnRepairService, args: argparse.Namespace
) -> EnRepairReport:
    """Scan, or repair the ``--only`` posts with ``--apply``."""
    if args.apply:
        return await service.repair(tuple(args.only))
    return await service.scan()


async def _main(args: argparse.Namespace) -> int:
    """Uses its own engine without ``create_all``: the repair never creates or alters
    tables.
    """
    from rag_backend.bootstrap.blog_en_repair import build_en_repair_service

    engine = create_async_engine(
        get_settings().database_url, pool_pre_ping=True, hide_parameters=True
    )
    try:
        maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        report = await run_mode(build_en_repair_service(maker), args)
    finally:
        await engine.dispose()
    for line in format_report(report):
        print(line)
    return EXIT_FAILED if report.failed else EXIT_OK


def main(argv: Sequence[str] | None = None) -> int:
    """Parse flags, scan or repair, return the process exit code."""
    args = build_parser().parse_args(argv)
    if args.apply and not args.only:
        print(f"ERROR: {ERR_APPLY_NEEDS_ONLY}", file=sys.stderr)
        return EXIT_USAGE
    return asyncio.run(_main(args))


if __name__ == "__main__":
    sys.exit(main())
