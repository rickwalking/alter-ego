"""Rendered image prompt packages for carousel slide generation."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from hashlib import sha256

from rag_backend.application.services.carousel.theme_resolver import resolve_theme
from rag_backend.application.services.carousel.types import SlideData
from rag_backend.application.services.image_prompt_sanitizer import (
    sanitize_image_prompt,
)
from rag_backend.application.services.image_style_strategies import (
    GeminiComicNeonStrategy,
    OpenAICinematicStrategy,
    OpenAIFlatEditorialStrategy,
    OpenAIHyperrealStrategy,
    OpenAINeoAnimeStrategy,
)
from rag_backend.domain.constants import (
    IMAGE_MODEL_GEMINI,
    IMAGE_MODEL_OPENAI,
    IMAGE_STYLE_CINEMATIC,
    IMAGE_STYLE_COMIC_NEON,
    IMAGE_STYLE_FLAT_EDITORIAL,
    IMAGE_STYLE_HYPERREAL,
    IMAGE_STYLE_NEO_ANIME,
)
from rag_backend.domain.models import CarouselProject
from rag_backend.domain.protocols import ImageStyleStrategy

HASH_SEPARATOR = b"\0"
METADATA_CONTENT_SHA = "image_content_sha256"
METADATA_GENERATION_KEY = "image_generation_key"
METADATA_MODEL = "image_generation_model"
METADATA_PROMPT_SHA = "image_prompt_sha256"
METADATA_PROVIDER = "image_generation_provider"
METADATA_RAW_PROMPT = "raw_image_prompt"
METADATA_RENDERED_PROMPT = "rendered_image_prompt"
METADATA_STYLE = "image_generation_style"


@dataclass(frozen=True)
class ImagePromptPackageRequest:
    project: CarouselProject
    slide: SlideData
    theme: Mapping[str, str] | None = None


@dataclass(frozen=True)
class ImagePromptPackage:
    raw_prompt: str
    rendered_prompt: str
    prompt_hash: str
    generation_key: str
    provider: str
    model: str
    style: str
    theme_name: str
    theme_colors: dict[str, str]


def render_image_prompt_package(
    request: ImagePromptPackageRequest,
) -> ImagePromptPackage:
    raw_prompt = request.slide.image_prompt or ""
    if request.project.image_model == IMAGE_MODEL_OPENAI:
        raw_prompt = sanitize_image_prompt(raw_prompt)
    theme = request.theme or resolve_theme(request.project)
    rendered_prompt = _strategy_for_project(request.project).wrap(raw_prompt, theme)
    generation_key = sha256_parts((
        request.project.image_model,
        request.project.image_style,
        rendered_prompt,
    ))
    prompt_hash = sha256_parts((rendered_prompt,))
    return ImagePromptPackage(
        raw_prompt=raw_prompt,
        rendered_prompt=rendered_prompt,
        prompt_hash=prompt_hash,
        generation_key=generation_key,
        provider=request.project.image_model,
        model=request.project.image_model,
        style=request.project.image_style,
        theme_name=request.project.theme.value,
        theme_colors=dict(theme),
    )


def sha256_parts(parts: Sequence[str]) -> str:
    digest = sha256()
    for part in parts:
        digest.update(part.encode("utf-8"))
        digest.update(HASH_SEPARATOR)
    return digest.hexdigest()


_STRATEGY_MAP: dict[tuple[str, str], type[ImageStyleStrategy]] = {
    (IMAGE_MODEL_GEMINI, IMAGE_STYLE_COMIC_NEON): GeminiComicNeonStrategy,
    (IMAGE_MODEL_OPENAI, IMAGE_STYLE_CINEMATIC): OpenAICinematicStrategy,
    (IMAGE_MODEL_OPENAI, IMAGE_STYLE_HYPERREAL): OpenAIHyperrealStrategy,
    (IMAGE_MODEL_OPENAI, IMAGE_STYLE_NEO_ANIME): OpenAINeoAnimeStrategy,
    (IMAGE_MODEL_OPENAI, IMAGE_STYLE_FLAT_EDITORIAL): OpenAIFlatEditorialStrategy,
}

_DEFAULT_STRATEGY = GeminiComicNeonStrategy


def _strategy_for_project(project: CarouselProject) -> ImageStyleStrategy:
    strategy_cls = _STRATEGY_MAP.get(
        (project.image_model, project.image_style), _DEFAULT_STRATEGY
    )
    return strategy_cls()
