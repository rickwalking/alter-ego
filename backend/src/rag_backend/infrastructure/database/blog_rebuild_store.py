"""SQL adapter of the AE-0426 hidden-post rebuild (``blog_posts``).

Reads every row carrying the AE-0422 ``hidden_bad_post`` marker and performs the
two writes of a rebuild:

* :meth:`SqlBlogRebuildStore.start_attempt` — the same row becomes a ``draft``
  with its publish stamps cleared, its legacy body replaced by a fresh ``blog.v2``
  document (the AE-0424 slot path only edits v2), a fresh generation lease and
  ``lock_version + 1`` (compare-and-set, so a concurrent edit wins).
* :meth:`SqlBlogRebuildStore.mark_rebuilt` — ``hidden_bad_post.rebuilt_at`` is
  stamped in the existing marker (it is kept for audit).

The marker/document shape is read in Python: the table is small and this keeps
the selection dialect-independent (SQLite in tests, Postgres in prod).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import cast

from sqlalchemy import select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from rag_backend.application.services.blog.blog_document_service import (
    BlogDocumentService,
)
from rag_backend.application.services.blog.blog_rebuild import (
    AttemptSpec,
    RebuildCandidate,
    RebuiltStamp,
)
from rag_backend.domain.constants.ai_disclosure import AI_DISCLOSURE_GENERATED
from rag_backend.domain.constants.blog_document import KEY_QUALITY, KEY_SCHEMA
from rag_backend.domain.constants.blog_post import BlogPostStatus
from rag_backend.domain.constants.blog_rebuild import (
    HIDDEN_BAD_POST_KEY,
    REBUILD_STATUS_KEY,
    REBUILT_AT_KEY,
)
from rag_backend.domain.models.blog_generation import GenerationLease
from rag_backend.domain.models.blog_generation_state import started
from rag_backend.infrastructure.database.models.blog_post import BlogPostModel

SessionFactory = async_sessionmaker[AsyncSession]


def _metadata(value: object) -> dict[str, object]:
    return dict(value) if isinstance(value, Mapping) else {}


def _content(value: object) -> dict[str, object]:
    return dict(value) if isinstance(value, Mapping) else {}


def _marker(metadata: Mapping[str, object]) -> dict[str, object] | None:
    marker = metadata.get(HIDDEN_BAD_POST_KEY)
    return dict(marker) if isinstance(marker, Mapping) else None


def _rebuilt_at(marker: Mapping[str, object] | None) -> str | None:
    if marker is None:
        return None
    value = marker.get(REBUILT_AT_KEY)
    return value if isinstance(value, str) and value else None


def _voice_score(content: Mapping[str, object]) -> float | None:
    quality = content.get(KEY_QUALITY)
    if not isinstance(quality, Mapping):
        return None
    score = quality.get("voice_score")
    if isinstance(score, bool) or not isinstance(score, (int, float)):
        return None
    return float(score)


def _schema(content: Mapping[str, object]) -> str | None:
    value = content.get(KEY_SCHEMA)
    return value if isinstance(value, str) else None


def _candidate(row: BlogPostModel) -> RebuildCandidate:
    metadata = _metadata(row.ai_generation_metadata)
    marker = _marker(metadata)
    content = _content(row.content)
    return RebuildCandidate(
        post_id=str(row.id),
        project_id=str(row.project_id) if row.project_id else None,
        author_id=str(row.author_id) if row.author_id else None,
        lock_version=int(row.lock_version or 0),
        status=str(row.status),
        has_hidden_marker=marker is not None,
        rebuilt_at=_rebuilt_at(marker),
        content_schema=_schema(content),
        voice_score=_voice_score(content),
    )


class SqlBlogRebuildStore:
    """``RebuildStore`` over ``blog_posts`` (one instance per run)."""

    def __init__(self, sessions: SessionFactory) -> None:
        self._sessions = sessions

    async def candidates(self) -> list[RebuildCandidate]:
        """Every row, reduced to the facts of the selection predicate."""
        async with self._sessions() as session:
            rows = (await session.execute(select(BlogPostModel))).scalars().all()
        return [_candidate(row) for row in rows]

    async def start_attempt(self, spec: AttemptSpec) -> GenerationLease | None:
        """Draft + fresh lease on the SAME row; ``None`` when it moved meanwhile."""
        next_version = spec.seen_lock_version + 1
        async with self._sessions.begin() as session:
            metadata = await self._metadata_of(session, spec.post_id)
            conditions = [
                BlogPostModel.id == spec.post_id,
                BlogPostModel.lock_version == spec.seen_lock_version,
            ]
            if not spec.allow_published:
                conditions.append(
                    BlogPostModel.status != BlogPostStatus.PUBLISHED.value
                )
            result = await session.execute(
                update(BlogPostModel)
                .where(*conditions)
                .values(
                    status=BlogPostStatus.DRAFT.value,
                    content=BlogDocumentService.initial_content(),
                    featured_image_url=None,
                    published_at=None,
                    submitted_for_review_at=None,
                    approved_at=None,
                    scheduled_publish_at=None,
                    ai_disclosure_label=AI_DISCLOSURE_GENERATED,
                    ai_generation_metadata=started(metadata, spec.start),
                    lock_version=next_version,
                )
                .execution_options(synchronize_session=False)
            )
            written = cast(CursorResult[object], result).rowcount == 1
        if not written:
            return None
        return GenerationLease(
            post_id=spec.post_id,
            lease_id=spec.start.lease_id,
            lock_version=next_version,
        )

    async def mark_rebuilt(self, stamp: RebuiltStamp) -> None:
        """Stamp ``hidden_bad_post.rebuilt_at`` (the marker is kept for audit)."""
        async with self._sessions.begin() as session:
            metadata = await self._metadata_of(session, stamp.post_id)
            marker = _marker(metadata) or {}
            await session.execute(
                update(BlogPostModel)
                .where(BlogPostModel.id == stamp.post_id)
                .values(
                    ai_generation_metadata={
                        **metadata,
                        HIDDEN_BAD_POST_KEY: {
                            **marker,
                            REBUILT_AT_KEY: stamp.at,
                            REBUILD_STATUS_KEY: stamp.status,
                        },
                    }
                )
                .execution_options(synchronize_session=False)
            )

    @staticmethod
    async def _metadata_of(session: AsyncSession, post_id: str) -> dict[str, object]:
        result = await session.execute(
            select(BlogPostModel.ai_generation_metadata).where(
                BlogPostModel.id == post_id
            )
        )
        return _metadata(result.scalar_one_or_none())


__all__ = ["SqlBlogRebuildStore"]
