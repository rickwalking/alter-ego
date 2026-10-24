"""The image bridge's image-edit path for a cover from the owner's photos.

Feature: Generate a slide-1 cover from library photos with Grok
(tests/features/cover_generation_ae0508.feature). The same webhook endpoint
and callback as the text path; reference photos ride inside the body.
"""

from __future__ import annotations

import base64
import io
from uuid import UUID

import pytest
from PIL import Image
from pydantic import SecretStr

from rag_backend.domain.models.cover_generation import CoverEditJob, ReferencePhoto
from rag_backend.infrastructure.config.settings import Settings
from rag_backend.modules.image_bridge import (
    IMAGE_BRIDGE_MODEL,
    ImageBridgeConfigError,
    build_grokbot_cover_editor,
)
from rag_backend.modules.image_bridge.application.grokbot_image_service import (
    GrokBotImageConfig,
    GrokBotImageDeps,
    GrokBotImageService,
)
from rag_backend.modules.image_bridge.domain.exceptions import (
    InvalidCallbackImageError,
)
from rag_backend.modules.image_bridge.domain.models import (
    JobSuccess,
    WebhookRequest,
    data_url,
)
from rag_backend.modules.image_bridge.domain.ports import NormalizeRequest
from rag_backend.modules.image_bridge.infrastructure.pillow_codec import (
    PillowImageCodec,
)
from rag_backend.modules.image_bridge.infrastructure.repository import (
    SqlImageBridgeJobRepository,
)
from tests.unit.modules.image_bridge.support import (
    T0,
    FakeClock,
    FakeWebhook,
    png_bytes,
    sqlite_repository,
)

_PHOTO = b"\x89PNG-reference-photo-bytes"
_BASE_URL = "https://marinssolutions.com"


class _BrokenCodec(PillowImageCodec):
    @staticmethod
    def normalize(request: NormalizeRequest) -> bytes:
        del request
        raise InvalidCallbackImageError("image could not be decoded")


def _service(
    repo: SqlImageBridgeJobRepository,
    probe: tuple[FakeWebhook, FakeClock],
    codec: PillowImageCodec | None = None,
) -> GrokBotImageService:
    webhook, clock = probe
    deps = GrokBotImageDeps(
        repository=repo,
        webhook=webhook,
        codec=codec or PillowImageCodec(),
        clock=clock,
    )
    return GrokBotImageService(deps, GrokBotImageConfig(callback_base_url=_BASE_URL))


def _answer(repo: SqlImageBridgeJobRepository, webhook: FakeWebhook, clock: FakeClock):
    answered: set[UUID] = set()

    async def answer() -> None:
        for request in webhook.requests:
            if request.job_id not in answered:
                answered.add(request.job_id)
                image = png_bytes((1024, 1024), "WEBP")
                await repo.succeed(JobSuccess(request.job_id, image, clock.now()))

    return answer


def _job() -> CoverEditJob:
    return CoverEditJob(
        prompt="direction: café",
        photos=(
            ReferencePhoto(content=_PHOTO, mime_type="image/png"),
            ReferencePhoto(content=b"second", mime_type="image/png"),
        ),
        project_id="proj-9",
    )


async def test_edit_job_carries_the_photo_bytes_and_returns_a_cover_png() -> None:
    """Scenario: A confirmed generation sends the photo bytes and stores a private cover."""
    webhook, clock = FakeWebhook(), FakeClock()
    async with sqlite_repository() as repo:
        clock.on_sleep = _answer(repo, webhook, clock)
        image = await _service(repo, (webhook, clock)).edit_image(_job())
        job = await repo.get(webhook.requests[0].job_id)

    body = webhook.requests[0].payload()
    assert body["operation"] == "images.edit"
    assert body["image"] == [
        "data:image/png;base64," + base64.b64encode(_PHOTO).decode("ascii"),
        "data:image/png;base64," + base64.b64encode(b"second").decode("ascii"),
    ]
    assert body["prompt"] == "direction: café"
    assert body["model"] == IMAGE_BRIDGE_MODEL
    assert body["size"] == "1024x1536"
    assert body["n"] == 1
    assert body["response_format"] == "b64_json"
    assert body["metadata"] == {
        "content_type": "carousel_cover",
        "project_id": "proj-9",
    }
    assert sorted(body) == [
        "callback_token",
        "callback_url",
        "expires_at",
        "image",
        "job_id",
        "metadata",
        "model",
        "n",
        "operation",
        "prompt",
        "response_format",
        "size",
    ]
    assert job is not None
    assert job.size == "1024x1536"
    with Image.open(io.BytesIO(image)) as cover:
        assert cover.format == "PNG"
        assert cover.size == (1080, 1350)


