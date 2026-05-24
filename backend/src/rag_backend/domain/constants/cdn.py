"""Constants for CDN asset URL resolution (PERF-002)."""

CDN_PATH_BLOG_IMAGES = "blog-images"
CDN_PATH_CAROUSEL_IMAGES = "carousels"

HEADER_CACHE_CONTROL = "Cache-Control"
CDN_CACHE_MAX_AGE = 31536000

__all__ = [
    "CDN_CACHE_MAX_AGE",
    "CDN_PATH_BLOG_IMAGES",
    "CDN_PATH_CAROUSEL_IMAGES",
    "HEADER_CACHE_CONTROL",
]
