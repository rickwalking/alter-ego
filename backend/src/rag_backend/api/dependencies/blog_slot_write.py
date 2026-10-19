"""Shared write path of the per-slot editor routes (AE-0424; reused by AE-0425).

A slot action (image, rewrite, translation) spends 10-60 s on a provider. The
contract that keeps that paid result:

1. **Preflight** (before any spend): ``require_current_version`` (428/409),
   ``load_document`` (422 for a non-migrated row, AC15) and the slot lookup
   (404) on the loaded row.
2. **Spend** the provider call outside any lock.
3. **Commit with** :func:`apply_slot_edit`: the row is re-read
   ``SELECT ... FOR UPDATE``, ``SlotEdit.edit`` is applied onto the LATEST
   document (by section id; only the section must still exist, else 404) and
   stored through :func:`write_post_content` at the locked ``lock_version``,
   so a concurrent cover + section generation or a Save during the spend never
   409s. The review reset and the version snapshot come from the locked row.
   ``SlotEdit.discard`` runs when that write fails (e.g. delete the new image
   file), so a failed write leaves no orphan.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol, TypeVar
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.api.dependencies.blog_content_write import (
    BlogPostRow,
    ContentWrite,
    require_if_match,
    write_post_content,
)
from rag_backend.api.dependencies.blog_document import (
    raise_invalid_document,
    validated_write,
)
from rag_backend.api.dependencies.resource_access import lock_blog_post
from rag_backend.application.services.ai_disclosure_service import AiDisclosureService
from rag_backend.application.services.blog.blog_document_edits import BlogEditError
from rag_backend.application.services.workflow_event_service import WorkflowEventService
from rag_backend.domain.constants.ai_disclosure import AI_DISCLOSURE_NONE
from rag_backend.domain.constants.blog_editor import VERSION_SUMMARY_SAVE
from rag_backend.domain.constants.optimistic_locking import ERR_VERSION_CONFLICT
from rag_backend.domain.models.blog_document import (
    BlogDocument,
    InvalidBlogDocumentError,
    parse_blog_content,
)

T = TypeVar("T")


class LockedBlogPostRow(BlogPostRow, Protocol):
    """A content row plus the lock/metadata fields a slot write checks."""

    lock_version: int
    ai_generation_metadata: object


DocumentEdit = Callable[[BlogDocument], BlogDocument]
MetadataEdit = Callable[[dict[str, object]], dict[str, object]]


@dataclass(frozen=True)
class SlotEdit:
    """One post-spend slot write onto the latest document of ``post_id``."""

    post_id: UUID | str
    user_id: str
    edit: DocumentEdit
    events: WorkflowEventService
    ai_action: str | None = None
    # Extra ``ai_generation_metadata`` change in the same write (image budget).
    metadata_edit: MetadataEdit | None = None
    discard: Callable[[], None] | None = None
    change_summary: str = VERSION_SUMMARY_SAVE


def _metadata_values(post: LockedBlogPostRow, slot: SlotEdit) -> dict[str, object]:
    if slot.ai_action is None and slot.metadata_edit is None:
        return {}
    metadata = post.ai_generation_metadata
    current = dict(metadata) if isinstance(metadata, dict) else {}
    if slot.metadata_edit is not None:
        current = slot.metadata_edit(current)
    if slot.ai_action is not None:
        current = AiDisclosureService().record_action(current, slot.ai_action)
    return {
        "ai_generation_metadata": current,
        "ai_disclosure_label": current.get("ai_disclosure_label", AI_DISCLOSURE_NONE),
    }


def require_current_version(post: LockedBlogPostRow, if_match: int | None) -> None:
    """428 without ``If-Match``; 409 when it is not the row's lock version."""
    if require_if_match(if_match) != post.lock_version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=ERR_VERSION_CONFLICT
        )


def load_document(post: LockedBlogPostRow) -> BlogDocument:
    """The stored ``blog.v2`` document (strict: a legacy row is a 422)."""
    try:
        return parse_blog_content(post.content)
    except InvalidBlogDocumentError as exc:
        raise_invalid_document(exc)


def edit_or_404(edit: Callable[[], T]) -> T:
    """Run a document edit; an unknown section/translation is a 404."""
    try:
        return edit()
    except BlogEditError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=exc.code
        ) from exc


async def _write_latest(db: AsyncSession, slot: SlotEdit) -> LockedBlogPostRow:
    locked = await lock_blog_post(db, slot.post_id)
    document = edit_or_404(lambda: slot.edit(load_document(locked)))
    validated = validated_write(document.to_content(), locked.ai_generation_metadata)
    await write_post_content(
        db,
        ContentWrite(
            post=locked,
            if_match=locked.lock_version,
            values={
                "content": validated.content,
                "featured_image_url": validated.featured_image_url,
                **_metadata_values(locked, slot),
            },
            user_id=slot.user_id,
            events=slot.events,
            change_summary=slot.change_summary,
        ),
    )
    await db.commit()
    await db.refresh(locked)
    return locked


async def apply_slot_edit(db: AsyncSession, slot: SlotEdit) -> LockedBlogPostRow:
    """Lock, apply ``slot.edit`` onto the latest document, store and commit."""
    try:
        return await _write_latest(db, slot)
    except HTTPException:
        await db.rollback()
        if slot.discard is not None:
            slot.discard()
        raise


__all__ = [
    "DocumentEdit",
    "LockedBlogPostRow",
    "MetadataEdit",
    "SlotEdit",
    "apply_slot_edit",
    "edit_or_404",
    "load_document",
    "require_current_version",
]
