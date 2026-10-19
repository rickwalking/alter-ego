"""The production store of a blog generation run (AE-0425 on AE-0424's slot path).

Run state (heartbeat, final status, content reads) is lease-fenced in
:class:`SqlBlogGenerationStore`. Every CONTENT write of the run (the article,
then the images) goes through AE-0424's shared slot-write helper
(:func:`apply_slot_edit`): the row is re-read ``SELECT ... FOR UPDATE`` after
the provider spend, the edit is applied onto the LATEST document by section id,
stored with a version snapshot at the locked ``lock_version`` (an owner save
during the run is the base of the write, never a 409), and the new image files
are discarded when the write fails. The lease is checked on the locked row, in
the same transaction, and the generated images are counted against AE-0424's
per-post cap is RESERVED under the row lock before the provider spend
(``reserve_image_budget``, AE-0424 review round 2).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from rag_backend.api.dependencies.blog_content_write import (
    ContentWrite,
    write_post_content,
)
from rag_backend.api.dependencies.blog_document import validated_write
from rag_backend.api.dependencies.blog_image_budget import (
    BudgetReservation,
    reserve_image_budget,
)
from rag_backend.api.dependencies.blog_slot_write import (
    LockedBlogPostRow,
    SlotEdit,
    apply_slot_edit,
)
from rag_backend.api.dependencies.resource_access import lock_blog_post
from rag_backend.application.services.workflow_event_service import WorkflowEventService
from rag_backend.domain.constants.ai_disclosure import AI_ACTION_GENERATE_IMAGE
from rag_backend.domain.constants.blog_generation import VERSION_SUMMARY_GENERATION
from rag_backend.domain.models.blog_document import (
    InvalidBlogDocumentError,
    parse_blog_content,
)
from rag_backend.domain.models.blog_generation import (
    DocumentApply,
    GenerationLease,
    GenerationOutcome,
    LeaseLostError,
)
from rag_backend.domain.models.blog_generation_state import (
    heartbeat,
    lease_of,
    with_voice_score,
)
from rag_backend.infrastructure.config.settings import get_settings
from rag_backend.infrastructure.database.blog_generation_drafts import (
    bootstrap_content,
)
from rag_backend.infrastructure.database.blog_generation_store import (
    SqlBlogGenerationStore,
)
from rag_backend.infrastructure.events.factory import get_event_publisher

SessionFactory = async_sessionmaker[AsyncSession]


def _event_service() -> WorkflowEventService:
    """The blog workflow event service (same wiring as the editor routes)."""
    settings = get_settings()
    return WorkflowEventService(get_event_publisher(settings.redis_url or None))


@dataclass(frozen=True)
class _MetadataChange:
    lease: GenerationLease
    change: DocumentApply
    now: str

    def __call__(self, metadata: dict[str, object]) -> dict[str, object]:
        if lease_of(metadata) != self.lease.lease_id:
            raise LeaseLostError(self.lease.post_id)
        return with_voice_score(heartbeat(metadata, self.now), self.change.voice_score)


@dataclass(frozen=True)
class RunOwner:
    """Who the run writes as, and the post's image cap (BLOG_IMAGE_COST_CAP)."""

    user_id: str
    image_cap: int


class SlotWriteGenerationStore:
    """``BlogGenerationStore``: run state lease-fenced, content via the slot path."""

    def __init__(self, sessions: SessionFactory, owner: RunOwner) -> None:
        self._sessions = sessions
        self._user_id = owner.user_id
        self._cap = owner.image_cap
        self._state = SqlBlogGenerationStore(sessions)

    async def heartbeat(self, lease: GenerationLease) -> None:
        """Stamp ``generation.heartbeat_at``."""
        await self._state.heartbeat(lease)

    async def read_content(self, lease: GenerationLease) -> dict[str, object]:
        """The row's current content."""
        return await self._state.read_content(lease)

    async def reserve_images(self, lease: GenerationLease, wanted: int) -> int:
        """Reserve the images one by one through AE-0424's reservation (row
        lock + commit before the spend); stop at the cap (429)."""
        granted = 0
        for _image in range(wanted):
            try:
                async with self._sessions() as db:
                    await reserve_image_budget(
                        db, BudgetReservation(post_id=lease.post_id, cap=self._cap)
                    )
            except HTTPException:
                break
            granted += 1
        return granted

    async def finish(self, lease: GenerationLease, outcome: GenerationOutcome) -> None:
        """Record the final status."""
        await self._state.finish(lease, outcome)

    async def apply_document(
        self, lease: GenerationLease, change: DocumentApply
    ) -> None:
        """Apply ``change`` onto the latest document under the row lock."""
        if change.replaces_document and await self._replace_unparseable(lease, change):
            return
        slot = SlotEdit(
            post_id=lease.post_id,
            user_id=self._user_id,
            edit=change.edit,
            events=_event_service(),
            ai_action=AI_ACTION_GENERATE_IMAGE if change.images_generated else None,
            metadata_edit=_MetadataChange(lease, change, datetime.now(UTC).isoformat()),
            discard=change.discard,
            change_summary=VERSION_SUMMARY_GENERATION,
        )
        try:
            async with self._sessions() as db:
                await apply_slot_edit(db, slot)
        except HTTPException as exc:
            raise InvalidBlogDocumentError(str(exc.detail)) from exc
        except BaseException:
            if change.discard is not None:
                change.discard()
            raise

    async def _replace_unparseable(
        self, lease: GenerationLease, change: DocumentApply
    ) -> bool:
        """Full-document write when the locked row does not parse as v2.

        The slot path rejects such a row (422) because there is nothing to
        merge onto; the freshly written article replaces it instead, through
        the same versioned write (snapshot of the old content, review reset).
        Returns ``False`` (no write) when the row parses.
        """
        async with self._sessions() as db:
            locked = await lock_blog_post(db, lease.post_id)
            try:
                parse_blog_content(locked.content)
            except InvalidBlogDocumentError:
                await self._write_replacement(db, (lease, change), locked)
                return True
            await db.rollback()
            return False

    async def _write_replacement(
        self,
        db: AsyncSession,
        job: tuple[GenerationLease, DocumentApply],
        locked: LockedBlogPostRow,
    ) -> None:
        lease, change = job
        metadata: object = locked.ai_generation_metadata
        current: dict[str, object] = (
            dict(metadata) if isinstance(metadata, dict) else {}
        )
        updated = _MetadataChange(lease, change, datetime.now(UTC).isoformat())(current)
        document = change.edit(parse_blog_content(bootstrap_content()))
        try:
            validated = validated_write(document.to_content(), updated)
        except HTTPException as exc:
            raise InvalidBlogDocumentError(str(exc.detail)) from exc
        await write_post_content(
            db,
            ContentWrite(
                post=locked,
                if_match=locked.lock_version,
                values={
                    "content": validated.content,
                    "featured_image_url": validated.featured_image_url,
                    "ai_generation_metadata": updated,
                },
                user_id=self._user_id,
                events=_event_service(),
                change_summary=VERSION_SUMMARY_GENERATION,
            ),
        )
        await db.commit()


__all__ = ["RunOwner", "SlotWriteGenerationStore"]
