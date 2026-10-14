"""The Instagram Story image announcing a carousel post (AE-0369).

Pure Pillow, no database. The PT slide 1 is centred on a blurred, darkened
copy of itself with a short caption band above it, as a 1080x1920 JPEG of at
most 8 MB. The file lives in the serving root (the active artifact version, or
the output dir) and is rendered again only when slide 1 is newer.
"""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

from rag_backend.domain.constants import (
    HD_SUBDIR_NAME,
    LANGUAGE_PT,
    SLIDE_FILENAME_PREFIX,
    SLIDE_IMAGE_EXTENSION,
)
from rag_backend.domain.constants.artifact_build import ARTIFACT_VERSIONS_DIR
from rag_backend.modules.publishing.constants import (
    ERR_STORY_IMAGE_TOO_LARGE,
    STORY_ARROW_GAP,
    STORY_ARROW_HEAD_HEIGHT,
    STORY_ARROW_HEIGHT,
    STORY_ARROW_SHAFT_WIDTH,
    STORY_ARROW_WIDTH,
    STORY_BACKGROUND_DARKEN,
    STORY_BAND_ALPHA,
    STORY_BAND_COLOR,
    STORY_BAND_HEIGHT,
    STORY_BLUR_RADIUS,
    STORY_CAPTION_ANCHOR,
    STORY_CAPTION_CENTER_Y,
    STORY_CAPTION_COLOR,
    STORY_CAPTION_FONT_SIZE,
    STORY_CAPTION_TEXT,
    STORY_HEIGHT,
    STORY_IMAGE_FILENAME,
    STORY_IMAGE_MODE,
    STORY_IMAGE_URL,
    STORY_JPEG_FORMAT,
    STORY_JPEG_QUALITIES,
    STORY_MAX_BYTES,
    STORY_SLIDE_NUMBER,
    STORY_SLIDE_TOP,
    STORY_TEMP_SUFFIX,
    STORY_WIDTH,
)


@dataclass(frozen=True, kw_only=True)
class StoryPaths:
    """Where slide 1 is (None when it was never rendered) and where the Story goes."""

    slide: Path | None
    story: Path


def story_paths(
    output_dir: str | None, artifact_version: str | None
) -> StoryPaths | None:
    """Slide 1 and Story paths in the serving root, or None without an output dir."""
    root = _serving_root(output_dir, artifact_version)
    if root is None:
        return None
    return StoryPaths(
        slide=_slide_one(root / LANGUAGE_PT),
        story=root / STORY_IMAGE_FILENAME,
    )


def story_image_file(
    output_dir: str | None, artifact_version: str | None
) -> Path | None:
    """The rendered Story JPEG, or None when it does not exist."""
    paths = story_paths(output_dir, artifact_version)
    if paths is None or not paths.story.is_file():
        return None
    return paths.story


def build_public_story_image_url(base_url: str, project_id: str) -> str:
    """Absolute URL Meta's fetcher GETs for the Story image."""
    return STORY_IMAGE_URL.format(base=base_url.rstrip("/"), project_id=project_id)


def render_story_image(paths: StoryPaths) -> bool:
    """Write the Story JPEG unless it is newer than slide 1. False without slide 1."""
    if paths.slide is None:
        return False
    if _is_current(paths.slide, paths.story):
        return True
    _write_atomic(paths.story, story_jpeg(paths.slide))
    return True


