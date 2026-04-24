"""Google Gemini image generation service."""

import asyncio
import time
from pathlib import Path

from google import genai
from google.genai import types

from rag_backend.domain.protocols import ImageGenerationService

_ERR_NO_IMAGE_DATA = "No image data in Gemini response"


class GeminiImageService(ImageGenerationService):
    """Google Gemini image generation implementation."""

    def __init__(self, api_key: str) -> None:
        self._client = genai.Client(api_key=api_key)

    def _generate_image_blocking(
        self,
        prompt: str,
        output_path: str,
    ) -> str:
        """Synchronous image generation; runs in a thread pool.

        ``generate_content`` is a blocking HTTP call. Wrapping it in
        ``asyncio.to_thread`` keeps the event loop free so the FastAPI
        server can continue serving ``/status`` polls while images are
        being generated.
        """
        response = self._client.models.generate_content(
            model="gemini-3.1-flash-image-preview",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE", "TEXT"],
            ),
        )

        for part in response.candidates[0].content.parts:
            if part.inline_data:
                output_dir = Path(output_path).parent
                output_dir.mkdir(parents=True, exist_ok=True)
                with open(output_path, "wb") as f:
                    f.write(part.inline_data.data)
                return output_path

        raise RuntimeError(_ERR_NO_IMAGE_DATA)

    async def generate_image(
        self,
        prompt: str,
        output_path: str,
    ) -> str:
        """Generate an image from a text prompt and save to output_path.

        Returns the path to the saved image file.
        """
        return await asyncio.to_thread(self._generate_image_blocking, prompt, output_path)

    def generate_image_sync(
        self,
        prompt: str,
        output_path: str,
        delay_seconds: float = 2.0,
    ) -> str:
        """Generate an image synchronously with rate-limit delay.

        Returns the path to the saved image file.
        """
        result = self._generate_image_blocking(prompt, output_path)
        time.sleep(delay_seconds)
        return result
