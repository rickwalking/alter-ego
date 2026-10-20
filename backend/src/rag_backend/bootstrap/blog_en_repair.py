"""Composition root of the one-shot EN repair (AE-0435).

The SQL store reads posts with plain ``SELECT``s and writes through AE-0424's
slot-write path (:func:`apply_slot_edit`: row lock, latest document, version
snapshot, lock-version bump), so the repair is versioned like an editor action.
The translator is the editor's PT -> EN translation service.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from rag_backend.api.dependencies.blog_editor import build_blog_translation_service
from rag_backend.api.dependencies.blog_slot_write import SlotEdit, apply_slot_edit
from rag_backend.application.services.blog.blog_document_edits import (
    with_translation,
)
from rag_backend.application.services.blog.blog_en_repair import (
    BlogEnRepairService,
    EnRepairDeps,
    StoredPost,
)
from rag_backend.application.services.workflow_event_service import WorkflowEventService
from rag_backend.domain.models.blog_document import BlogLanguageDocument
from rag_backend.infrastructure.config.settings import get_settings
from rag_backend.infrastructure.database.models.blog_post import BlogPostModel
from rag_backend.infrastructure.events.factory import get_event_publisher

# Version-history summary and actor of the repair write (no owner session).
VERSION_SUMMARY_EN_REPAIR = "Before EN repair (AE-0435)"
EN_REPAIR_ACTOR = "system:ae-0435-en-repair"

SessionMaker = async_sessionmaker[AsyncSession]


def _stored(row: BlogPostModel) -> StoredPost:
    return StoredPost(post_id=str(row.id), title=row.title, content=row.content)


class SqlEnRepairStore:
    """``EnRepairStore`` over the ``blog_posts`` table."""

    def __init__(self, maker: SessionMaker) -> None:
        self._maker = maker

    async def posts(self) -> list[StoredPost]:
        """Every blog post (read-only)."""
        async with self._maker() as db:
            rows = (await db.execute(select(BlogPostModel))).scalars().all()
            return [_stored(row) for row in rows]

    async def post(self, post_id: str) -> StoredPost | None:
        """One post (read-only), ``None`` when missing."""
        async with self._maker() as db:
            row = await db.get(BlogPostModel, post_id)
            return _stored(row) if row is not None else None

    async def replace_english(
        self, post_id: str, english: BlogLanguageDocument
    ) -> None:
        """Versioned write of ``translations.en`` onto the latest content."""
        async with self._maker() as db:
            row = await db.get(BlogPostModel, post_id)
            actor = str(row.author_id) if row and row.author_id else EN_REPAIR_ACTOR
            await apply_slot_edit(
                db,
                SlotEdit(
                    post_id=post_id,
                    user_id=actor,
                    edit=lambda latest: with_translation(latest, english),
                    events=_events(),
                    change_summary=VERSION_SUMMARY_EN_REPAIR,
                ),
            )


def _events() -> WorkflowEventService:
    return WorkflowEventService(get_event_publisher(get_settings().redis_url or None))


def build_en_repair_service(maker: SessionMaker) -> BlogEnRepairService:
    """The repair over the SQL store and the editor's translation service."""
    return BlogEnRepairService(
        EnRepairDeps(
            store=SqlEnRepairStore(maker),
            translator=build_blog_translation_service(),
        )
    )


__all__ = ["SqlEnRepairStore", "build_en_repair_service"]
