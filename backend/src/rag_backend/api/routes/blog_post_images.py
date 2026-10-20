"""Cover and section image routes of the blog editor (AE-0424, ADR-0025).

``/cover/image`` and ``/sections/{section_id}/image`` support generate /
regenerate (POST, optional edited ``prompt``), alt + caption edits (PATCH) and
remove (DELETE) on the language the editor shows (``?language=pt|en``).

Generation follows the shared slot-write contract (``blog_slot_write``):
preflight (``If-Match``, v2 document, slot exists), the per-post image budget
reserved under the row lock (``blog_image_budget``), then the provider spend, then :func:`apply_slot_edit` onto the LATEST document under
a row lock; a failed write deletes the new file. After every write the store
keeps only files referenced by the content or a version snapshot.

``GET /blog-images/{post_id}/{file}`` serves the store: published posts to
anyone (revalidated cache), other posts only to their author or an admin
(``private, no-store``), else the uniform 404 (ADR-0013).
"""

import re
from dataclasses import dataclass
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import FileResponse

from rag_backend.api.dependencies.auth import get_optional_user
from rag_backend.api.dependencies.blog_editor import (
    CoverTarget,
    SectionTarget,
    Session,
    blog_image_cost_cap,
    blog_images_store,
    build_blog_image_service,
    prune_unreferenced_images,
)
from rag_backend.api.dependencies.blog_image_budget import (
    BudgetReservation,
    reserve_image_budget,
)
from rag_backend.api.dependencies.blog_slot_write import (
    DocumentEdit,
    LockedBlogPostRow,
    SlotEdit,
    apply_slot_edit,
    edit_or_404,
    load_document,
    require_current_version,
)
from rag_backend.api.dependencies.resource_access import (
    get_blog_post_by_id,
    get_blog_post_for_user,
)
from rag_backend.api.middleware.rate_limiting import limiter
from rag_backend.api.routes.blog_post_ai import blog_event_service
from rag_backend.api.schemas.blog_post import BlogPostResponse
from rag_backend.api.schemas.blog_post_editor import (
    BlogImageGenerateRequest,
    BlogImagePatchRequest,
)
from rag_backend.application.services.blog.blog_document_edits import (
    find_section,
    language_document,
    with_cover,
    with_section,
)
from rag_backend.application.services.blog.blog_image_service import (
    BlogImageError,
    BlogImageRequest,
    default_scene,
)
from rag_backend.domain.constants.ai_disclosure import AI_ACTION_GENERATE_IMAGE
from rag_backend.domain.constants.blog_editor import (
    BLOG_IMAGE_CACHE_NOT_FOUND,
    BLOG_IMAGE_CACHE_PRIVATE,
    BLOG_IMAGE_CACHE_PUBLIC,
    BLOG_IMAGE_FILENAME_PATTERN,
    BLOG_IMAGE_MEDIA_TYPES,
    ERR_BLOG_IMAGE_NOT_FOUND,
    ERR_BLOG_SECTION_IMAGE_MISSING,
)
from rag_backend.domain.constants.blog_post import BlogPostStatus
from rag_backend.domain.constants.rate_limits import (
    RATE_LIMIT_AI_ENDPOINTS,
    RATE_LIMIT_WORKFLOW_ENDPOINTS,
)
from rag_backend.domain.models import User
from rag_backend.domain.models.blog_document import BlogDocument, BlogImage

router = APIRouter(tags=["blog_post_images"])

# Path params are fields of the target dataclasses (``Depends()``).
COVER_PATH = "/blog-posts/{post_id}/cover/image"
SECTION_PATH = "/blog-posts/{post_id}/sections/{section_id}/image"
IMAGE_FILE_PATH = "/blog-images/{post_id}/{filename}"
CACHE_CONTROL_HEADER = "Cache-Control"


@dataclass(frozen=True)
class _Slot:
    """The image slot: the cover (``section_id is None``) or one section's."""

    language: str
    section_id: str | None = None


@dataclass(frozen=True)
class _SlotEdit:
    db: Session
    post: LockedBlogPostRow
    post_id: str
    user_id: str
    slot: _Slot


def _current(document: BlogDocument, slot: _Slot) -> BlogImage | None:
    current = language_document(document, slot.language)
    if slot.section_id is None:
        return current.cover
    return find_section(current, slot.section_id).image


