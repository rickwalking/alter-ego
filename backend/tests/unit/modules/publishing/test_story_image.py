"""Story image render (AE-0369).

Gherkin: tests/features/autopilot_story_and_music.feature
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from PIL import Image

import rag_backend.infrastructure.database.models  # noqa: F401  (import order)
from rag_backend.modules.publishing.application import story_image
from rag_backend.modules.publishing.application.story_image import (
    StoryPaths,
    render_story_image,
    story_image_file,
    story_jpeg,
    story_paths,
)
from rag_backend.modules.publishing.constants import (
    ERR_STORY_IMAGE_TOO_LARGE,
    STORY_CAPTION_PT,
    STORY_HEIGHT,
    STORY_IMAGE_FILENAME,
    STORY_MAX_BYTES,
    STORY_SLIDE_TOP,
    STORY_WIDTH,
)
from rag_backend.modules.publishing.public import build_public_story_image_url

_SLIDE_COLOR = (200, 40, 90)
_SLIDE_SIZE = (1080, 1350)


def _slide(directory: Path, size: tuple[int, int] = _SLIDE_SIZE) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "slide_1.jpg"
    Image.new("RGB", size, _SLIDE_COLOR).save(path, format="JPEG")
    return path


def _output(tmp_path: Path) -> Path:
    _slide(tmp_path / "pt")
    return tmp_path


@pytest.mark.unit
class TestStoryImageRender:
    """Scenario: The Story image is a 1080x1920 JPEG under 8 MB."""

    def test_story_is_a_1080x1920_jpeg_under_8_mb(self, tmp_path: Path) -> None:
        paths = story_paths(str(_output(tmp_path)), None)
        assert paths is not None

        assert render_story_image(paths) is True

        assert paths.story == tmp_path / STORY_IMAGE_FILENAME
        with Image.open(paths.story) as story:
            assert story.size == (STORY_WIDTH, STORY_HEIGHT)
            assert story.format == "JPEG"
        assert paths.story.stat().st_size <= STORY_MAX_BYTES

    def test_slide_one_sits_in_the_middle_over_a_darker_background(
        self, tmp_path: Path
    ) -> None:
        paths = story_paths(str(_output(tmp_path)), None)
        assert paths is not None
        render_story_image(paths)

        with Image.open(paths.story) as story:
            rgb = story.convert("RGB")
            centre = rgb.getpixel((STORY_WIDTH // 2, STORY_SLIDE_TOP + 600))
            background = rgb.getpixel((STORY_WIDTH // 2, STORY_HEIGHT - 20))
        assert isinstance(centre, tuple)
        assert isinstance(background, tuple)
        assert abs(centre[0] - _SLIDE_COLOR[0]) < 12
        # The blurred copy is darkened, so it is clearly dimmer than slide 1.
        assert background[0] < centre[0] * 0.7

    def test_caption_reads_novo_post_no_perfil(self) -> None:
        assert STORY_CAPTION_PT == "Novo post no perfil ↑"

    def test_render_is_deterministic(self, tmp_path: Path) -> None:
        slide = _slide(tmp_path / "pt")
        assert story_jpeg(slide) == story_jpeg(slide)

    def test_a_tall_slide_is_scaled_down_to_fit(self, tmp_path: Path) -> None:
        slide = _slide(tmp_path / "pt", size=(1080, 1920))
        data = story_jpeg(slide)
        target = tmp_path / "story.jpg"
        target.write_bytes(data)
        with Image.open(target) as story:
            assert story.size == (STORY_WIDTH, STORY_HEIGHT)

    def test_too_large_output_raises(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        slide = _slide(tmp_path / "pt")
        monkeypatch.setattr(story_image, "STORY_MAX_BYTES", 10)
        with pytest.raises(ValueError, match=ERR_STORY_IMAGE_TOO_LARGE):
            story_jpeg(slide)


@pytest.mark.unit
class TestStoryImageCache:
    """Scenario: Rendering is deterministic and cached."""

    def test_unchanged_slide_reuses_the_file(self, tmp_path: Path) -> None:
        paths = story_paths(str(_output(tmp_path)), None)
        assert paths is not None
        render_story_image(paths)
        paths.story.write_bytes(b"cached")
        future = paths.story.stat().st_mtime + 10
        os.utime(paths.story, (future, future))

        assert render_story_image(paths) is True

        assert paths.story.read_bytes() == b"cached"

    def test_newer_slide_renders_again(self, tmp_path: Path) -> None:
        paths = story_paths(str(_output(tmp_path)), None)
        assert paths is not None and paths.slide is not None
        render_story_image(paths)
        paths.story.write_bytes(b"stale")
        past = paths.slide.stat().st_mtime - 10
        os.utime(paths.story, (past, past))

        render_story_image(paths)

        assert paths.story.read_bytes() != b"stale"


@pytest.mark.unit
class TestStoryPaths:
    """Scenario: No slide 1 means no Story image."""

    def test_no_slide_one_renders_nothing(self, tmp_path: Path) -> None:
        paths = story_paths(str(tmp_path), None)
        assert paths is not None
        assert paths.slide is None
        assert render_story_image(paths) is False
        assert not paths.story.exists()

    def test_no_output_dir_has_no_paths(self) -> None:
        assert story_paths(None, None) is None
        assert story_image_file(None, None) is None

    def test_hd_slide_is_used_when_standard_is_missing(self, tmp_path: Path) -> None:
        hd = _slide(tmp_path / "pt" / "hd", size=(2160, 2700))
        paths = story_paths(str(tmp_path), None)
        assert paths == StoryPaths(slide=hd, story=tmp_path / STORY_IMAGE_FILENAME)

    def test_active_artifact_version_is_the_serving_root(self, tmp_path: Path) -> None:
        version = tmp_path / "versions" / "v2"
        _slide(version / "pt")
        paths = story_paths(str(tmp_path), "v2")
        assert paths is not None
        assert paths.story == version / STORY_IMAGE_FILENAME

    def test_missing_version_dir_falls_back_to_the_output_dir(
        self, tmp_path: Path
    ) -> None:
        paths = story_paths(str(_output(tmp_path)), "gone")
        assert paths is not None
        assert paths.story == tmp_path / STORY_IMAGE_FILENAME

    def test_story_image_file_only_once_rendered(self, tmp_path: Path) -> None:
        output = str(_output(tmp_path))
        assert story_image_file(output, None) is None
        paths = story_paths(output, None)
        assert paths is not None
        render_story_image(paths)
        assert story_image_file(output, None) == paths.story

    def test_public_url(self) -> None:
        url = build_public_story_image_url("https://api.test/", "p-1")
        assert url == "https://api.test/api/carousels/p-1/story-image/pt.jpg"
