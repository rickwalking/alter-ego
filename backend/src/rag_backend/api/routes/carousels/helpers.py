from pathlib import Path
from uuid import UUID

from fastapi import HTTPException

from rag_backend.api.constants import (
    CAROUSEL_CACHE_HEADERS,
    ERR_CAROUSEL_NOT_FOUND,
    ERR_CAROUSEL_NOT_GENERATED,
)
from rag_backend.domain.constants import BRAND_KEYWORDS, BRAND_PALETTES, CAROUSEL_THEMES
from rag_backend.domain.models import CarouselProject
from rag_backend.domain.protocols import CarouselRepository

_ERR_MISSING_PUBLIC_BASE_URL = (
    "CAROUSEL_PUBLIC_BASE_URL is not set — Instagram cannot "
    "fetch images from localhost. Configure a public HTTPS base "
    "URL in the backend .env."
)


_JPEG_CACHE_HEADERS = CAROUSEL_CACHE_HEADERS


def _pdf_path_for_language(project: CarouselProject, lang: str) -> str | None:
    if lang == "en":
        return project.pdf_path_en or project.pdf_path
    return project.pdf_path


def _extract_first_paragraph(markdown: str) -> str | None:
    lines = markdown.strip().split("\n")
    paragraphs: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        if stripped:
            paragraphs.append(stripped)
        elif paragraphs:
            break
    if not paragraphs:
        return None
    return " ".join(paragraphs)[:200]


def _extract_title_and_subtitle(markdown: str) -> tuple[str | None, str | None]:
    lines = markdown.strip().split("\n")
    if not lines:
        return None, None

    first_line = lines[0]
    if not first_line.startswith("# "):
        return None, None

    heading = first_line[2:].strip()

    title_subtitle_separator = ":"
    if title_subtitle_separator in heading:
        separator_pos = heading.index(title_subtitle_separator)
        title = heading[:separator_pos].strip()
        subtitle = heading[separator_pos + 1 :].strip()
        return title, subtitle

    return heading, None


def _count_slide_images(output_dir: str | None) -> int:
    if not output_dir:
        return 0
    images_dir = Path(output_dir) / "images"
    if images_dir.is_dir():
        count = len(list(images_dir.glob("slide_*.jpg")))
        if count > 0:
            return count
    pt_dir = Path(output_dir) / "pt"
    if pt_dir.is_dir():
        count = len(list(pt_dir.glob("slide_*.jpg")))
        if count > 0:
            return count
    en_dir = Path(output_dir) / "en"
    if en_dir.is_dir():
        count = len(list(en_dir.glob("slide_*.jpg")))
        if count > 0:
            return count
    return 0


def _has_rendered_slides(output_dir: str, lang: str) -> bool:
    lang_dir = Path(output_dir) / lang
    return lang_dir.is_dir() and len(list(lang_dir.glob("slide_*.jpg"))) > 0


def _build_default_design_tokens(
    project: CarouselProject,
) -> dict[str, object]:
    theme_value = project.theme.value
    palette = CAROUSEL_THEMES.get(theme_value)
    if palette is None:
        topic_lower = project.topic.lower()
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

    slide_count = _count_slide_images(project.output_dir)
    if slide_count == 0:
        slide_count = 4

    project_id_str = str(project.id)
    slide_paths = [
        f"/api/carousels/{project_id_str}/images/slide_{i}.jpg" for i in range(1, slide_count + 1)
    ]
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
    output_dir = project.output_dir
    if output_dir and _has_rendered_slides(output_dir, "pt"):
        images["rendered_slides_pt"] = [
            f"/api/carousels/{project_id_str}/slide-images/pt/slide_{i}.jpg"
            for i in range(1, slide_count + 1)
        ]
    if output_dir and _has_rendered_slides(output_dir, "en"):
        images["rendered_slides_en"] = [
            f"/api/carousels/{project_id_str}/slide-images/en/slide_{i}.jpg"
            for i in range(1, slide_count + 1)
        ]
    badge = project.niche.strip() if project.niche else "CARROSSEL"
    layout = {
        "badge_label": badge,
        "swipe_text": "Deslize \u2192",
        "progress_segments": slide_count,
    }

    return {
        "colors": colors,
        "typography": typography,
        "images": images,
        "layout": layout,
    }


def _resolve_image_file(directory: Path, filename: str) -> Path | None:
    candidate = directory / filename
    if candidate.is_file():
        return candidate
    with_ext = Path(f"{candidate}.jpg")
    return with_ext if with_ext.is_file() else None


async def _load_project_with_output(project_id: UUID, repo: CarouselRepository) -> CarouselProject:
    project = await repo.get_project_by_id(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail=ERR_CAROUSEL_NOT_FOUND)
    if project.output_dir is None:
        raise HTTPException(status_code=404, detail=ERR_CAROUSEL_NOT_GENERATED)
    return project


def _build_public_image_urls(project_id: UUID, slides_count: int = 4) -> list[str]:
    from rag_backend.infrastructure.config.settings import get_settings

    base = get_settings().carousel_public_base_url.rstrip("/")
    if not base:
        raise RuntimeError(_ERR_MISSING_PUBLIC_BASE_URL)
    return [
        f"{base}/api/carousels/{project_id}/images/slide_{i}.jpg"
        for i in range(1, slides_count + 1)
    ]
