"""Rebuild the hidden carousel-origin posts as v2 drafts.

One-off operator action: every ``blog_posts`` row carrying the hide
marker (``ai_generation_metadata.hidden_bad_post`` present, ``rebuilt_at``
absent) is rebuilt through the writer pipeline and left a ``draft`` for
owner review. Selection is by that durable marker, never by ``status`` (hiding
already flipped the rows to ``draft``). Idempotent and resumable: a successful
rebuild stamps ``hidden_bad_post.rebuilt_at`` and is skipped on the next run.

    python -m rag_backend.scripts.rebuild_hidden_posts --dry-run
    python -m rag_backend.scripts.rebuild_hidden_posts --apply --only <post-id>

Run this **inside the prod backend container**: generated images are written to
the configured ``carousel_output_dir/blog-images`` volume.

The default is ``--dry-run``; pass ``--apply`` to write. Never publishes.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from collections.abc import Sequence
from contextlib import AsyncExitStack
from typing import TYPE_CHECKING

import structlog

from rag_backend.domain.constants.blog_rebuild import LOG_REBUILD_ABORTED

if TYPE_CHECKING:
    from rag_backend.application.services.blog.blog_rebuild import (
        RebuildReport,
        RebuildSelection,
    )

logger = structlog.get_logger(__name__)

EXIT_OK = 0
EXIT_FAILED = 1
DEFAULT_MAX_POSTS = 1
ERR_CAP_POSITIVE = "must be at least 1"


def _positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(ERR_CAP_POSITIVE) from None
    if parsed < 1:
        raise argparse.ArgumentTypeError(ERR_CAP_POSITIVE)
    return parsed


def build_parser() -> argparse.ArgumentParser:
    """CLI flags; the default is ``--dry-run`` (a preview of the targets)."""
    parser = argparse.ArgumentParser(prog="rebuild_hidden_posts", description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--apply",
        action="store_true",
        help="write changes (default is dry-run)",
    )
    mode.add_argument(
        "--dry-run",
        action="store_true",
        help="preview only (the default)",
    )
    parser.add_argument(
        "--only",
        action="append",
        default=[],
        metavar="POST_ID",
        help="rebuild only this post id (repeatable)",
    )
    parser.add_argument(
        "--limit",
        type=_positive_int,
        default=None,
        metavar="N",
        help="consider only the first N selected posts",
    )
    parser.add_argument(
        "--max-posts",
        type=_positive_int,
        default=DEFAULT_MAX_POSTS,
        metavar="N",
        help="hard cap on posts attempted by --apply (default: 1)",
    )
    parser.add_argument(
        "--include-published",
        action="store_true",
        help="also rebuild published rows (they are flipped back to draft)",
    )
    return parser


def selection_from_args(args: argparse.Namespace) -> RebuildSelection:
    """Translate the parsed CLI flags into the application selection guard."""
    from rag_backend.application.services.blog.blog_rebuild import RebuildSelection

    return RebuildSelection(
        only=frozenset(args.only),
        limit=args.limit,
        max_posts=args.max_posts,
        allow_published=args.include_published,
    )


def format_report(report: RebuildReport) -> list[str]:
    """Human-readable lines of a run summary (AC6)."""
    counts = report.counts
    summary = (
        "summary: "
        f"selected={counts['selected']} rebuilt={counts['rebuilt']} "
        f"skipped={counts['skipped']} failed={counts['failed']}"
    )
    if report.omitted:
        summary += f" omitted={report.omitted}"
    lines = [summary]
    lines.extend(
        f"  rebuilt {entry.post_id} ({entry.detail})" for entry in report.rebuilt
    )
    lines.extend(
        f"  skipped {entry.post_id} ({entry.criterion})" for entry in report.skipped
    )
    lines.extend(
        f"  failed  {entry.post_id} ({entry.detail})" for entry in report.failed
    )
    return lines


def exit_code(report: RebuildReport) -> int:
    """Non-zero when at least one post failed (the operator/CI sees it)."""
    return EXIT_FAILED if report.failed else EXIT_OK


def _init_langfuse() -> None:
    from rag_backend.infrastructure.config.settings import get_settings
    from rag_backend.infrastructure.langfuse_client import init_langfuse

    settings = get_settings()
    init_langfuse(
        settings.langfuse_public_key,
        settings.langfuse_secret_key.get_secret_value()
        if settings.langfuse_secret_key
        else "",
        settings.langfuse_host,
    )


def _flush_langfuse() -> None:
    from rag_backend.infrastructure.langfuse_client import get_langfuse_client

    try:
        client = get_langfuse_client()
        if client is not None:
            client.flush()
    except Exception:
        logger.exception(LOG_REBUILD_ABORTED)


async def _run(*, apply: bool, selection: RebuildSelection) -> int:
    from rag_backend.agents.harness import build_checkpointer
    from rag_backend.application.services.blog.blog_rebuild import RebuildReport
    from rag_backend.bootstrap.blog_rebuild import build_rebuild_service
    from rag_backend.infrastructure.config.settings import get_settings
    from rag_backend.infrastructure.database.config import close_db, init_db

    report = RebuildReport()
    aborted = False
    try:
        settings = get_settings()
        await init_db(settings.database_url)
        _init_langfuse()
        async with AsyncExitStack() as stack:
            checkpointer = await build_checkpointer(settings, stack)
            service = build_rebuild_service(checkpointer)
            report = await (
                service.run(selection) if apply else service.preview(selection)
            )
    except Exception:
        logger.exception(LOG_REBUILD_ABORTED)
        aborted = True
    finally:
        _flush_langfuse()
        try:
            await close_db()
        except Exception:
            logger.exception(LOG_REBUILD_ABORTED)
            aborted = True
        for line in format_report(report):
            print(line)
    return EXIT_FAILED if aborted else exit_code(report)


def main(argv: Sequence[str] | None = None) -> int:
    """Parse flags, run the rebuild, return the process exit code."""
    args = build_parser().parse_args(argv)
    from rag_backend.infrastructure.config.settings import get_settings
    from rag_backend.infrastructure.logging import setup_logging

    setup_logging(debug=get_settings().debug)
    return asyncio.run(_run(apply=args.apply, selection=selection_from_args(args)))


__all__ = [
    "DEFAULT_MAX_POSTS",
    "EXIT_FAILED",
    "EXIT_OK",
    "build_parser",
    "exit_code",
    "format_report",
    "main",
    "selection_from_args",
]

if __name__ == "__main__":
    sys.exit(main())
