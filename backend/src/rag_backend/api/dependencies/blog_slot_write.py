"""Shared edge of the per-slot editor routes (images, rewrite, translation).

Each route: checks ``If-Match`` against the row **before** any LLM/image spend
(409 on a stale editor), parses the stored document strictly (a non-migrated
row is a 422 the editor shows as "migration pending", AE-0424 AC15), edits one
slot (404 for an unknown section/translation) and stores the whole document
through the versioned :func:`write_post_content` path.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol, TypeVar

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


@dataclass(frozen=True)
class SlotWrite:
    """Store ``document`` as the new content of ``post``."""

    post: LockedBlogPostRow
    if_match: int | None
    document: BlogDocument
    user_id: str
    events: WorkflowEventService
    change_summary: str = VERSION_SUMMARY_SAVE
    # The AI action this write records (disclosure label), if any.
    ai_action: str | None = None


def _ai_action_values(post: LockedBlogPostRow, action: str | None) -> dict[str, object]:
    if action is None:
        return {}
    metadata = post.ai_generation_metadata
    current = dict(metadata) if isinstance(metadata, dict) else {}
    updated = AiDisclosureService().record_action(current, action)
    return {
        "ai_generation_metadata": updated,
        "ai_disclosure_label": updated.get("ai_disclosure_label", AI_DISCLOSURE_NONE),
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


async def store_document(db: AsyncSession, write: SlotWrite) -> None:
    """Validate and store the edited document (versioned, snapshotted)."""
    validated = validated_write(
        write.document.to_content(), write.post.ai_generation_metadata
    )
    await write_post_content(
        db,
        ContentWrite(
            post=write.post,
            if_match=write.if_match,
            values={
                "content": validated.content,
                "featured_image_url": validated.featured_image_url,
                **_ai_action_values(write.post, write.ai_action),
            },
            user_id=write.user_id,
            events=write.events,
            change_summary=write.change_summary,
        ),
    )


__all__ = [
    "SlotWrite",
    "edit_or_404",
    "load_document",
    "require_current_version",
    "store_document",
]
