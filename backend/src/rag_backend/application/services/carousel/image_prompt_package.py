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
    IMAGE_STRATEGY_REGISTRY,
    OpenAIComicNeonStrategy,
)
from rag_backend.domain.constants import IMAGE_MODEL_OPENAI
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
    raw_prompt = _compose_scene(raw_prompt, request.project.custom_visual_details)
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
        theme_name=request.project.theme,
        theme_colors=dict(theme),
    )


_VISUAL_DIRECTION_PREFIX = "Visual direction:"


def _compose_scene(scene: str, custom_visual_details: str | None) -> str:
    """Fold project-level custom visual direction into the slide scene.

    The details ride inside the scene (the ``Scene:`` trailer the strategy
    appends), so they reach the model AND change the rendered prompt hash —
    which busts the per-prompt image reuse so a revision actually regenerates
    (AE-0261). Empty details leave the scene byte-identical (AE-0263).
    """
    details = (custom_visual_details or "").strip()
    if not details:
        return scene
    base = scene.strip()
    direction = f"{_VISUAL_DIRECTION_PREFIX} {details}"
    return f"{base}. {direction}" if base else direction


def sha256_parts(parts: Sequence[str]) -> str:
    digest = sha256()
    for part in parts:
        digest.update(part.encode("utf-8"))
        digest.update(HASH_SEPARATOR)
    return digest.hexdigest()


# Dark default for any combo the registry doesn't cover (defence in depth;
# API validation rejects unsupported combos before they reach here).
_DEFAULT_STRATEGY = OpenAIComicNeonStrategy


def _strategy_for_project(project: CarouselProject) -> ImageStyleStrategy:
    strategy_cls = IMAGE_STRATEGY_REGISTRY.get(
        (project.image_model, project.image_style), _DEFAULT_STRATEGY
    )
    return strategy_cls()