def story_jpeg(slide: Path) -> bytes:
    """The 1080x1920 Story JPEG for one slide image. Deterministic."""
    with Image.open(slide) as raw:
        source = raw.convert(STORY_IMAGE_MODE)
    canvas = _background(source)
    front = _fit(source)
    canvas.paste(front, ((STORY_WIDTH - front.width) // 2, STORY_SLIDE_TOP))
    _caption(canvas)
    return _encode(canvas)


def _serving_root(output_dir: str | None, artifact_version: str | None) -> Path | None:
    if not output_dir:
        return None
    root = Path(output_dir).resolve()
    if artifact_version:
        version_root = root / ARTIFACT_VERSIONS_DIR / artifact_version
        if version_root.is_dir():
            return version_root
    return root


def _slide_one(language_dir: Path) -> Path | None:
    name = f"{SLIDE_FILENAME_PREFIX}{STORY_SLIDE_NUMBER}{SLIDE_IMAGE_EXTENSION}"
    for directory in (language_dir, language_dir / HD_SUBDIR_NAME):
        candidate = directory / name
        if candidate.is_file():
            return candidate
    return None


def _is_current(slide: Path, story: Path) -> bool:
    if not story.is_file():
        return False
    return story.stat().st_mtime >= slide.stat().st_mtime


def _background(source: Image.Image) -> Image.Image:
    """Cover the canvas with slide 1, then blur and darken it."""
    scale = max(STORY_WIDTH / source.width, STORY_HEIGHT / source.height)
    size = (round(source.width * scale), round(source.height * scale))
    cover = source.resize(size, Image.Resampling.LANCZOS)
    left = (cover.width - STORY_WIDTH) // 2
    top = (cover.height - STORY_HEIGHT) // 2
    cropped = cover.crop((left, top, left + STORY_WIDTH, top + STORY_HEIGHT))
    blurred = cropped.filter(ImageFilter.GaussianBlur(STORY_BLUR_RADIUS))
    return ImageEnhance.Brightness(blurred).enhance(STORY_BACKGROUND_DARKEN)


def _fit(source: Image.Image) -> Image.Image:
    """Slide 1 at full width, or smaller when it would run off the canvas."""
    room = STORY_HEIGHT - STORY_SLIDE_TOP
    scale = min(STORY_WIDTH / source.width, room / source.height)
    size = (round(source.width * scale), round(source.height * scale))
    return source.resize(size, Image.Resampling.LANCZOS)


def _caption(canvas: Image.Image) -> None:
    top = STORY_CAPTION_CENTER_Y - STORY_BAND_HEIGHT // 2
    box = (0, top, STORY_WIDTH, top + STORY_BAND_HEIGHT)
    band = Image.new(
        STORY_IMAGE_MODE, (STORY_WIDTH, STORY_BAND_HEIGHT), STORY_BAND_COLOR
    )
    canvas.paste(Image.blend(canvas.crop(box), band, STORY_BAND_ALPHA), box)
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default(size=STORY_CAPTION_FONT_SIZE)
    text_width = round(draw.textlength(STORY_CAPTION_TEXT, font=font))
    left = (STORY_WIDTH - text_width - STORY_ARROW_GAP - STORY_ARROW_WIDTH) // 2
    draw.text(
        (left, STORY_CAPTION_CENTER_Y),
        STORY_CAPTION_TEXT,
        fill=STORY_CAPTION_COLOR,
        font=font,
        anchor=STORY_CAPTION_ANCHOR,
    )
    _arrow(draw, left + text_width + STORY_ARROW_GAP)


def _arrow(draw: ImageDraw.ImageDraw, left: int) -> None:
    """An upward arrow: a triangle head over a shaft."""
    top = STORY_CAPTION_CENTER_Y - STORY_ARROW_HEIGHT // 2
    bottom = top + STORY_ARROW_HEIGHT
    middle = left + STORY_ARROW_WIDTH // 2
    neck = top + STORY_ARROW_HEAD_HEIGHT
    head = [(middle, top), (left + STORY_ARROW_WIDTH, neck), (left, neck)]
    draw.polygon(head, fill=STORY_CAPTION_COLOR)
    half = STORY_ARROW_SHAFT_WIDTH // 2
    shaft = (middle - half, neck, middle + half, bottom)
    draw.rectangle(shaft, fill=STORY_CAPTION_COLOR)


def _encode(canvas: Image.Image) -> bytes:
    for quality in STORY_JPEG_QUALITIES:
        buffer = BytesIO()
        canvas.save(buffer, format=STORY_JPEG_FORMAT, quality=quality)
        data = buffer.getvalue()
        if len(data) <= STORY_MAX_BYTES:
            return data
    raise ValueError(ERR_STORY_IMAGE_TOO_LARGE)


def _write_atomic(target: Path, data: bytes) -> None:
    temp = target.with_name(f"{target.name}{STORY_TEMP_SUFFIX}")
    temp.write_bytes(data)
    Path(temp).replace(target)
