import re
from collections.abc import Sequence
from pathlib import Path
from uuid import UUID

from fastapi import HTTPException

from rag_backend.api.constants import (
    CAROUSEL_CACHE_HEADERS,
    CAROUSEL_PREVIEW_CACHE_HEADERS,
    ERR_CAROUSEL_NOT_FOUND,
    ERR_CAROUSEL_NOT_GENERATED,
    ERR_IMAGE_NOT_FOUND,
    ERR_INSTAGRAM_PUBLIC_BASE_URL_NOT_CONFIGURED,
)
from rag_backend.api.routes.carousels.carousel_access import (  # noqa: F401 — re-exported for backward compatibility
    assert_carousel_artifacts_healthy,
    assert_carousel_project_access,
    assert_carousel_public,
    assert_carousel_public_or_editor,
)
from rag_backend.application.services.carousel.artifact_path_resolver import (
    resolve_language_dir,
    resolve_pdf_path,
    resolve_shared_images_dir,
)
from rag_backend.application.services.carousel.types import slide_count_from_config
from rag_backend.domain.constants import (
    BRAND_KEYWORDS,
    BRAND_PALETTES,
    CAROUSEL_THEMES,
    LANGUAGE_PT,
    SWIPE_TEXT_EN,
)
from rag_backend.domain.models import CarouselProject
from rag_backend.domain.protocols import CarouselRepository

_SAFE_IMAGE_FILENAME = re.compile(r"^[a-zA-Z0-9_\-\.]+$")
_SLIDE_IMAGE_FILENAME = re.compile(r"^slide_(\d+)\.jpg$")

_JPEG_CACHE_HEADERS = CAROUSEL_CACHE_HEADERS
_PREVIEW_JPEG_CACHE_HEADERS = CAROUSEL_PREVIEW_CACHE_HEADERS


def _pdf_path_for_language(project: CarouselProject, lang: str) -> str | None:
    if lang == "en":
        return project.pdf_path_en or project.pdf_path
    return project.pdf_path


def _resolve_pdf_file(project: CarouselProject, lang: str) -> Path | None:
    """Resolve PDF path confined to the active artifact serving root."""
    versioned = resolve_pdf_path(project, lang)
    if versioned is not None:
        return versioned
    raw_path = _pdf_path_for_language(project, lang)
    if not raw_path or not project.output_dir:
        return None
    output_dir = Path(project.output_dir).resolve()
    if not output_dir.is_dir():
        return None
    candidate = Path(raw_path).resolve()
    if not candidate.is_relative_to(output_dir):
        return None
    if not candidate.is_file():
        return None
    return candidate


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


def _count_slide_images(output_dir: str | None) -> int:
    counts = [
        len(_slide_image_numbers(output_dir, subdir))
        for subdir in ("images", "pt", "en")
    ]
    return max(counts, default=0)


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

    if pt_numbers:
        preview_pt = _preview_rendered_slide_urls(
            project.id,
            pt_numbers,
            "pt",
        )
        images["rendered_slides_pt"] = preview_pt
        if preview_pt:
            images["hero"] = preview_pt[0]
            images["slides"] = preview_pt
    else:
        images.pop("rendered_slides_pt", None)
        images["hero"] = ""
        images["slides"] = []

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

    pt_slide_numbers = _slide_image_numbers_for_project(project, "pt")
    en_slide_numbers = _slide_image_numbers_for_project(project, "en")
    slide_count = max(
        len(pt_slide_numbers),
        len(en_slide_numbers),
    )
    if slide_count == 0:
        slide_count = slide_count_from_config(project.slides_config)

    slide_paths = _public_rendered_slide_urls(project.id, pt_slide_numbers, "pt")
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


def _sanitize_image_filename(filename: str) -> str:
    """Reject path traversal and unsafe characters in image filenames."""
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=404, detail=ERR_IMAGE_NOT_FOUND)
    basename = Path(filename).name
    if not basename or basename in {".", ".."}:
        raise HTTPException(status_code=404, detail=ERR_IMAGE_NOT_FOUND)
    if not _SAFE_IMAGE_FILENAME.match(basename):
        raise HTTPException(status_code=404, detail=ERR_IMAGE_NOT_FOUND)
    return basename


def _resolve_image_file(directory: Path, filename: str) -> Path | None:
    safe_name = _sanitize_image_filename(filename)
    base_dir = directory.resolve()
    candidate = (base_dir / safe_name).resolve()
    if not candidate.is_relative_to(base_dir):
        return None
    if candidate.is_file():
        return candidate
    with_ext = candidate.with_suffix(".jpg")
    if with_ext.is_file() and with_ext.is_relative_to(base_dir):
        return with_ext
    return None


def _safe_relative_file_path(path: Path, base: Path) -> str | None:
    """Return a relative path when the file is confined to base."""
    try:
        resolved = path.resolve()
        if not resolved.is_file():
            return None
        if not resolved.is_relative_to(base):
            return None
        return str(resolved.relative_to(base))
    except (OSError, ValueError):
        return None


async def _load_project_with_output(
    project_id: UUID, repo: CarouselRepository
) -> CarouselProject:
    project = await repo.get_project_by_id(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail=ERR_CAROUSEL_NOT_FOUND)
    if project.output_dir is None:
        raise HTTPException(status_code=404, detail=ERR_CAROUSEL_NOT_GENERATED)
    return project


def _build_public_image_urls(
    project_id: UUID,
    slide_numbers: Sequence[int] | int | None = None,
    lang: str = LANGUAGE_PT,
) -> list[str]:
    from rag_backend.infrastructure.config.settings import get_settings

    base = get_settings().carousel_public_base_url.rstrip("/")
    if not base:
        raise RuntimeError(ERR_INSTAGRAM_PUBLIC_BASE_URL_NOT_CONFIGURED)
    if slide_numbers is None:
        slide_numbers = range(1, 5)
    if isinstance(slide_numbers, int):
        slide_numbers = range(1, slide_numbers + 1)
    return [
        f"{base}/api/carousels/{project_id}/slide-images/{lang}/slide_{i}.jpg"
        for i in slide_numbers
    ]
