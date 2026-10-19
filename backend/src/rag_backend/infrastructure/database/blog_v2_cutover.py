"""One-shot ``blog_posts.content`` v1 -> ``blog.v2`` cutover (AE-0423, ADR-0025).

Data-only (no DDL, no Alembic state): every row is rewritten in place with the
pure, fence-aware conversion in ``domain.models.blog_document_split``. Driven
by ``python -m rag_backend.scripts.blog_v1_to_v2`` as an explicit deploy step
(after Postgres is healthy, before the app stack starts).

- ``dry_run`` — per-row PT/translation section counts + oversized flags; no writes.
- ``apply`` — batched, one transaction per batch under ``pg_advisory_xact_lock``;
  a v2 row is skipped, so a second run changes nothing. ``featured_image_url``
  is cleared with the cover (the column is the cover's projection).
- ``verify`` — standalone-safe gate: lists every row (or translation) not at v2.
- ``rollback`` — re-joins sections to ``{"markdown", "translations"}``; run it
  from the new image BEFORE reverting the app code.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

import structlog
from sqlalchemy import inspect, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from rag_backend.domain.constants.blog_document import (
    BLOG_SECTION_MAX_CHARS,
    KEY_BODY_MD,
    KEY_SECTIONS,
    KEY_TRANSLATIONS,
)
from rag_backend.domain.models.blog_document_split import (
    is_v2_content,
    is_v2_language_document,
    migrate_content,
    rollback_content,
)
from rag_backend.infrastructure.database.models.blog_post import BlogPostModel

logger = structlog.get_logger(__name__)

CUTOVER_BATCH_SIZE = 100
# Stable key so two concurrent runs serialize on the same Postgres advisory lock.
CUTOVER_ADVISORY_LOCK_KEY = 4_230_423
POSTGRES_DIALECT = "postgresql"
PT_LANGUAGE = "pt"
MODE_DRY_RUN = "dry-run"
MODE_APPLY = "apply"
MODE_VERIFY = "verify"
MODE_ROLLBACK = "rollback"
_LOCK_SQL = text("SELECT pg_advisory_xact_lock(:key)")

SessionMaker = async_sessionmaker[AsyncSession]
Rewrite = Callable[[object], dict[str, object] | None]
_Row = tuple[str, object, str | None]


@dataclass
class CutoverRow:
    """What the cutover does (or would do) to one row."""

    post_id: str
    section_counts: dict[str, int] = field(default_factory=dict)
    oversized: list[str] = field(default_factory=list)
    cleared_featured_image_url: str | None = None


@dataclass
class CutoverReport:
    """Outcome of one mode run; ``non_v2_ids`` drives the ``--verify`` exit."""

    mode: str
    scanned: int = 0
    changed: int = 0
    rows: list[CutoverRow] = field(default_factory=list)
    non_v2_ids: list[str] = field(default_factory=list)


def _section_lengths(document: object) -> list[int]:
    if not isinstance(document, dict):
        return []
    sections = document.get(KEY_SECTIONS)
    if not isinstance(sections, list):
        return []
    return [
        len(str(section.get(KEY_BODY_MD, "")))
        for section in sections
        if isinstance(section, dict)
    ]


def _languages(content: dict[str, object]) -> dict[str, object]:
    languages: dict[str, object] = {PT_LANGUAGE: content}
    translations = content.get(KEY_TRANSLATIONS)
    if isinstance(translations, dict):
        languages.update({str(lang): doc for lang, doc in translations.items()})
    return languages


def describe_row(
    post_id: str, migrated: dict[str, object], featured: str | None
) -> CutoverRow:
    """Section counts per language + oversized sections (flagged, not cut)."""
    row = CutoverRow(post_id=post_id, cleared_featured_image_url=featured)
    for language, document in _languages(migrated).items():
        lengths = _section_lengths(document)
        row.section_counts[language] = len(lengths)
        row.oversized.extend(
            f"{language}#{index}"
            for index, length in enumerate(lengths)
            if length > BLOG_SECTION_MAX_CHARS
        )
    return row


def _rollback_rewrite(content: object) -> dict[str, object] | None:
    if not is_v2_language_document(content):
        return None
    return rollback_content(content)


async def _table_exists(session: AsyncSession) -> bool:
    return await session.run_sync(
        lambda sync: inspect(sync.connection()).has_table(BlogPostModel.__tablename__)
    )


async def _all_ids(maker: SessionMaker) -> list[str]:
    async with maker() as session:
        if not await _table_exists(session):
            return []
        result = await session.execute(
            select(BlogPostModel.id).order_by(BlogPostModel.id)
        )
        return [str(post_id) for post_id in result.scalars().all()]


async def _lock(session: AsyncSession) -> None:
    if session.get_bind().dialect.name != POSTGRES_DIALECT:
        return
    await session.execute(_LOCK_SQL, {"key": CUTOVER_ADVISORY_LOCK_KEY})


async def _load_batch(session: AsyncSession, ids: list[str]) -> list[_Row]:
    result = await session.execute(
        select(
            BlogPostModel.id, BlogPostModel.content, BlogPostModel.featured_image_url
        ).where(BlogPostModel.id.in_(ids))
    )
    return [(str(row[0]), row[1], row[2]) for row in result.all()]


async def _write_row(
    session: AsyncSession, post_id: str, values: dict[str, object]
) -> None:
    await session.execute(
        update(BlogPostModel)
        .where(BlogPostModel.id == post_id)
        # A data cutover is not an edit: keep ``updated_at`` as it was.
        .values(**values, updated_at=BlogPostModel.updated_at)
    )


@dataclass(frozen=True)
class _BatchJob:
    rewrite: Rewrite
    clear_featured: bool


async def _run_batch(
    session: AsyncSession, ids: list[str], job: _BatchJob
) -> list[CutoverRow]:
    changed: list[CutoverRow] = []
    for post_id, content, featured in await _load_batch(session, ids):
        rewritten = job.rewrite(content)
        if rewritten is None:
            continue
        values: dict[str, object] = {"content": rewritten}
        if job.clear_featured:
            values["featured_image_url"] = None
        await _write_row(session, post_id, values)
        cleared = featured if job.clear_featured else None
        changed.append(describe_row(post_id, rewritten, cleared))
    return changed


async def _run_batched(
    maker: SessionMaker, job: _BatchJob, report: CutoverReport
) -> CutoverReport:
    ids = await _all_ids(maker)
    report.scanned = len(ids)
    for start in range(0, len(ids), CUTOVER_BATCH_SIZE):
        batch = ids[start : start + CUTOVER_BATCH_SIZE]
        async with maker() as session, session.begin():
            await _lock(session)
            report.rows.extend(await _run_batch(session, batch, job))
    report.changed = len(report.rows)
    logger.info(
        "blog_v2_cutover_done",
        mode=report.mode,
        scanned=report.scanned,
        changed=report.changed,
    )
    return report


async def apply(maker: SessionMaker) -> CutoverReport:
    """Rewrite every non-v2 row in place (idempotent)."""
    job = _BatchJob(rewrite=migrate_content, clear_featured=True)
    return await _run_batched(maker, job, CutoverReport(mode=MODE_APPLY))


async def rollback(maker: SessionMaker) -> CutoverReport:
    """Re-join every v2 row to the v1 ``{markdown, translations}`` shape."""
    job = _BatchJob(rewrite=_rollback_rewrite, clear_featured=False)
    return await _run_batched(maker, job, CutoverReport(mode=MODE_ROLLBACK))


async def _scan(maker: SessionMaker) -> list[_Row]:
    async with maker() as session:
        if not await _table_exists(session):
            return []
        result = await session.execute(
            select(
                BlogPostModel.id,
                BlogPostModel.content,
                BlogPostModel.featured_image_url,
            ).order_by(BlogPostModel.id)
        )
        return [(str(row[0]), row[1], row[2]) for row in result.all()]


async def dry_run(maker: SessionMaker) -> CutoverReport:
    """Report what ``apply`` would change; writes nothing."""
    report = CutoverReport(mode=MODE_DRY_RUN)
    rows = await _scan(maker)
    report.scanned = len(rows)
    for post_id, content, featured in rows:
        migrated = migrate_content(content)
        if migrated is not None:
            report.rows.append(describe_row(post_id, migrated, featured))
    report.changed = len(report.rows)
    return report


async def verify(maker: SessionMaker) -> CutoverReport:
    """List every row whose content (or any translation) is not ``blog.v2``."""
    report = CutoverReport(mode=MODE_VERIFY)
    rows = await _scan(maker)
    report.scanned = len(rows)
    report.non_v2_ids = [
        post_id for post_id, content, _ in rows if not is_v2_content(content)
    ]
    if report.non_v2_ids:
        logger.error("blog_v2_cutover_verify_failed", non_v2=len(report.non_v2_ids))
    return report


def format_report(report: CutoverReport) -> list[str]:
    """Human-readable lines for the operator / deploy log."""
    lines = [
        f"[{report.mode}] scanned={report.scanned} changed={report.changed} "
        f"non_v2={len(report.non_v2_ids)}"
    ]
    for row in report.rows:
        counts = ",".join(f"{lang}:{n}" for lang, n in row.section_counts.items())
        oversized = ",".join(row.oversized) or "-"
        cleared = row.cleared_featured_image_url or "-"
        lines.append(
            f"  {row.post_id} sections[{counts}] oversized[{oversized}] "
            f"cleared_featured_image_url={cleared}"
        )
    lines.extend(f"  NOT_V2 {post_id}" for post_id in report.non_v2_ids)
    return lines


__all__ = [
    "CUTOVER_BATCH_SIZE",
    "CutoverReport",
    "CutoverRow",
    "SessionMaker",
    "apply",
    "describe_row",
    "dry_run",
    "format_report",
    "rollback",
    "verify",
]
