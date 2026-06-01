"""Unit tests for preview_carousel_image HD fallback and filename validation.

Gherkin: tests/features/carousel_image_refinement.feature
"""

from __future__ import annotations

from contextlib import ExitStack
from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from rag_backend.api.routes.carousels.preview import preview_carousel_image
from rag_backend.domain.models import CarouselProject, User
from rag_backend.domain.models.user import UserRole


def _mock_request() -> Request:
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/api/carousels/test/preview/images/slide_1.jpg",
        "headers": [],
        "query_string": b"",
        "server": ("test", 80),
        "client": ("127.0.0.1", 12345),
    }
    return Request(scope)


@pytest.mark.unit
class TestPreviewCarouselImageFallback:
    """HD → standard → hero fallback chain."""

    async def _call_endpoint(
        self,
        tmp_path: Path,
        filename: str = "slide_1.jpg",
        lang: str = "pt",
        patched_resolve: list[Path | None] | None = None,
        mock_resolve_image_file: bool = True,
    ) -> object:
        project = CarouselProject(
            topic="T",
            audience="A",
            niche="N",
            output_dir=str(tmp_path),
        )
        user = User(
            id=uuid4(),
            email="t@example.com",
            full_name="Test",
            role=UserRole.EDITOR,
            hashed_password="hash",
        )
        request = _mock_request()
        repo = MagicMock()
        db = MagicMock()

        with ExitStack() as stack:
            stack.enter_context(
                patch(
                    "rag_backend.api.routes.carousels.preview._load_project_with_output",
                    return_value=project,
                )
            )
            stack.enter_context(
                patch(
                    "rag_backend.api.routes.carousels.preview._assigned_reviewer_id",
                    return_value=None,
                )
            )
            stack.enter_context(
                patch(
                    "rag_backend.api.routes.carousels.preview.assert_carousel_project_access",
                )
            )
            mock_resolve = None
            if mock_resolve_image_file:
                mock_resolve = stack.enter_context(
                    patch(
                        "rag_backend.api.routes.carousels.preview._resolve_image_file",
                        side_effect=patched_resolve or [None, None, None],
                    )
                )

            response = await preview_carousel_image(
                request=request,
                project_id=project.id,
                filename=filename,
                user=user,
                repo=repo,
                db=db,
                lang=lang,
            )
            return response, mock_resolve

    # Scenario: HD image is served when available
    async def test_serves_hd_when_present(self, tmp_path: Path) -> None:
        hd_file = tmp_path / "pt" / "hd" / "slide_1.jpg"
        hd_file.parent.mkdir(parents=True, exist_ok=True)
        hd_file.write_text("hd-content")

        response, mock_resolve = await self._call_endpoint(
            tmp_path,
            patched_resolve=[hd_file, None, None],
        )

        assert mock_resolve.call_count == 1
        assert mock_resolve.call_args_list[0][0][0] == tmp_path / "pt" / "hd"
        assert response.path == str(hd_file)

    # Scenario: Standard image is served when HD is missing
    async def test_falls_back_to_standard_when_hd_missing(self, tmp_path: Path) -> None:
        std_file = tmp_path / "pt" / "slide_1.jpg"
        std_file.parent.mkdir(parents=True, exist_ok=True)
        std_file.write_text("std-content")

        response, mock_resolve = await self._call_endpoint(
            tmp_path,
            patched_resolve=[None, std_file, None],
        )

        assert mock_resolve.call_count == 2
        assert mock_resolve.call_args_list[0][0][0] == tmp_path / "pt" / "hd"
        assert mock_resolve.call_args_list[1][0][0] == tmp_path / "pt"
        assert response.path == str(std_file)

    # Scenario: Hero image is served when both HD and standard are missing
    async def test_falls_back_to_hero_when_both_missing(self, tmp_path: Path) -> None:
        hero_file = tmp_path / "images" / "slide_1.jpg"
        hero_file.parent.mkdir(parents=True, exist_ok=True)
        hero_file.write_text("hero-content")

        response, mock_resolve = await self._call_endpoint(
            tmp_path,
            patched_resolve=[None, None, hero_file],
        )

        assert mock_resolve.call_count == 3
        assert mock_resolve.call_args_list[2][0][0] == tmp_path / "images"
        assert response.path == str(hero_file)

    # Scenario: Returns 404 when no image exists in any tier
    async def test_raises_404_when_no_image_found(self, tmp_path: Path) -> None:
        with pytest.raises(HTTPException) as exc_info:
            _, _ = await self._call_endpoint(
                tmp_path,
                patched_resolve=[None, None, None],
            )
        assert exc_info.value.status_code == 404

    # Scenario: Rejects path-traversal filename patterns
    async def test_rejects_path_traversal_filename(self, tmp_path: Path) -> None:
        # When calling the handler directly FastPath validation is bypassed,
        # but _resolve_image_file internally sanitizes the filename and
        # raises HTTPException(404) before any file access occurs.
        with pytest.raises(HTTPException) as exc_info:
            _, _ = await self._call_endpoint(
                tmp_path,
                filename="../../../etc/passwd",
                mock_resolve_image_file=False,
            )
        assert exc_info.value.status_code == 404

    # Scenario: Accepts safe filenames with hyphens, underscores, and dots
    async def test_accepts_safe_filename(self, tmp_path: Path) -> None:
        safe_file = tmp_path / "pt" / "hd" / "slide_1-2.jpg"
        safe_file.parent.mkdir(parents=True, exist_ok=True)
        safe_file.write_text("safe")

        response, _ = await self._call_endpoint(
            tmp_path,
            filename="slide_1-2.jpg",
            patched_resolve=[safe_file, None, None],
        )
        assert response.path == str(safe_file)
