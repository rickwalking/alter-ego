"""Unit tests for asset CDN service (PERF-002)."""

from rag_backend.application.services.asset_cdn_service import AssetCdnService


def test_cdn_disabled_returns_local_path() -> None:
    service = AssetCdnService(cdn_base_url="https://cdn.example.com", enabled=False)
    assert service.resolve_url("/local/path.jpg") == "/local/path.jpg"


def test_cdn_enabled_rewrites_url() -> None:
    service = AssetCdnService(cdn_base_url="https://cdn.example.com", enabled=True)
    assert service.resolve_blog_image("blog-images/photo.jpg") == (
        "https://cdn.example.com/blog-images/photo.jpg"
    )
