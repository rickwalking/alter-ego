"""Persistence helpers for carousel image generation attempts."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

from rag_backend.application.services.carousel.image_prompt_package import (
    ImagePromptPackage,
)
from rag_backend.application.services.carousel.image_validation import (
    is_valid_jpeg,
)
from rag_backend.domain.models import (
    CarouselImageGeneration,
    CarouselProject,
    CarouselSlide,
)
from rag_backend.domain.protocols import CarouselRepository
from rag_backend.infrastructure.logging import get_logger

logger = get_logger()

GENERATION_STATUS_FAILED = "failed"
GENERATION_STATUS_RECOVERED = "recovered"
GENERATION_STATUS_REUSED = "reused"
GENERATION_STATUS_SUCCEEDED = "succeeded"


@dataclass(frozen=True)
class ImageGenerationRecordInput:
    project: CarouselProject
    slide: CarouselSlide
    prompt: ImagePromptPackage
    status: str
    image_path: str | None = None
    error_message: str | None = None
    error_details: dict[str, object] | None = None


async def reuse_recorded_generation(
    repo: CarouselRepository,
    prompt: ImagePromptPackage,
) -> str | None:
    if not hasattr(repo, "get_image_generation_by_key"):
        logger.warning(
            "Repository %s does not support get_image_generation_by_key",
            type(repo).__name__,
        )
        return None
    try:
        record = await repo.get_image_generation_by_key(prompt.generation_key)
    except NotImplementedError:
        return None
    if (
        not isinstance(record, CarouselImageGeneration)
        or record.status
        not in {
            GENERATION_STATUS_RECOVERED,
            GENERATION_STATUS_REUSED,
            GENERATION_STATUS_SUCCEEDED,
        }
        or not record.output_path
    ):
        return None
    path = Path(record.output_path)
    return str(path) if (path.is_file() and is_valid_jpeg(path)) else None


async def upsert_generation_record(
    repo: CarouselRepository,
    record_input: ImageGenerationRecordInput,
) -> None:
    try:
        await repo.upsert_image_generation(_generation_record(record_input))
    except (AttributeError, NotImplementedError):
        return
    except Exception as exc:
        logger.warning(
            "carousel_image_generation_record_failed",
            project_id=str(record_input.project.id),
            slide_number=record_input.slide.slide_number,
            generation_key=record_input.prompt.generation_key,
            error=str(exc),
            exc_info=True,
        )


_FILE_NOT_FOUND_SHA256 = "<file-not-found>"


def file_sha256(image_path: str) -> str:
    try:
        return sha256(Path(image_path).read_bytes()).hexdigest()
    except FileNotFoundError:
        logger.warning("image file not found for sha256", image_path=image_path)
        return _FILE_NOT_FOUND_SHA256


def _generation_record(
    record_input: ImageGenerationRecordInput,
) -> CarouselImageGeneration:
    error_json: dict[str, object] | None = None
    if record_input.error_message:
        details = record_input.error_details or {}
        error_json = {"message": record_input.error_message, **details}
    return CarouselImageGeneration(
        project_id=record_input.project.id,
        slide_id=record_input.slide.id,
        slide_number=record_input.slide.slide_number,
        generation_key=record_input.prompt.generation_key,
        status=record_input.status,
        output_path=record_input.image_path,
        prompt_hash=record_input.prompt.prompt_hash,
        provider=record_input.prompt.provider,
        model=record_input.prompt.model,
        style=record_input.prompt.style,
        raw_prompt=record_input.prompt.raw_prompt,
        rendered_prompt=record_input.prompt.rendered_prompt,
        content_sha256=_record_content_sha(record_input.image_path),
        error_json=error_json,
    )


def _record_content_sha(image_path: str | None) -> str | None:
    if not image_path:
        return None
    path = Path(image_path)
    if not path.is_file():
        return None
    return file_sha256(image_path)