def _place(
    document: BlogDocument, slot: _Slot, image: BlogImage | None
) -> BlogDocument:
    """Put ``image`` into the slot of ``document`` (the section by id)."""
    if slot.section_id is None:
        return with_cover(document, slot.language, image)
    current = language_document(document, slot.language)
    section = find_section(current, slot.section_id)
    updated = section.model_copy(update={"image": image})
    return with_section(document, slot.language, updated)


def _request(
    edit: _SlotEdit, document: BlogDocument, prompt: str | None
) -> BlogImageRequest:
    current = language_document(document, edit.slot.language)
    title = edit.post.title
    if edit.slot.section_id is None:
        lede = current.sections[0].body_md if current.sections else ""
        scene, alt = default_scene(title, lede), title
    else:
        section = find_section(current, edit.slot.section_id)
        scene = default_scene(section.heading, section.body_md)
        alt = section.heading or title
    chosen = prompt.strip() if prompt and prompt.strip() else scene
    return BlogImageRequest(post_id=edit.post_id, scene=chosen, alt=alt or chosen)


async def _write(edit: _SlotEdit, change: SlotEdit) -> LockedBlogPostRow:
    written = await apply_slot_edit(edit.db, change)
    prune_unreferenced_images(written)
    return written


def _change(edit: _SlotEdit, document_edit: DocumentEdit) -> SlotEdit:
    return SlotEdit(
        post_id=edit.post_id,
        user_id=edit.user_id,
        edit=document_edit,
        events=blog_event_service(),
    )


async def _generated_image(edit: _SlotEdit, prompt: str | None) -> BlogImage:
    """Preflight (document, slot), reserve the budget, then the provider spend."""
    document = load_document(edit.post)
    request = edit_or_404(lambda: _request(edit, document, prompt))
    # Reserve under the row lock and commit: no transaction is held during
    # the slow spend; the write re-reads the row ``FOR UPDATE`` afterwards.
    await reserve_image_budget(
        edit.db, BudgetReservation(post_id=edit.post_id, cap=blog_image_cost_cap())
    )
    try:
        return await build_blog_image_service().generate(request)
    except BlogImageError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=exc.code
        ) from exc


async def _generate(edit: _SlotEdit, prompt: str | None) -> LockedBlogPostRow:
    image = await _generated_image(edit, prompt)
    post_id = edit.post_id
    filename = image.url.rsplit("/", 1)[-1]
    change = SlotEdit(
        post_id=post_id,
        user_id=edit.user_id,
        edit=lambda latest: _place(latest, edit.slot, image),
        events=blog_event_service(),
        ai_action=AI_ACTION_GENERATE_IMAGE,
        discard=lambda: blog_images_store().delete(post_id, filename),
    )
    return await _write(edit, change)


def _patched(
    document: BlogDocument, slot: _Slot, body: BlogImagePatchRequest
) -> BlogDocument:
    image = _current(document, slot)
    if image is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERR_BLOG_SECTION_IMAGE_MISSING
        )
    changes: dict[str, object] = {}
    if body.alt is not None:
        changes["alt"] = body.alt.strip()
    if "caption" in body.model_fields_set:
        changes["caption"] = (body.caption or "").strip() or None
    return _place(document, slot, image.model_copy(update=changes))


async def _patch(edit: _SlotEdit, body: BlogImagePatchRequest) -> LockedBlogPostRow:
    document = load_document(edit.post)
    edit_or_404(lambda: _patched(document, edit.slot, body))
    return await _write(edit, _change(edit, lambda d: _patched(d, edit.slot, body)))


async def _remove(edit: _SlotEdit) -> LockedBlogPostRow:
    document = load_document(edit.post)
    edit_or_404(lambda: _place(document, edit.slot, None))
    return await _write(edit, _change(edit, lambda d: _place(d, edit.slot, None)))


async def _edit(target: CoverTarget | SectionTarget) -> _SlotEdit:
    """Load the post and run the preflight ``If-Match`` check (before spend)."""
    section_id = getattr(target, "section_id", None)
    post = await get_blog_post_for_user(target.db, target.post_id, target.current_user)
    require_current_version(post, target.if_match)
    return _SlotEdit(
        db=target.db,
        post=post,
        post_id=str(post.id),
        user_id=target.current_user.id,
        slot=_Slot(target.language, section_id),
    )


Cover = Annotated[CoverTarget, Depends()]
Section = Annotated[SectionTarget, Depends()]


@router.post(COVER_PATH, response_model=BlogPostResponse, summary="Generate the cover")
@limiter.limit(RATE_LIMIT_AI_ENDPOINTS)
async def generate_cover_image(
    request: Request, body: BlogImageGenerateRequest, target: Cover
) -> LockedBlogPostRow:
    """Generate or regenerate the cover (502 on failure, cover unchanged)."""
    return await _generate(await _edit(target), body.prompt)


