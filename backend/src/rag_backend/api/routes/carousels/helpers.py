import re
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
from rag_backend.api.dependencies.resource_access import assert_domain_owner_or_admin
from rag_backend.domain.constants import BRAND_KEYWORDS, BRAND_PALETTES, CAROUSEL_THEMES
from rag_backend.domain.constants.access_control import ERR_CAROUSEL_NOT_PUBLIC
from rag_backend.domain.models import CarouselProject, User
from rag_backend.domain.protocols import CarouselRepository

_SAFE_IMAGE_FILENAME = re.compile(r"^[a-zA-Z0-9_\-\.]+$")

_JPEG_CACHE_HEADERS = CAROUSEL_CACHE_HEADERS
_PREVIEW_JPEG_CACHE_HEADERS = CAROUSEL_PREVIEW_CACHE_HEADERS


def _pdf_path_for_language(project: CarouselProject, lang: str) -> str | None:
    if lang == "en":
        return project.pdf_path_en or project.pdf_path
    return project.pdf_path


def _resolve_pdf_file(project: CarouselProject, lang: str) -> Path | None:
    """Resolve PDF path confined to the project output directory."""
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


def _count_slide_images(output_dir: str | None) -> int:
    if not output_dir:
        return 0
    base = Path(output_dir)
    counts: list[int] = []
    for subdir in ("images", "pt", "en"):
        slide_dir = base / subdir
        if slide_dir.is_dir():
            counts.append(len(list(slide_dir.glob("slide_*.jpg"))))
    return max(counts) if counts else 0


def _preview_rendered_slide_urls(
    project_id: UUID,
    slide_count: int,
    lang: str,
) -> list[str]:
    """Authenticated preview URLs for draft carousels (publish workspace)."""
    project_id_str = str(project_id)
    return [
        f"/api/carousels/{project_id_str}/preview/images/slide_{i}.jpg?lang={lang}"
        for i in range(1, slide_count + 1)
    ]


def _apply_draft_preview_urls(
    project: CarouselProject,
    tokens: dict[str, object],
) -> dict[str, object]:
    """Use owner-scoped preview routes until the carousel is published publicly."""
    if project.is_public or not project.output_dir:
        return tokens
    slide_count = _count_slide_images(project.output_dir)
    if slide_count == 0:
        return tokens
    raw_images = tokens.get("images")
    if not isinstance(raw_images, dict):
        return tokens
    images = dict(raw_images)
    if _has_rendered_slides(project.output_dir, "pt"):
        preview_pt = _preview_rendered_slide_urls(
            project.id,
            slide_count,
            "pt",
        )
        images["rendered_slides_pt"] = preview_pt
        if preview_pt:
            images["hero"] = preview_pt[0]
            hero_slot_count = min(4, len(preview_pt))
            images["slides"] = preview_pt[:hero_slot_count]
    if _has_rendered_slides(project.output_dir, "en"):
        images["rendered_slides_en"] = _preview_rendered_slide_urls(
            project.id,
            slide_count,
            "en",
        )
    else:
        images.pop("rendered_slides_en", None)
    return {**tokens, "images": images}


def _merge_design_tokens_with_disk(
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
            if isinstance(raw_list, list) and len(raw_list) > len(default_list):
                merged_images[key] = raw_list
            else:
                merged_images[key] = default_list
        elif key == "rendered_slides_en":
            merged_images.pop("rendered_slides_en", None)

    if project.output_dir and not _has_rendered_slides(project.output_dir, "en"):
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
        f"/api/carousels/{project_id_str}/images/slide_{i}.jpg"
        for i in range(1, slide_count + 1)
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


def assert_carousel_public(project: CarouselProject) -> None:
    """Allow only published carousels on public media routes."""
    if project.is_public:
        return
    raise HTTPException(status_code=404, detail=ERR_CAROUSEL_NOT_PUBLIC)


def assert_carousel_project_access(
    project: CarouselProject,
    user: User,
    *,
    assigned_reviewer_id: str | None = None,
) -> None:
    """Allow project owners, admins, and assigned reviewers on preview routes."""
    if user.is_admin():
        return
    if assigned_reviewer_id and str(user.id) == assigned_reviewer_id:
        return
    assert_domain_owner_or_admin(project.owner_id, user)


def assert_carousel_public_or_editor(
    project: CarouselProject,
    user: User | None,
) -> None:
    """Deprecated: public routes must use assert_carousel_public only."""
    _ = user
    assert_carousel_public(project)


def _build_public_image_urls(project_id: UUID, slides_count: int = 4) -> list[str]:
    from rag_backend.infrastructure.config.settings import get_settings

    base = get_settings().carousel_public_base_url.rstrip("/")
    if not base:
        raise RuntimeError(ERR_INSTAGRAM_PUBLIC_BASE_URL_NOT_CONFIGURED)
    return [
        f"{base}/api/carousels/{project_id}/images/slide_{i}.jpg"
        for i in range(1, slides_count + 1)
    ]
