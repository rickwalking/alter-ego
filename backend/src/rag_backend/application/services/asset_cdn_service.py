"""CDN URL resolution for image assets (PERF-002)."""

from __future__ import annotations

from rag_backend.domain.constants.cdn import (
    CDN_PATH_BLOG_IMAGES,
    CDN_PATH_CAROUSEL_IMAGES,
)


class AssetCdnService:
    """Rewrites local asset paths to CDN URLs when configured."""

    def __init__(self, *, cdn_base_url: str = "", enabled: bool = False) -> None:
        self._cdn_base_url = cdn_base_url.rstrip("/") if cdn_base_url else ""
        self._enabled = enabled and bool(self._cdn_base_url)

    @property
    def enabled(self) -> bool:
        return self._enabled

    def resolve_blog_image(self, relative_path: str) -> str:
        """Return CDN URL for a blog image path."""
        if not self._enabled:
            return relative_path
        filename = relative_path.split("/")[-1]
        return f"{self._cdn_base_url}/{CDN_PATH_BLOG_IMAGES}/{filename}"

    def resolve_carousel_image(self, project_id: str, slide_index: int) -> str:
        """Return CDN URL for a carousel slide image."""
        if not self._enabled:
            return f"/api/carousels/{project_id}/images/slide_{slide_index}.jpg"
        base = f"{self._cdn_base_url}/{CDN_PATH_CAROUSEL_IMAGES}/{project_id}"
        return f"{base}/slide_{slide_index}.jpg"

    def resolve_url(self, path: str) -> str:
        """Resolve any asset path to CDN URL if enabled."""
        if not self._enabled or path.startswith("http"):
            return path
        clean = path.lstrip("/")
        return f"{self._cdn_base_url}/{clean}"


__all__ = ["AssetCdnService"]
