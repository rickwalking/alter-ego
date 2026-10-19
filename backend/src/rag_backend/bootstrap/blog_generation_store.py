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
per-post cap (``count_one_image``).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from rag_backend.api.dependencies.blog_slot_write import SlotEdit, apply_slot_edit
from rag_backend.application.services.blog.blog_image_budget import count_one_image
from rag_backend.application.services.workflow_event_service import WorkflowEventService
from rag_backend.domain.constants.ai_disclosure import AI_ACTION_GENERATE_IMAGE
from rag_backend.domain.constants.blog_generation import VERSION_SUMMARY_GENERATION
from rag_backend.domain.models.blog_document import InvalidBlogDocumentError
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
        updated = with_voice_score(
            heartbeat(metadata, self.now), self.change.voice_score
        )
        for _image in range(self.change.images_generated):
            updated = count_one_image(updated)
        return updated


class SlotWriteGenerationStore:
    """``BlogGenerationStore``: run state lease-fenced, content via the slot path."""

    def __init__(self, sessions: SessionFactory, user_id: str) -> None:
        self._sessions = sessions
        self._user_id = user_id
        self._state = SqlBlogGenerationStore(sessions)

    async def heartbeat(self, lease: GenerationLease) -> None:
        """Stamp ``generation.heartbeat_at``."""
        await self._state.heartbeat(lease)

    async def read_content(self, lease: GenerationLease) -> dict[str, object]:
        """The row's current content."""
        return await self._state.read_content(lease)

    async def images_generated(self, lease: GenerationLease) -> int:
        """Images generated for the post so far."""
        return await self._state.images_generated(lease)

    async def finish(self, lease: GenerationLease, outcome: GenerationOutcome) -> None:
        """Record the final status."""
        await self._state.finish(lease, outcome)

    async def apply_document(
        self, lease: GenerationLease, change: DocumentApply
    ) -> None:
        """Apply ``change`` onto the latest document under the row lock."""
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


__all__ = ["SlotWriteGenerationStore"]
