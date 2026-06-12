"""Unit tests for shared image validation utility.

Feature: JPEG validation for carousel pipeline

  Scenario: Valid JPEG passes validation
    Given a file is a valid JPEG with size >= min_bytes
    When is_valid_jpeg checks it
    Then it returns True

  Scenario: Too-small file fails validation
    Given a file smaller than min_bytes
    When is_valid_jpeg checks it
    Then it returns False

  Scenario: Non-JPEG format fails validation
    Given a PNG file with sufficient size
    When is_valid_jpeg checks it
    Then it returns False

  Scenario: Nonexistent file fails validation
    Given a path that does not exist
    When is_valid_jpeg checks it
    Then it returns False

  Scenario: Corrupted data fails validation
    Given a file with random bytes
    When is_valid_jpeg checks it
    Then it returns False

  Scenario: Custom min_bytes threshold is respected
    Given a JPEG file of 500 bytes
    When is_valid_jpeg checks it with min_bytes=100
    Then it returns True
    When is_valid_jpeg checks it with min_bytes=2048
    Then it returns False
"""

from __future__ import annotations

from pathlib import Path

import pytest

from rag_backend.application.services.carousel.image_validation import (
    is_valid_jpeg,
)


@pytest.mark.unit
class TestIsValidJpeg:
    def test_valid_jpeg_passes(self, tmp_path: Path) -> None:
        from PIL import Image as PILImage

        file_path = tmp_path / "slide_1.jpg"
        PILImage.new("RGB", (1080, 1350)).save(file_path, format="JPEG")
        assert is_valid_jpeg(file_path) is True

    def test_tiny_file_fails(self, tmp_path: Path) -> None:
        tiny_file = tmp_path / "tiny.jpg"
        tiny_file.write_bytes(b"not a jpeg")
        assert is_valid_jpeg(tiny_file) is False

    def test_png_fails_format_check(self, tmp_path: Path) -> None:
        from PIL import Image as PILImage

        png_path = tmp_path / "slide.png"
        PILImage.new("RGB", (1080, 1350)).save(png_path, format="PNG")
        assert is_valid_jpeg(png_path) is False

    def test_nonexistent_file_fails(self, tmp_path: Path) -> None:
        missing = tmp_path / "missing.jpg"
        assert is_valid_jpeg(missing) is False

    def test_corrupted_data_fails(self, tmp_path: Path) -> None:
        corrupt = tmp_path / "corrupt.jpg"
        corrupt.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 2000)
        assert is_valid_jpeg(corrupt) is False

    def test_custom_min_bytes_threshold(self, tmp_path: Path) -> None:
        from PIL import Image as PILImage

        small_jpeg = tmp_path / "small.jpg"
        PILImage.new("RGB", (10, 10)).save(small_jpeg, format="JPEG", quality=1)
        assert is_valid_jpeg(small_jpeg, min_bytes=1) is True
        assert is_valid_jpeg(small_jpeg, min_bytes=2048) is False

    def test_exact_min_bytes_boundary(self, tmp_path: Path) -> None:
        from PIL import Image as PILImage

        file_path = tmp_path / "boundary.jpg"
        PILImage.new("RGB", (100, 100)).save(file_path, format="JPEG", quality=95)
        file_size = file_path.stat().st_size
        assert is_valid_jpeg(file_path, min_bytes=file_size) is True
        assert is_valid_jpeg(file_path, min_bytes=file_size + 1) is False

    def test_empty_directory_path_fails(self, tmp_path: Path) -> None:
        dir_path = tmp_path / "subdir.jpg"
        dir_path.mkdir()
        assert is_valid_jpeg(dir_path) is False