async def test_an_image_the_codec_cannot_fit_is_a_job_error() -> None:
    """Scenario: An unusable image leaves no asset."""
    webhook, clock = FakeWebhook(), FakeClock()
    async with sqlite_repository() as repo:
        clock.on_sleep = _answer(repo, webhook, clock)
        service = _service(repo, (webhook, clock), _BrokenCodec())
        with pytest.raises(RuntimeError, match="could not be decoded"):
            await service.edit_image(_job())


def test_text_only_body_has_no_edit_keys() -> None:
    """Scenario: Text-only bridge jobs keep the old webhook body."""
    request = WebhookRequest(
        job_id=UUID(int=1),
        model="gpt-image-2",
        prompt="p",
        size="1536x1024",
        callback_url="https://x/cb",
        callback_token="t",
        expires_at=T0,
    )

    body = request.payload()

    assert "operation" not in body
    assert "image" not in body
    assert sorted(body) == [
        "callback_token",
        "callback_url",
        "expires_at",
        "job_id",
        "metadata",
        "model",
        "n",
        "prompt",
        "response_format",
        "size",
    ]


def test_data_url_shape() -> None:
    """Scenario: A confirmed generation sends the photo bytes and stores a private cover."""
    assert data_url(b"ABC", "image/png") == "data:image/png;base64,QUJD"


def test_cover_editor_needs_the_bridge_urls() -> None:
    """Scenario: The bridge is not configured."""
    settings = Settings.model_validate({
        "openai_api_key": SecretStr("sk"),
        "carousel_checkpoint_backend": "postgres",
    })
    with pytest.raises(ImageBridgeConfigError, match="GROKBOT_IMAGE_WEBHOOK_URL"):
        build_grokbot_cover_editor(settings)


def test_cover_editor_is_the_bridge_service_when_configured() -> None:
    """Scenario: A confirmed generation sends the photo bytes and stores a private cover."""
    settings = Settings.model_validate({
        "openai_api_key": SecretStr("sk"),
        "carousel_checkpoint_backend": "postgres",
        "grokbot_image_webhook_url": SecretStr("https://hooks.example/x"),
        "image_bridge_public_base_url": _BASE_URL,
    })
    assert isinstance(build_grokbot_cover_editor(settings), GrokBotImageService)


def test_cover_jobs_share_one_editor(monkeypatch: pytest.MonkeyPatch) -> None:
    """Scenario: A confirmed generation sends the photo bytes and stores a private cover."""
    from rag_backend.infrastructure.config.settings import get_settings
    from rag_backend.modules.editorial.public import cover_run_wiring

    monkeypatch.setenv("GROKBOT_IMAGE_WEBHOOK_URL", "https://hooks.example/x")
    monkeypatch.setenv("IMAGE_BRIDGE_PUBLIC_BASE_URL", _BASE_URL)
    get_settings.cache_clear()
    try:
        first = cover_run_wiring(str).editor
        second = cover_run_wiring(str).editor
        get_settings.cache_clear()
        third = cover_run_wiring(str).editor
    finally:
        get_settings.cache_clear()

    assert first is second
    assert third is not first


async def test_a_refused_claim_sends_nothing() -> None:
    """Scenario: A queued job whose row was failed meanwhile sends nothing."""
    from dataclasses import replace

    from rag_backend.domain.models.cover_generation import CoverJobCancelledError

    asked: list[bool] = []

    async def _refuse() -> bool:
        asked.append(True)
        return False

    webhook, clock = FakeWebhook(), FakeClock()
    async with sqlite_repository() as repo:
        service = _service(repo, (webhook, clock))
        with pytest.raises(CoverJobCancelledError):
            await service.edit_image(replace(_job(), claim=_refuse))

    assert asked == [True]
    assert webhook.requests == []


async def test_the_claim_runs_inside_the_slot_before_the_webhook() -> None:
    """Scenario: A queued job is timed from its bridge slot, not its creation."""
    from dataclasses import replace

    webhook, clock = FakeWebhook(), FakeClock()
    order: list[str] = []
    async with sqlite_repository() as repo:
        service = _service(repo, (webhook, clock))

        async def _claim() -> bool:
            order.append(f"claim:{service._slots._value}:{len(webhook.requests)}")
            return True

        clock.on_sleep = _answer(repo, webhook, clock)
        await service.edit_image(replace(_job(), claim=_claim))

    assert order == ["claim:1:0"]
    assert len(webhook.requests) == 1
