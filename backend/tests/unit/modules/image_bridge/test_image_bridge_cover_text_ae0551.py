"""The image bridge's text-only path for a cover without photos.

Feature: Generate a slide-1 cover from a text prompt alone
(tests/features/cover_generation_text_ae0551.feature). A cover job with no
photo sends exactly the text-only body of contract section 2.1.
"""

from __future__ import annotations

import io
from uuid import UUID

from PIL import Image

from rag_backend.domain.models.cover_generation import CoverEditJob
from rag_backend.modules.image_bridge import IMAGE_BRIDGE_MODEL
from rag_backend.modules.image_bridge.application.grokbot_image_service import (
    GrokBotImageConfig,
    GrokBotImageDeps,
    GrokBotImageService,
)
from rag_backend.modules.image_bridge.domain.models import JobSuccess
from rag_backend.modules.image_bridge.infrastructure.pillow_codec import (
    PillowImageCodec,
)
from tests.unit.modules.image_bridge.support import (
    FakeClock,
    FakeWebhook,
    png_bytes,
    sqlite_repository,
)

_JOB_ID = UUID("0c5d1d4e-1f6a-4a8e-9a51-2d8f0c7b3e10")
_TEXT_KEYS = [
    "job_id",
    "model",
    "prompt",
    "size",
    "n",
    "response_format",
    "callback_url",
    "callback_token",
    "expires_at",
    "metadata",
]


async def test_cover_job_without_photos_sends_the_text_body() -> None:
    """Scenario: A text-only job sends exactly the text body."""
    webhook, clock = FakeWebhook(), FakeClock()
    async with sqlite_repository() as repo:

        async def answer() -> None:
            request = webhook.requests[0]
            image = png_bytes((1024, 1536), "PNG")
            await repo.succeed(JobSuccess(request.job_id, image, clock.now()))

        clock.on_sleep = answer
        deps = GrokBotImageDeps(
            repository=repo, webhook=webhook, codec=PillowImageCodec(), clock=clock
        )
        service = GrokBotImageService(
            deps, GrokBotImageConfig(callback_base_url="https://marinssolutions.com")
        )
        image = await service.edit_image(
            CoverEditJob(
                job_id=_JOB_ID, prompt="cena: café", photo_count=0, project_id="p-1"
            )
        )

    body = webhook.requests[0].payload()
    assert list(body) == _TEXT_KEYS
    assert "operation" not in body
    assert "image" not in body
    assert body["job_id"] == str(_JOB_ID)
    assert body["prompt"] == "cena: café"
    assert body["model"] == IMAGE_BRIDGE_MODEL
    assert body["size"] == "1024x1536"
    assert body["metadata"] == {"content_type": "carousel_cover", "project_id": "p-1"}
    with Image.open(io.BytesIO(image)) as cover:
        assert cover.format == "PNG"
        assert cover.size == (1080, 1350)
