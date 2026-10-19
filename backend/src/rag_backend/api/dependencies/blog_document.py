"""``blog.v2`` content handling at the blog-post API edge (AE-0423, ADR-0025).

Every route that writes ``blog_posts.content`` goes through
``BlogDocumentService`` here, so the strict v2 shape and the
``featured_image_url == content.cover.url`` projection are enforced in one
place. ``featured_image_url`` is never taken from a client: it is derived from
the cover. An invalid document is a 422 whose ``detail`` starts with the
error code (the editor keys its "migration pending" banner on it, AE-0424).
"""

from __future__ import annotations

from typing import NoReturn

from fastapi import HTTPException, status

from rag_backend.application.services.blog.blog_document_service import (
    BlogDocumentService,
    BlogDocumentWrite,
    is_generation_in_progress,
)
from rag_backend.domain.models.blog_document import (
    BlogImage,
    InvalidBlogDocumentError,
)

CONTENT_FIELD = "content"
FEATURED_IMAGE_URL_FIELD = "featured_image_url"


def raise_invalid_document(exc: InvalidBlogDocumentError) -> NoReturn:
    """Map a document error to a 422 ``code`` / ``code: message`` detail."""
    detail = exc.code if exc.message == exc.code else f"{exc.code}: {exc.message}"
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail
    ) from exc


def validated_write(content: object, metadata: object) -> BlogDocumentWrite:
    """Strict v2 write validation (422 on failure) plus the cover projection."""
    try:
        return BlogDocumentService.validate_for_write(
            content, generation_in_progress=is_generation_in_progress(metadata)
        )
    except InvalidBlogDocumentError as exc:
        raise_invalid_document(exc)


def prepare_create_payload(payload: dict[str, object]) -> None:
    """Empty content becomes a fresh v2 document; anything else must be v2."""
    content = payload.get(CONTENT_FIELD)
    if not content:
        content = BlogDocumentService.initial_content()
    write = validated_write(content, None)
    payload[CONTENT_FIELD] = write.content
    payload[FEATURED_IMAGE_URL_FIELD] = write.featured_image_url


def prepare_update_values(update_data: dict[str, object], metadata: object) -> None:
    """Validate a PUT's content and re-project ``featured_image_url`` from it."""
    update_data.pop(FEATURED_IMAGE_URL_FIELD, None)
    if CONTENT_FIELD not in update_data:
        return
    write = validated_write(update_data[CONTENT_FIELD], metadata)
    update_data[CONTENT_FIELD] = write.content
    update_data[FEATURED_IMAGE_URL_FIELD] = write.featured_image_url


def cover_write(content: object, cover: BlogImage | None) -> BlogDocumentWrite:
    """Set/clear the cover through the service so the projection stays synced."""
    try:
        return BlogDocumentService.with_cover(content, cover)
    except InvalidBlogDocumentError as exc:
        raise_invalid_document(exc)


def assert_publishable(content: object) -> None:
    """422 unless the document has >= 1 non-empty section (cover optional)."""
    try:
        BlogDocumentService.assert_publishable(content)
    except InvalidBlogDocumentError as exc:
        raise_invalid_document(exc)


def display_content(content: object, post_id: str) -> dict[str, object]:
    """Editor read: the v2 document (legacy rows adapted in memory, temporary)."""
    return BlogDocumentService.read_document(content, post_id).to_content()


__all__ = [
    "assert_publishable",
    "cover_write",
    "display_content",
    "prepare_create_payload",
    "prepare_update_values",
    "raise_invalid_document",
    "validated_write",
]
