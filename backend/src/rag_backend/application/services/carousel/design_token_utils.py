"""Design-token utilities for carousel projects.

Functions that build and merge design tokens from disk state.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from rag_backend.application.services.carousel.artifact_path_resolver import (
    resolve_language_dir,
    resolve_shared_images_dir,
)
from rag_backend.application.services.carousel.types import slide_count_from_config
from rag_backend.domain.constants import (
    BRAND_KEYWORDS,
    BRAND_PALETTES,
    CAROUSEL_THEMES,
    SWIPE_TEXT_EN,
)
from rag_backend.domain.models import CarouselProject

_SAFE_IMAGE_FILENAME = re.compile(r"^[a-zA-Z0-9_\-\.]+$")
_SLIDE_IMAGE_FILENAME = re.compile(r"^slide_(\d+)\.jpg$")


def _slide_image_numbers(output_dir: str | None, subdir: str) -> list[int]:
    if not output_dir:
        return []
    slide_dir = Path(output_dir) / subdir
    return _numbers_from_slide_dir(slide_dir)


def _numbers_from_slide_dir(slide_dir: Path) -> list[int]:
    if not slide_dir.is_dir():
        return []
    numbers: set[int] = set()
    for path in slide_dir.glob("slide_*.jpg"):
        match = _SLIDE_IMAGE_FILENAME.fullmatch(path.name)
        if match and path.is_file():
            numbers.add(int(match.group(1)))
    return sorted(numbers)


def _count_slide_images(output_dir: str | None) -> int:
    counts = [
        len(_slide_image_numbers(output_dir, subdir))
        for subdir in ("images", "pt", "en")
    ]
    return max(counts, default=0)


def _slide_image_numbers_for_project(
    project: CarouselProject,
    subdir: str,
) -> list[int]:
    if subdir in {"pt", "en"}:
        language_dir = resolve_language_dir(project, subdir)
        if language_dir is None:
            return []
        return _numbers_from_slide_dir(language_dir)
    images_dir = resolve_shared_images_dir(project)
    if images_dir is None:
        return []
    return _numbers_from_slide_dir(images_dir)


def _preview_rendered_slide_urls(
    project_id: UUID,
    slide_numbers: list[int],
    lang: str,
) -> list[str]:
    """Authenticated preview URLs for draft carousels (publish workspace)."""
    project_id_str = str(project_id)
    return [
        f"/api/carousels/{project_id_str}/preview/images/slide_{i}.jpg?lang={lang}"
        for i in slide_numbers
    ]


def _public_rendered_slide_urls(
    project_id: UUID,
    slide_numbers: Sequence[int],
    lang: str,
) -> list[str]:
    project_id_str = str(project_id)
    return [
        f"/api/carousels/{project_id_str}/slide-images/{lang}/slide_{i}.jpg"
        for i in slide_numbers
    ]


@dataclass(frozen=True)
class _PreviewSlideNumbers:
    """Slide numbers for PT and fallback raw preview."""

    pt: list[int]
    raw: list[int]
    project_id: UUID


def _apply_preview_pt_urls(
    images: dict[str, object],
    numbers: _PreviewSlideNumbers,
) -> dict[str, object]:
    """Set rendered-slide URLs for PT (or fallback raw) into image dict."""
    if numbers.pt:
        preview_pt = _preview_rendered_slide_urls(numbers.project_id, numbers.pt, "pt")
        images["rendered_slides_pt"] = preview_pt
        if preview_pt:
            images["hero"] = preview_pt[0]
            images["slides"] = preview_pt
    elif numbers.raw:
        preview_pt = _preview_rendered_slide_urls(
            numbers.project_id,
            numbers.raw,
            "pt",
        )
        images["rendered_slides_pt"] = preview_pt
        images["hero"] = preview_pt[0] if preview_pt else ""
        images["slides"] = preview_pt
    else:
        images.pop("rendered_slides_pt", None)
        images["hero"] = ""
        images["slides"] = []
    return images


def _apply_draft_preview_urls(
    project: CarouselProject,
    tokens: dict[str, object],
) -> dict[str, object]:
    """Use owner-scoped preview routes until the carousel is published publicly."""
    if project.is_public or not project.output_dir:
        return tokens
    raw_numbers = _slide_image_numbers_for_project(project, "images")
    pt_numbers = _slide_image_numbers_for_project(project, "pt")
    en_numbers = _slide_image_numbers_for_project(project, "en")
    if not raw_numbers and not pt_numbers and not en_numbers:
        return tokens
    raw_images = tokens.get("images")
    if not isinstance(raw_images, dict):
        return tokens
    images = dict(raw_images)

    images = _apply_preview_pt_urls(
        images,
        _PreviewSlideNumbers(pt=pt_numbers, raw=raw_numbers, project_id=project.id),
    )

    if en_numbers:
        images["rendered_slides_en"] = _preview_rendered_slide_urls(
            project.id,
            en_numbers,
            "en",
        )
    else:
        images.pop("rendered_slides_en", None)
    return {**tokens, "images": images}


def merge_design_tokens_with_disk(
    project: CarouselProject,
) -> dict[str, object]:
    """Refresh slide image paths from disk so publish/download include all slides."""
    defaults = _build_default_design_tokens(project)
    raw_tokens = project.design_tokens
    if not raw_tokens or not isinstance(raw_tokens, dict):
        return _apply_draft_preview_urls(project, defaults)

    raw_images = dict(raw_tokens.get("images", {}))
    default_images = defaults["images"]
    merged_images: dict[str, object] = {**default_images, **raw_images}
    for key in ("slides", "rendered_slides_pt", "rendered_slides_en"):
        default_list = default_images.get(key)
        raw_list = raw_images.get(key)
        if isinstance(default_list, list):
            if key == "slides":
                merged_images[key] = default_list
            elif isinstance(raw_list, list) and len(raw_list) > len(default_list):
                merged_images[key] = raw_list
            else:
                merged_images[key] = default_list
        elif key == "rendered_slides_en":
            merged_images.pop("rendered_slides_en", None)

    if project.output_dir and not _has_rendered_slides(project, "en"):
        merged_images.pop("rendered_slides_en", None)

    merged = {
        **defaults,
        **raw_tokens,
        "images": merged_images,
        "layout": {
            **dict(defaults.get("layout", {})),
            **dict(raw_tokens.get("layout", {})),
            "progress_segments": defaults["layout"]["progress_segments"],
        },
    }
    return _apply_draft_preview_urls(project, merged)


def _has_rendered_slides(project: CarouselProject, lang: str) -> bool:
    language_dir = resolve_language_dir(project, lang)
    if language_dir is None:
        return False
    return len(_numbers_from_slide_dir(language_dir)) > 0


def _resolve_palette(theme: str, topic: str) -> dict[str, str]:
    palette = CAROUSEL_THEMES.get(theme)
    if palette is None:
        topic_lower = topic.lower()
        for brand, keywords in BRAND_KEYWORDS.items():
            if any(kw in topic_lower for kw in keywords):
                palette = BRAND_PALETTES.get(brand)
                break
    if palette is None:
        palette = {
            "primary": "#3b82f6",
            "accent": "#f59e0b",
            "background": "#0a0e17",
        }
    return palette


def _resolve_slide_info(
    project: CarouselProject,
) -> tuple[int, list[str], list[int], list[int]]:
    pt_slide_numbers = _slide_image_numbers_for_project(project, "pt")
    en_slide_numbers = _slide_image_numbers_for_project(project, "en")
    slide_count = max(
        len(pt_slide_numbers),
        len(en_slide_numbers),
    )
    if slide_count == 0:
        slide_count = slide_count_from_config(project.slides_config)
    slide_paths = _public_rendered_slide_urls(project.id, pt_slide_numbers, "pt")
    return slide_count, slide_paths, pt_slide_numbers, en_slide_numbers


def _build_default_design_tokens(
    project: CarouselProject,
) -> dict[str, object]:
    palette = _resolve_palette(project.theme.value, project.topic)
    slide_count, slide_paths, pt_slide_numbers, en_slide_numbers = _resolve_slide_info(
        project,
    )
    hero_path = slide_paths[0] if slide_paths else ""

    colors = {
        "primary": palette["primary"],
        "accent": palette["accent"],
        "bg": palette.get("background", "#0a0e17"),
        "text": "#e2e8f0",
        "text_muted": "#94a3b8",
        "text_dim": "#64748b",
        "border": "#1e293b",
        "glow": palette["accent"],
    }
    typography = {
        "font_family_heading": "Inter, system-ui, sans-serif",
        "font_family_body": "Inter, system-ui, sans-serif",
        "font_family_badge": "JetBrains Mono, monospace",
    }
    images: dict[str, object] = {
        "hero": hero_path,
        "slides": slide_paths,
    }
    if pt_slide_numbers:
        images["rendered_slides_pt"] = slide_paths
    if en_slide_numbers:
        images["rendered_slides_en"] = _public_rendered_slide_urls(
            project.id,
            en_slide_numbers,
            "en",
        )
    badge = project.niche.strip() if project.niche else "CARROSSEL"
    layout = {
        "badge_label": badge,
        "swipe_text": SWIPE_TEXT_EN,
        "progress_segments": slide_count,
    }

    return {
        "colors": colors,
        "typography": typography,
        "images": images,
        "layout": layout,
    }
