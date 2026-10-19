"""Cover and section images of a blog post (AE-0424, ADR-0025).

One service generates every blog image (the editor routes here; AE-0425's bulk
generation reuses it). The provider writes the bytes straight into the
blog-images store (``<output>/blog-images/<post_id>/<uuid>.jpg``); the image is
only returned once the file is really there, and only the canonical URL (CDN,
or the same-origin ``/api/blog-images/...`` route) is stored. A provider URL
is never persisted; a failure raises :class:`BlogImageError` and the caller
leaves the slot unchanged.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from rag_backend.application.services.asset_cdn_service import AssetCdnService
from rag_backend.application.services.blog.blog_prompts import image_prompt
from rag_backend.application.services.blog_workflow_observability import (
    blog_ai_propagate,
)
from rag_backend.application.services.image_prompt_sanitizer import (
    sanitize_image_prompt,
)
from rag_backend.domain.constants import IMAGE_MODEL_OPENAI
from rag_backend.domain.constants.blog_document import BLOG_IMAGE_SOURCE_GENERATED
from rag_backend.domain.constants.blog_editor import (
    BLOG_IMAGE_EXTENSION,
    BLOG_IMAGES_DIR_NAME,
    BLOG_IMAGES_ROUTE_PREFIX,
    ERR_BLOG_IMAGE_GENERATION_FAILED,
    ERR_BLOG_IMAGE_PERSIST_FAILED,
    IMAGE_PROMPT_BODY_CHARS,
    IMAGE_PROMPT_MAX_CHARS,
    PHASE_BLOG_SECTION_IMAGE,
)
from rag_backend.domain.models.blog_document import BlogImage
from rag_backend.domain.protocols import ImageGenerationService


class BlogImageError(RuntimeError):
    """Image generation or persistence failed; ``code`` is the API detail."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class BlogImageStore:
    """Where blog image bytes live and how they are addressed."""

    root: Path
    cdn: AssetCdnService

    def new_path(self, post_id: str) -> Path:
        """A fresh ``<root>/<post_id>/<uuid>.jpg`` path (directory created)."""
        directory = self.root / post_id
        directory.mkdir(parents=True, exist_ok=True)
        return directory / f"{uuid.uuid4()}{BLOG_IMAGE_EXTENSION}"

    def url_for(self, post_id: str, filename: str) -> str:
        """The canonical URL: CDN when enabled, else the same-origin route."""
        if self.cdn.enabled:
            return self.cdn.resolve_url(f"{BLOG_IMAGES_DIR_NAME}/{post_id}/{filename}")
        return f"{BLOG_IMAGES_ROUTE_PREFIX}/{post_id}/{filename}"

    def file_for(self, post_id: str, filename: str) -> Path | None:
        """The stored file, or ``None`` when it does not exist."""
        path = self.root / post_id / filename
        return path if path.is_file() else None


@dataclass(frozen=True)
class BlogImageRequest:
    """One image to generate: the owner-editable scene and its alt text."""

    post_id: str
    scene: str
    alt: str


def default_scene(heading: str | None, body_md: str) -> str:
    """The deterministic scene of a slot: its heading plus a body excerpt."""
    excerpt = " ".join(body_md.split())[:IMAGE_PROMPT_BODY_CHARS]
    parts = [part for part in (heading or "", excerpt) if part.strip()]
    return ". ".join(parts)


def _clean_scene(scene: str) -> str:
    return sanitize_image_prompt(scene.strip())[:IMAGE_PROMPT_MAX_CHARS]


def _persisted(path: Path) -> bool:
    return path.is_file() and path.stat().st_size > 0


async def _call_provider(
    provider: ImageGenerationService, prompt: str, path: Path
) -> None:
    """The provider writes the bytes to ``path``; any failure is a 502."""
    try:
        await provider.generate_image(prompt, str(path))
    except Exception as exc:
        raise BlogImageError(ERR_BLOG_IMAGE_GENERATION_FAILED) from exc


class BlogImageService:
    """Generate a blog image into the store and describe it as a ``BlogImage``."""

    def __init__(
        self, provider: ImageGenerationService | None, store: BlogImageStore
    ) -> None:
        self._provider = provider
        self._store = store

    async def generate(self, request: BlogImageRequest) -> BlogImage:
        """Generate, persist and return the image; raises :class:`BlogImageError`."""
        provider = self._provider
        if provider is None:
            raise BlogImageError(ERR_BLOG_IMAGE_GENERATION_FAILED)
        scene = _clean_scene(request.scene)
        prompt = image_prompt(scene)
        path = self._store.new_path(request.post_id)
        with blog_ai_propagate(request.post_id, PHASE_BLOG_SECTION_IMAGE):
            await _call_provider(provider, prompt, path)
        if not _persisted(path):
            raise BlogImageError(ERR_BLOG_IMAGE_PERSIST_FAILED)
        return BlogImage(
            url=self._store.url_for(request.post_id, path.name),
            alt=request.alt,
            source=BLOG_IMAGE_SOURCE_GENERATED,
            prompt=scene,
            model=IMAGE_MODEL_OPENAI,
            created_at=datetime.now(UTC).isoformat(),
        )


__all__ = [
    "BlogImageError",
    "BlogImageRequest",
    "BlogImageService",
    "BlogImageStore",
    "default_scene",
]
