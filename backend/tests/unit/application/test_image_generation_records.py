"""Unit tests for image generation record persistence helpers.

Feature: Image generation idempotency

  Scenario: Reuse existing successful generation
    Given a slide has a succeeded generation record
    And the output file exists and is valid
    When image generation runs with the same generation key
    Then OpenAI is not called
    And the slide image_path is reused

  Scenario: Provider call fails — persist structured error
    Given a provider call fails
    When the generation record is created
    Then error_json contains a message

  Scenario: Recovery creates record without inventing provider IDs
    Given a slide has an image_path on disk
    And no generation record exists
    When the recovery is recorded
    Then provider_image_id remains null

  Scenario: Content SHA is computed from output file
    Given a valid image file
    When a generation record is created with an image path
    Then content_sha256 is populated
"""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest

from rag_backend.application.services.carousel.image_generation_records import (
    GENERATION_STATUS_FAILED,
    GENERATION_STATUS_RECOVERED,
    GENERATION_STATUS_REUSED,
    GENERATION_STATUS_SUCCEEDED,
    ImageGenerationRecordInput,
    _generation_record,
    _record_content_sha,
    file_sha256,
)
from rag_backend.application.services.carousel.image_prompt_package import (
    ImagePromptPackage,
)
from rag_backend.domain.models import (
    CarouselProject,
    CarouselSlide,
)


def _make_project(**overrides: object) -> CarouselProject:
    defaults: dict[str, object] = {
        "topic": "test",
        "audience": "test",
        "niche": "test",
    }
    defaults.update(overrides)
    return CarouselProject(**defaults)


def _make_slide(slide_number: int = 1, project_id: uuid4 | None = None) -> CarouselSlide:
    pid = project_id or uuid4()
    return CarouselSlide(
        project_id=pid,
        slide_number=slide_number,
        slide_type="content",
        heading="test",
        body="test",
    )


def _make_prompt(**overrides: object) -> ImagePromptPackage:
    defaults: dict[str, object] = {
        "raw_prompt": "a scenic landscape",
        "rendered_prompt": "A beautiful scenic landscape with mountains",
        "prompt_hash": "abc123hash",
        "generation_key": "key456gen",
        "provider": "openai",
        "model": "gpt-image-2",
        "style": "cinematic",
        "theme_name": "dark",
        "theme_colors": {"primary": "#000000"},
    }
    defaults.update(overrides)
    return ImagePromptPackage(**defaults)


@pytest.mark.unit
class TestFileSha256:
    def test_computes_hash_of_file_content(self, tmp_path: Path) -> None:
        file_path = tmp_path / "test.jpg"
        file_path.write_bytes(b"hello world")
        result = file_sha256(str(file_path))
        assert isinstance(result, str)
        assert len(result) == 64

    def test_different_content_different_hash(self, tmp_path: Path) -> None:
        file_a = tmp_path / "a.jpg"
        file_b = tmp_path / "b.jpg"
        file_a.write_bytes(b"content a")
        file_b.write_bytes(b"content b")
        assert file_sha256(str(file_a)) != file_sha256(str(file_b))

    def test_missing_file_returns_sentinel(self) -> None:
        result = file_sha256("/nonexistent/path/to/image.jpg")
        assert result == "<file-not-found>"


@pytest.mark.unit
class TestRecordContentSha:
    def test_returns_none_for_none_path(self) -> None:
        result = _record_content_sha(None)
        assert result is None

    def test_returns_none_for_nonexistent_file(self) -> None:
        result = _record_content_sha("/nonexistent/path.jpg")
        assert result is None

    def test_returns_hash_for_existing_file(self, tmp_path: Path) -> None:
        file_path = tmp_path / "test.jpg"
        file_path.write_bytes(b"test content")
        result = _record_content_sha(str(file_path))
        assert result is not None
        assert len(result) == 64


