"""OpenAI image generation service (gpt-image-2).

Wraps `openai.images.generate` behind the `ImageGenerationService`
protocol so the carousel pipeline can swap between Gemini and OpenAI
without touching the agent. The SDK call is sync; we push it to a
thread via `asyncio.to_thread` to keep the agent async-clean.

Error translation happens here so the agent doesn't need to know vendor
error shapes — missing API key and 403 organization-verification errors
are converted into `RuntimeError`s with actionable messages that end up
in the project's `error_message` field and the Gherkin contract.
"""

from __future__ import annotations

import asyncio
import base64
from pathlib import Path

from openai import APIError, APIStatusError, OpenAI

from rag_backend.domain.protocols import ImageGenerationService

_DEFAULT_MODEL = "gpt-image-2"
# Widest 2:3-ish size OpenAI offers; matches the 3.5:1 hero-img CSS
# frame in the carousel template better than the square variants.
_DEFAULT_SIZE = "1536x1024"

_MSG_MISSING_KEY = (
    "OPENAI_API_KEY is not set — add it to the backend .env before "
    "selecting an OpenAI image preset."
)
_MSG_NOT_VERIFIED = (
    "OpenAI returned 403 — the organization likely needs identity "
    "verification at platform.openai.com/settings/organization/general "
    "before gpt-image-2 is available."
)

HTTP_STATUS_FORBIDDEN = 403

_ERR_GENERATION_FAILED = "OpenAI image generation failed: {}"
_ERR_NO_RESPONSE_DATA = "OpenAI image response contained no data"
_ERR_MISSING_B64_JSON = "OpenAI image response missing b64_json payload"


class OpenAIImageService(ImageGenerationService):
    """OpenAI Images 2.0 (`gpt-image-2`) implementation."""

    def __init__(
        self,
        api_key: str,
        model: str = _DEFAULT_MODEL,
        size: str = _DEFAULT_SIZE,
    ) -> None:
        # Client is built lazily so a user who never touches an OpenAI
        # preset doesn't need OPENAI_API_KEY set — the failure surfaces
        # only when an OpenAI-backed image is actually requested.
        self._api_key = api_key
        self._model = model
        self._size = size
        self._client: OpenAI | None = None

    def _get_client(self) -> OpenAI:
        if self._client is not None:
            return self._client
        if not self._api_key:
            raise RuntimeError(_MSG_MISSING_KEY)
        self._client = OpenAI(api_key=self._api_key)
        return self._client

    async def generate_image(
        self,
        prompt: str,
        output_path: str,
    ) -> str:
        return await asyncio.to_thread(self._generate_sync, prompt, output_path)

    def _generate_sync(self, prompt: str, output_path: str) -> str:
        client = self._get_client()
        try:
            # SDK types `size` as a strict Literal; we validate it via
            # settings but mypy can't narrow a runtime string to a literal.
            resp = client.images.generate(  # type: ignore[call-overload]
                model=self._model,
                prompt=prompt,
                size=self._size,
                n=1,
            )
        except APIStatusError as exc:
            if exc.status_code == HTTP_STATUS_FORBIDDEN:
                raise RuntimeError(_MSG_NOT_VERIFIED) from exc
            raise RuntimeError(_ERR_GENERATION_FAILED.format(exc)) from exc
        except APIError as exc:
            raise RuntimeError(_ERR_GENERATION_FAILED.format(exc)) from exc

        data = getattr(resp, "data", None)
        if not data:
            raise RuntimeError(_ERR_NO_RESPONSE_DATA)

        entry = data[0]
        b64 = getattr(entry, "b64_json", None)
        if not b64:
            raise RuntimeError(_ERR_MISSING_B64_JSON)

        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(base64.b64decode(b64))
        return output_path
