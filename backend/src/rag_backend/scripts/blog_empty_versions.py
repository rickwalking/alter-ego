"""One-shot repair of version histories holding empty snapshots (AE-0438, F-05).

Before AE-0438 the generation's first write snapshotted the empty bootstrap
document, so ``version_history`` of a generated post starts with an entry whose
``snapshot`` has no content; restoring it 422s. New writes never append empty
snapshots (``blog_version_history.append_version``); this command repairs the
history already stored.

Usage (in the built backend image, Postgres up):
    python -m rag_backend.scripts.blog_empty_versions --count
    python -m rag_backend.scripts.blog_empty_versions --apply
    python -m rag_backend.scripts.blog_empty_versions --verify

Exit codes: 0 ok, 1 ``--verify`` found an empty snapshot, 2 usage error.
``--apply`` is idempotent (a second run changes nothing); it drops the empty
entries, renumbers the rest 1..N and writes once per changed row.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from collections.abc import Sequence
from dataclasses import dataclass, field

import structlog
from sqlalchemy import inspect, select, text, update
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from rag_backend.application.services.blog.blog_version_history import (
    drop_empty_entries,
    is_empty_document,
)
from rag_backend.infrastructure.config.settings import get_settings
from rag_backend.infrastructure.database.models.blog_post import BlogPostModel

logger = structlog.get_logger(__name__)

EXIT_OK = 0
EXIT_VERIFY_FAILED = 1
EXIT_USAGE = 2

BATCH_SIZE = 100
ADVISORY_LOCK_KEY = 4_380_438
POSTGRES_DIALECT = "postgresql"
_LOCK_SQL = text("SELECT pg_advisory_xact_lock(:key)")
KEY_SNAPSHOT = "snapshot"

SessionMaker = async_sessionmaker[AsyncSession]


@dataclass
class PostReport:
    """What one post's history looks like (count mode) or was changed to."""

    post_id: str
    entries: int = 0
    empty: int = 0


@dataclass
class Report:
    """Outcome of one mode run."""

    mode: str
    scanned: int = 0
    changed: int = 0
    rows: list[PostReport] = field(default_factory=list)


def _empty_count(history: object) -> int:
    if not isinstance(history, list):
        return 0
    return sum(
        1
        for entry in history
        if isinstance(entry, dict) and is_empty_document(entry.get(KEY_SNAPSHOT))
    )


def build_parser() -> argparse.ArgumentParser:
    """CLI flags; at least one mode is required."""
    parser = argparse.ArgumentParser(prog="blog_empty_versions", description=__doc__)
    parser.add_argument("--count", action="store_true", help="report only")
    parser.add_argument("--apply", action="store_true", help="drop empty entries")
    parser.add_argument("--verify", action="store_true", help="gate on zero empties")
    return parser


def validate_modes(args: argparse.Namespace) -> str | None:
    """Return a usage error, or ``None`` when at least one mode is chosen."""
    if not any((args.count, args.apply, args.verify)):
        return "choose --count, --apply and/or --verify"
    return None


async def _table_exists(session: AsyncSession) -> bool:
    return await session.run_sync(
        lambda sync: inspect(sync.connection()).has_table(BlogPostModel.__tablename__)
    )


async def _lock(session: AsyncSession) -> None:
    if session.get_bind().dialect.name != POSTGRES_DIALECT:
        return
    await session.execute(_LOCK_SQL, {"key": ADVISORY_LOCK_KEY})


async def _history_rows(maker: SessionMaker) -> list[tuple[str, object]]:
    async with maker() as session:
        if not await _table_exists(session):
            return []
        result = await session.execute(
            select(BlogPostModel.id, BlogPostModel.version_history).order_by(
                BlogPostModel.id
            )
        )
        return [(str(post_id), history) for post_id, history in result.all()]


async def count(maker: SessionMaker) -> Report:
    """Read-only: every post whose history holds an empty snapshot."""
    report = Report(mode="count")
    rows = await _history_rows(maker)
    report.scanned = len(rows)
    for post_id, history in rows:
        empty = _empty_count(history)
        if empty:
            entries = len(history) if isinstance(history, list) else 0
            report.rows.append(
                PostReport(post_id=post_id, entries=entries, empty=empty)
            )
    report.changed = len(report.rows)
    return report


async def apply(maker: SessionMaker) -> Report:
    """Drop the empty entries and renumber; one write per changed row."""
    report = Report(mode="apply")
    rows = await _history_rows(maker)
    report.scanned = len(rows)
    changed_ids = [
        post_id for post_id, history in rows if drop_empty_entries(history) is not None
    ]
    for start in range(0, len(changed_ids), BATCH_SIZE):
        batch = changed_ids[start : start + BATCH_SIZE]
        async with maker() as session, session.begin():
            await _lock(session)
            for post_id in batch:
                found = await session.execute(
                    select(BlogPostModel.version_history).where(
                        BlogPostModel.id == post_id
                    )
                )
                history = found.scalar_one_or_none()
                cleaned = drop_empty_entries(history)
                if cleaned is None:
                    continue
                await session.execute(
                    update(BlogPostModel)
                    .where(BlogPostModel.id == post_id)
                    .values(
                        version_history=cleaned,
                        updated_at=BlogPostModel.updated_at,
                    )
                )
                report.rows.append(
                    PostReport(
                        post_id=post_id,
                        entries=len(cleaned),
                        empty=_empty_count(history),
                    )
                )
    report.changed = len(report.rows)
    logger.info(
        "blog_empty_versions_apply",
        scanned=report.scanned,
        changed=report.changed,
    )
    return report


async def verify(maker: SessionMaker) -> Report:
    """List every post whose history still holds an empty snapshot."""
    report = Report(mode="verify")
    rows = await _history_rows(maker)
    report.scanned = len(rows)
    report.rows = [
        PostReport(
            post_id=post_id,
            entries=len(history) if isinstance(history, list) else 0,
            empty=_empty_count(history),
        )
        for post_id, history in rows
        if _empty_count(history)
    ]
    return report


def format_report(report: Report) -> list[str]:
    """Human-readable lines for the operator."""
    lines = [f"[{report.mode}] scanned={report.scanned} changed={report.changed}"]
    lines.extend(
        f"  {row.post_id} entries={row.entries} empty={row.empty}"
        for row in report.rows
    )
    return lines


async def run_modes(maker: SessionMaker, args: argparse.Namespace) -> int:
    """Run the chosen modes; ``--verify`` drives the exit code."""
    for line in format_report(await count(maker)):
        print(line)
    if args.apply:
        for line in format_report(await apply(maker)):
            print(line)
    if not args.verify:
        return EXIT_OK
    report = await verify(maker)
    for line in format_report(report):
        print(line)
    return EXIT_VERIFY_FAILED if report.rows else EXIT_OK


async def _main(args: argparse.Namespace) -> int:
    engine = create_async_engine(get_settings().database_url, pool_pre_ping=True)
    try:
        maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        return await run_modes(maker, args)
    finally:
        await engine.dispose()


def main(argv: Sequence[str] | None = None) -> int:
    """Parse flags, run the repair, return the process exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)
    error = validate_modes(args)
    if error is not None:
        print(f"ERROR: {error}", file=sys.stderr)
        return EXIT_USAGE
    return asyncio.run(_main(args))


if __name__ == "__main__":
    sys.exit(main())
