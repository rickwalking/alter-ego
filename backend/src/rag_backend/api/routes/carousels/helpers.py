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
    resolve_pdf_path,
)
from rag_backend.domain.constants import LANGUAGE_PT
from rag_backend.domain.models import CarouselProject
from rag_backend.domain.protocols import CarouselRepository

_SAFE_IMAGE_FILENAME = re.compile(r"^[a-zA-Z0-9_\-\.]+$")

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