@router.patch(
    COVER_PATH, response_model=BlogPostResponse, summary="Edit cover alt/caption"
)
@limiter.limit(RATE_LIMIT_WORKFLOW_ENDPOINTS)
async def patch_cover_image(
    request: Request, body: BlogImagePatchRequest, target: Cover
) -> LockedBlogPostRow:
    """Edit the cover's alt (never blank) and caption."""
    return await _patch(await _edit(target), body)


@router.delete(COVER_PATH, response_model=BlogPostResponse, summary="Remove the cover")
@limiter.limit(RATE_LIMIT_WORKFLOW_ENDPOINTS)
async def delete_cover_image(request: Request, target: Cover) -> LockedBlogPostRow:
    """Clear the cover (PT: ``featured_image_url`` becomes ``NULL``)."""
    return await _remove(await _edit(target))


@router.post(
    SECTION_PATH, response_model=BlogPostResponse, summary="Generate a section image"
)
@limiter.limit(RATE_LIMIT_AI_ENDPOINTS)
async def generate_section_image(
    request: Request, body: BlogImageGenerateRequest, target: Section
) -> LockedBlogPostRow:
    """Generate or regenerate one section's image (alt defaults to its heading)."""
    return await _generate(await _edit(target), body.prompt)


@router.patch(
    SECTION_PATH,
    response_model=BlogPostResponse,
    summary="Edit section image alt/caption",
)
@limiter.limit(RATE_LIMIT_WORKFLOW_ENDPOINTS)
async def patch_section_image(
    request: Request, body: BlogImagePatchRequest, target: Section
) -> LockedBlogPostRow:
    """Edit one section image's alt (never blank) and caption."""
    return await _patch(await _edit(target), body)


@router.delete(
    SECTION_PATH, response_model=BlogPostResponse, summary="Remove a section image"
)
@limiter.limit(RATE_LIMIT_WORKFLOW_ENDPOINTS)
async def delete_section_image(request: Request, target: Section) -> LockedBlogPostRow:
    """Set one section's image to ``null``."""
    return await _remove(await _edit(target))


@dataclass
class ImageFileTarget:
    """A stored image request: the post, file name, session and optional user."""

    post_id: UUID
    filename: str
    db: Session
    user: Annotated[User | None, Depends(get_optional_user)]


def _not_found() -> HTTPException:
    """Uniform 404 (ADR-0013), never cached (AE-0439, QA F-14).

    The edge caches uncached 404s (Cloudflare's default browser TTL is
    14400 s); pinning ``no-store`` keeps a draft 404 from lingering after
    the post is published.
    """
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=ERR_BLOG_IMAGE_NOT_FOUND,
        headers={CACHE_CONTROL_HEADER: BLOG_IMAGE_CACHE_NOT_FOUND},
    )


def _cache_policy(post: LockedBlogPostRow, user: User | None) -> str:
    """Public for published posts; author/admin only otherwise (else 404)."""
    if post.status == BlogPostStatus.PUBLISHED.value:
        return BLOG_IMAGE_CACHE_PUBLIC
    author_id = getattr(post, "author_id", None)
    if user is not None and (user.is_admin() or str(user.id) == str(author_id)):
        return BLOG_IMAGE_CACHE_PRIVATE
    raise _not_found()


@router.get(IMAGE_FILE_PATH, summary="Serve a blog image")
@limiter.limit(RATE_LIMIT_WORKFLOW_ENDPOINTS)
async def get_blog_image(
    request: Request, target: Annotated[ImageFileTarget, Depends()]
) -> FileResponse:
    """Serve a stored blog image (only ``<uuid4>.<jpg|png|webp>`` names)."""
    match = re.fullmatch(BLOG_IMAGE_FILENAME_PATTERN, target.filename)
    if match is None:
        raise _not_found()
    try:
        post = await get_blog_post_by_id(target.db, target.post_id)
    except HTTPException as exc:
        raise _not_found() from exc
    cache = _cache_policy(post, target.user)
    path = blog_images_store().file_for(str(target.post_id), target.filename)
    if path is None:
        raise _not_found()
    return FileResponse(
        path=str(path),
        media_type=BLOG_IMAGE_MEDIA_TYPES[match.group(1)],
        headers={CACHE_CONTROL_HEADER: cache},
    )
