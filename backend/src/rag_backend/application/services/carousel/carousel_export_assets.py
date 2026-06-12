"""Prepare on-disk carousel assets before Playwright slide export."""

from __future__ import annotations

from pathlib import Path

from rag_backend.domain.constants import SHARED_IMAGES_DIR_NAME

_DEFAULT_CREATOR_AVATAR_FILENAME = "about-pedro.jpg"
_OPTIMIZED_IMAGE_MAX_EDGE_PX = 1600
_OPTIMIZED_IMAGE_JPEG_QUALITY = 82
_AVATAR_SOURCE_CANDIDATES: tuple[Path, ...] = (
    Path("/app/assets/about-pedro.jpg"),
    Path("/app/frontend/public/about-pedro.jpg"),
    Path(__file__).resolve().parents[6] / "frontend/public/about-pedro.jpg",
)


def optimize_carousel_artwork_images(images_dir: Path) -> None:
    """Shrink hero images so Playwright preflight can decode slides in time."""
    if not images_dir.is_dir():
        return
    from PIL import Image

    for image_file in sorted(images_dir.glob("slide_*.jpg")):
        with Image.open(image_file) as img:
            converted = img.convert("RGB")
            converted.thumbnail((
                _OPTIMIZED_IMAGE_MAX_EDGE_PX,
                _OPTIMIZED_IMAGE_MAX_EDGE_PX,
            ))
            converted.save(
                image_file,
                "JPEG",
                quality=_OPTIMIZED_IMAGE_JPEG_QUALITY,
                optimize=True,
            )


def ensure_cta_avatar_image(output_dir: Path) -> None:
    """Copy the default creator avatar when the CTA slide references it."""
    images_dir = output_dir / SHARED_IMAGES_DIR_NAME
    images_dir.mkdir(parents=True, exist_ok=True)
    avatar_target = images_dir / _DEFAULT_CREATOR_AVATAR_FILENAME
    if avatar_target.is_file():
        return
    for avatar_source in _AVATAR_SOURCE_CANDIDATES:
        if not avatar_source.is_file():
            continue
        avatar_target.write_bytes(avatar_source.read_bytes())
        return


def prepare_carousel_export_assets(output_dir: Path) -> None:
    """Ensure export prerequisites exist before Playwright screenshot capture."""
    images_dir = output_dir / SHARED_IMAGES_DIR_NAME
    ensure_cta_avatar_image(output_dir)
    optimize_carousel_artwork_images(images_dir)


__all__ = [
    "ensure_cta_avatar_image",
    "optimize_carousel_artwork_images",
    "prepare_carousel_export_assets",
]