@pytest.mark.unit
class TestGenerationRecord:
    def test_succeeded_record_has_all_fields(self) -> None:
        project = _make_project()
        slide = _make_slide(project_id=project.id)
        prompt = _make_prompt()
        input_data = ImageGenerationRecordInput(
            project=project,
            slide=slide,
            prompt=prompt,
            status=GENERATION_STATUS_SUCCEEDED,
            image_path="/tmp/out/slide_1.jpg",
        )
        record = _generation_record(input_data)
        assert record.project_id == project.id
        assert record.slide_id == slide.id
        assert record.slide_number == 1
        assert record.generation_key == "key456gen"
        assert record.status == GENERATION_STATUS_SUCCEEDED
        assert record.prompt_hash == "abc123hash"
        assert record.provider == "openai"
        assert record.model == "gpt-image-2"
        assert record.style == "cinematic"
        assert record.raw_prompt == "a scenic landscape"
        assert record.rendered_prompt == "A beautiful scenic landscape with mountains"
        assert record.error_json is None

    def test_failed_record_includes_error_message(self) -> None:
        project = _make_project()
        slide = _make_slide(project_id=project.id)
        prompt = _make_prompt()
        input_data = ImageGenerationRecordInput(
            project=project,
            slide=slide,
            prompt=prompt,
            status=GENERATION_STATUS_FAILED,
            error_message="OpenAI image generation failed",
        )
        record = _generation_record(input_data)
        assert record.status == GENERATION_STATUS_FAILED
        assert record.error_json is not None
        assert record.error_json.get("message") == "OpenAI image generation failed"

    def test_failed_record_includes_structured_error_details(self) -> None:
        project = _make_project()
        slide = _make_slide(project_id=project.id)
        prompt = _make_prompt()
        input_data = ImageGenerationRecordInput(
            project=project,
            slide=slide,
            prompt=prompt,
            status=GENERATION_STATUS_FAILED,
            error_message="model not found",
            error_details={"status": 400, "type": "invalid_request_error", "code": "model_not_found"},
        )
        record = _generation_record(input_data)
        assert record.error_json is not None
        assert record.error_json.get("message") == "model not found"
        assert record.error_json.get("status") == 400
        assert record.error_json.get("code") == "model_not_found"

    def test_no_error_json_when_no_error(self) -> None:
        project = _make_project()
        slide = _make_slide(project_id=project.id)
        prompt = _make_prompt()
        input_data = ImageGenerationRecordInput(
            project=project,
            slide=slide,
            prompt=prompt,
            status=GENERATION_STATUS_SUCCEEDED,
        )
        record = _generation_record(input_data)
        assert record.error_json is None

    def test_content_sha_populated_when_file_exists(self, tmp_path: Path) -> None:
        file_path = tmp_path / "slide_1.jpg"
        file_path.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 100)
        project = _make_project()
        slide = _make_slide(project_id=project.id)
        prompt = _make_prompt()
        input_data = ImageGenerationRecordInput(
            project=project,
            slide=slide,
            prompt=prompt,
            status=GENERATION_STATUS_SUCCEEDED,
            image_path=str(file_path),
        )
        record = _generation_record(input_data)
        assert record.content_sha256 is not None
        assert len(record.content_sha256) == 64

    def test_content_sha_none_when_no_path(self) -> None:
        project = _make_project()
        slide = _make_slide(project_id=project.id)
        prompt = _make_prompt()
        input_data = ImageGenerationRecordInput(
            project=project,
            slide=slide,
            prompt=prompt,
            status=GENERATION_STATUS_FAILED,
        )
        record = _generation_record(input_data)
        assert record.content_sha256 is None

    def test_recovered_status_record(self) -> None:
        project = _make_project()
        slide = _make_slide(project_id=project.id)
        prompt = _make_prompt()
        input_data = ImageGenerationRecordInput(
            project=project,
            slide=slide,
            prompt=prompt,
            status=GENERATION_STATUS_RECOVERED,
            image_path="/tmp/out/slide_1.jpg",
        )
        record = _generation_record(input_data)
        assert record.status == GENERATION_STATUS_RECOVERED
        assert record.provider_image_id is None

    def test_reused_status_record(self) -> None:
        project = _make_project()
        slide = _make_slide(project_id=project.id)
        prompt = _make_prompt()
        input_data = ImageGenerationRecordInput(
            project=project,
            slide=slide,
            prompt=prompt,
            status=GENERATION_STATUS_REUSED,
            image_path="/tmp/out/slide_1.jpg",
        )
        record = _generation_record(input_data)
        assert record.status == GENERATION_STATUS_REUSED
