"""Public JPEG URLs Meta's fetcher can GET. Pure: no settings, no I/O."""

from __future__ import annotations

from dataclasses import dataclass

SLIDE_IMAGE_URL = (
    "{base}/api/carousels/{project_id}/slide-images/{language}/slide_{number}.jpg"
)


@dataclass(frozen=True, kw_only=True)
class SlideImageUrlRequest:
    """Inputs for one carousel's public slide URLs."""

    base_url: str
    project_id: str
    slide_numbers: tuple[int, ...]
    language: str


def build_public_slide_image_urls(request: SlideImageUrlRequest) -> list[str]:
    """Return one absolute JPEG URL per slide number, in the given order."""
    base = request.base_url.rstrip("/")
    return [
        SLIDE_IMAGE_URL.format(
            base=base,
            project_id=request.project_id,
            language=request.language,
            number=number,
        )
        for number in request.slide_numbers
    ]
