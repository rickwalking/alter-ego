"""Composition edge of the blog section editor routes (AE-0424, ADR-0025).

- Service builders: the blog-images store, the image service (gpt-image-2 +
  the versioned image template) and the PT -> EN translation service. They
  read the container here (``api/dependencies`` is the sanctioned locator seam)
  and inject the ``agents`` prompt renderers, so the application services never
  import the agents layer.
- Request targets: dataclass dependencies that bundle a route's path, header,
  query, session and user parameters, so each route keeps <= 3 arguments.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Protocol
from uuid import UUID

from fastapi import Depends, Header, Query
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.agents.blog_editor_prompts import (
    image_prompt,
    translate_section_prompt,
)
from rag_backend.api.dependencies.database import get_db
from rag_backend.api.dependencies.knowledge import get_container
from rag_backend.api.dependencies.roles import EditorUser
from rag_backend.application.services.asset_cdn_service import AssetCdnService
from rag_backend.application.services.blog.blog_image_service import BlogImageService
from rag_backend.application.services.blog.blog_image_store import (
    BlogImageStore,
    referenced_filenames,
)
from rag_backend.application.services.blog.blog_translation_service import (
    BlogTranslationService,
)
from rag_backend.domain.constants import IMAGE_MODEL_OPENAI, IMAGE_STYLE_CINEMATIC
from rag_backend.domain.constants.blog_editor import (
    BLOG_EDITOR_LANGUAGE_PATTERN,
    BLOG_IMAGES_DIR_NAME,
    BLOG_LANGUAGE_PT,
)
from rag_backend.domain.constants.optimistic_locking import HTTP_HEADER_IF_MATCH

IfMatch = Annotated[int | None, Header(alias=HTTP_HEADER_IF_MATCH)]
Language = Annotated[str, Query(pattern=BLOG_EDITOR_LANGUAGE_PATTERN)]
Session = Annotated[AsyncSession, Depends(get_db)]


def blog_images_store() -> BlogImageStore:
    """The blog-images store: ``<carousel_output_dir>/blog-images`` (+ CDN)."""
    settings = get_container().settings()
    cdn = AssetCdnService(
        cdn_base_url=settings.cdn_base_url, enabled=settings.cdn_enabled
    )
    root = Path(settings.carousel_output_dir) / BLOG_IMAGES_DIR_NAME
    return BlogImageStore(root=root, cdn=cdn)


class StoredImagesRow(Protocol):
    """The row fields that decide which stored images are still referenced."""

    id: object
    content: object
    version_history: object


def prune_unreferenced_images(post: StoredImagesRow) -> int:
    """Delete store files referenced by neither the content nor the history.

    Run after every committed content write (slot routes, PUT, restore): a
    regenerated / removed image stays while a version snapshot can restore it,
    and goes once nothing references it (AE-0424 review).
    """
    keep = referenced_filenames(post.content, post.version_history)
    return blog_images_store().prune(str(post.id), keep)


def blog_image_cost_cap() -> int:
    """``BLOG_IMAGE_COST_CAP``: images generated per post before refusing."""
    return int(get_container().settings().blog_image_cost_cap)


def build_blog_image_service() -> BlogImageService:
    """Cover/section image generation through gpt-image-2 (ADR-0025)."""
    registry = get_container().image_provider_registry()
    try:
        provider = registry.resolve(IMAGE_MODEL_OPENAI, IMAGE_STYLE_CINEMATIC)
    except RuntimeError:
        return BlogImageService(None, blog_images_store(), image_prompt)
    return BlogImageService(provider.service, blog_images_store(), image_prompt)


def build_blog_translation_service() -> BlogTranslationService:
    """PT -> EN translation for the editor's "Generate EN translation"."""
    llm = get_container().llm_service()
    return BlogTranslationService(llm, translate_section_prompt)


@dataclass
class PostTarget:
    """A content write on one post: path id, session, caller and ``If-Match``."""

    post_id: UUID
    db: Session
    current_user: EditorUser
    if_match: IfMatch = None


@dataclass
class CoverTarget:
    """The cover slot of one content language (``?language=pt|en``)."""

    post_id: UUID
    db: Session
    current_user: EditorUser
    if_match: IfMatch = None
    language: Language = BLOG_LANGUAGE_PT


@dataclass
class SectionTarget:
    """One section (image or body) of one content language."""

    post_id: UUID
    section_id: str
    db: Session
    current_user: EditorUser
    if_match: IfMatch = None
    language: Language = BLOG_LANGUAGE_PT


__all__ = [
    "CoverTarget",
    "PostTarget",
    "SectionTarget",
    "Session",
    "blog_image_cost_cap",
    "blog_images_store",
    "build_blog_image_service",
    "build_blog_translation_service",
    "prune_unreferenced_images",
]
