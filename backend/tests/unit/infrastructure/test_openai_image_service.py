"""Unit tests for OpenAIImageService.

Gherkin: tests/features/image_generation_provider.feature
"""

from __future__ import annotations

import base64
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from openai import APIStatusError

from rag_backend.infrastructure.external.openai_image import OpenAIImageService


def _fake_response(b64: str = base64.b64encode(b"pixel-data").decode()) -> MagicMock:
    entry = MagicMock()
    entry.b64_json = b64
    resp = MagicMock()
    resp.data = [entry]
    return resp


def _fake_status_error(status_code: int) -> APIStatusError:
    mock_response = MagicMock()
    mock_response.status_code = status_code
    return APIStatusError(
        message=f"HTTP {status_code}",
        response=mock_response,
        body={"error": {"message": "boom"}},
    )


@pytest.mark.unit
class TestOpenAIImageServiceHappyPath:
    """Happy-path image generation with a mocked SDK."""

    async def test_writes_decoded_bytes(self, tmp_path: Path) -> None:
        service = OpenAIImageService(api_key="sk-test")
        fake_client = MagicMock()
        fake_client.images.generate.return_value = _fake_response()
        service._client = fake_client

        out = tmp_path / "slide_1.jpg"
        result = await service.generate_image("prompt", str(out))

        assert result == str(out)
        assert out.read_bytes() == b"pixel-data"

    async def test_uses_configured_model_and_size(self, tmp_path: Path) -> None:
        service = OpenAIImageService(
            api_key="sk-test", model="gpt-image-2", size="1024x1024"
        )
        fake_client = MagicMock()
        fake_client.images.generate.return_value = _fake_response()
        service._client = fake_client

        await service.generate_image("prompt", str(tmp_path / "a.jpg"))

        fake_client.images.generate.assert_called_once_with(
            model="gpt-image-2",
            prompt="prompt",
            size="1024x1024",
            n=1,
        )


@pytest.mark.unit
class TestOpenAIImageServiceFailureModes:
    """Scenario: Missing OPENAI_API_KEY / 403 verification error."""

    async def test_missing_api_key_surfaces_actionable_message(
        self, tmp_path: Path
    ) -> None:
        service = OpenAIImageService(api_key="")
        with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
            await service.generate_image("prompt", str(tmp_path / "x.jpg"))

    async def test_403_translated_to_verification_hint(self, tmp_path: Path) -> None:
        service = OpenAIImageService(api_key="sk-test")
        fake_client = MagicMock()
        fake_client.images.generate.side_effect = _fake_status_error(403)
        service._client = fake_client

        with pytest.raises(RuntimeError, match="verification"):
            await service.generate_image("prompt", str(tmp_path / "x.jpg"))

    async def test_non_403_status_error_still_surfaces(self, tmp_path: Path) -> None:
        service = OpenAIImageService(api_key="sk-test")
        fake_client = MagicMock()
        fake_client.images.generate.side_effect = _fake_status_error(500)
        service._client = fake_client

        with pytest.raises(RuntimeError, match="OpenAI image generation failed"):
            await service.generate_image("prompt", str(tmp_path / "x.jpg"))

    async def test_empty_data_raises(self, tmp_path: Path) -> None:
        service = OpenAIImageService(api_key="sk-test")
        fake_client = MagicMock()
        fake_resp = MagicMock()
        fake_resp.data = []
        fake_client.images.generate.return_value = fake_resp
        service._client = fake_client

        with pytest.raises(RuntimeError, match="no data"):
            await service.generate_image("prompt", str(tmp_path / "x.jpg"))

    async def test_missing_b64_raises(self, tmp_path: Path) -> None:
        service = OpenAIImageService(api_key="sk-test")
        fake_client = MagicMock()
        entry = MagicMock()
        entry.b64_json = None
        fake_resp = MagicMock()
        fake_resp.data = [entry]
        fake_client.images.generate.return_value = fake_resp
        service._client = fake_client

        with pytest.raises(RuntimeError, match="b64_json"):
            await service.generate_image("prompt", str(tmp_path / "x.jpg"))
