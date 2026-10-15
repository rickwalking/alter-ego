"""POST /api/v1/image-bridge/jobs/{job_id}/result (AE-0393, AC3/AC4/AC7/AC11).

Gherkin: tests/features/image_bridge.feature
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import timedelta

import httpx
from fastapi import FastAPI
from structlog.testing import capture_logs

from rag_backend.modules.image_bridge.api.router import (
    get_callback_service,
    router,
)
from rag_backend.modules.image_bridge.application.callback import (
    CallbackDeps,
    ImageBridgeCallbackService,
)
from rag_backend.modules.image_bridge.constants import MAX_CALLBACK_BODY_BYTES
from rag_backend.modules.image_bridge.domain.models import (
    ImageBridgeJob,
    ImageBridgeJobStatus,
    JobDeadline,
)
from rag_backend.modules.image_bridge.infrastructure.pillow_codec import (
    PillowImageCodec,
)
from rag_backend.modules.image_bridge.infrastructure.repository import (
    SqlImageBridgeJobRepository,
)
from tests.unit.modules.image_bridge.support import (
    TOKEN,
    FakeClock,
    b64,
    images_response,
    pending_job,
    png_bytes,
    sqlite_repository,
)

HEADER = "X-Image-Bridge-Token"
UNAUTHORIZED = {"detail": "invalid callback token"}


@dataclass
class _Harness:
    client: httpx.AsyncClient
    repo: SqlImageBridgeJobRepository
    clock: FakeClock

    async def post(
        self, job_id: object, body: object, token: str | None = TOKEN
    ) -> httpx.Response:
        headers = {HEADER: token} if token is not None else {}
        content = body if isinstance(body, bytes) else json.dumps(body).encode()
        return await self.client.post(
            f"/api/v1/image-bridge/jobs/{job_id}/result",
            content=content,
            headers={"Content-Type": "application/json", **headers},
        )

    async def job(self, job: ImageBridgeJob) -> ImageBridgeJob:
        stored = await self.repo.get(job.id)
        assert stored is not None
        return stored


@asynccontextmanager
async def _harness() -> AsyncIterator[_Harness]:
    clock = FakeClock()
    async with sqlite_repository() as repo:
        service = ImageBridgeCallbackService(
            CallbackDeps(repository=repo, codec=PillowImageCodec(), clock=clock)
        )
        app = FastAPI()
        app.include_router(router, prefix="/api")
        app.dependency_overrides[get_callback_service] = lambda: service
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://t"
        ) as client:
            yield _Harness(client=client, repo=repo, clock=clock)


async def _pending(h: _Harness) -> ImageBridgeJob:
    job = pending_job(h.clock.now())
    await h.repo.create(job)
    return job


# Scenario: Grok Bot returns an image
async def test_valid_images_response_is_accepted_and_stored() -> None:
    image = png_bytes((1122, 1402))
    async with _harness() as h:
        job = await _pending(h)
        response = await h.post(job.id, images_response(image))
        stored = await h.job(job)
        taken = await h.repo.take_image(job.id)
    assert response.status_code == 202
    assert response.json() == {"detail": "accepted"}
    assert stored.status is ImageBridgeJobStatus.SUCCEEDED
    assert taken == image


# Scenario: Wrong token
async def test_wrong_token_is_401_and_job_stays_pending() -> None:
    async with _harness() as h:
        job = await _pending(h)
        response = await h.post(job.id, images_response(png_bytes()), token="nope")
        stored = await h.job(job)
    assert response.status_code == 401
    assert response.json() == UNAUTHORIZED
    assert stored.status is ImageBridgeJobStatus.PENDING


# Scenario: Missing token
async def test_missing_token_is_401() -> None:
    async with _harness() as h:
        job = await _pending(h)
        response = await h.post(job.id, images_response(png_bytes()), token=None)
        stored = await h.job(job)
    assert response.status_code == 401
    assert response.json() == UNAUTHORIZED
    assert stored.status is ImageBridgeJobStatus.PENDING


# Scenario: Unknown job looks the same as a wrong token
async def test_unknown_or_malformed_job_id_is_the_same_401() -> None:
    async with _harness() as h:
        await _pending(h)
        wrong = await h.post(
            "6f1c2a9e-4c1b-4f7e-9a51-2d8f0c7b3e10", images_response(png_bytes())
        )
        not_uuid = await h.post("not-a-uuid", images_response(png_bytes()))
    assert wrong.status_code == not_uuid.status_code == 401
    assert wrong.json() == not_uuid.json() == UNAUTHORIZED


# Scenario: Duplicate callback
async def test_duplicate_callback_is_409_and_writes_nothing() -> None:
    first_image, second_image = png_bytes((600, 600)), png_bytes((700, 700))
    async with _harness() as h:
        job = await _pending(h)
        first = await h.post(job.id, images_response(first_image))
        second = await h.post(job.id, images_response(second_image))
        taken = await h.repo.take_image(job.id)
    assert first.status_code == 202
    assert second.status_code == 409
    assert second.json() == {"detail": "job is no longer pending"}
    assert taken == first_image


# Scenario: Grok Bot refuses
async def test_openai_error_body_fails_the_job_with_its_code() -> None:
    body = {
        "error": {
            "type": "image_generation_error",
            "code": "content_policy",
            "message": "refused",
        }
    }
    async with _harness() as h:
        job = await _pending(h)
        response = await h.post(job.id, body)
        stored = await h.job(job)
    assert response.status_code == 202
    assert stored.status is ImageBridgeJobStatus.FAILED
    assert stored.error_code == "content_policy"
    assert stored.error_message == "refused"


# Scenario: Invalid image
async def test_base64_that_is_not_an_image_is_422_and_fails_the_job() -> None:
    async with _harness() as h:
        job = await _pending(h)
        response = await h.post(job.id, {"data": [{"b64_json": b64(b"hello")}]})
        stored = await h.job(job)
    assert response.status_code == 422
    assert stored.status is ImageBridgeJobStatus.FAILED
    assert stored.error_code == "invalid_image"


async def test_image_out_of_bounds_is_422() -> None:
    async with _harness() as h:
        job = await _pending(h)
        response = await h.post(job.id, images_response(png_bytes((256, 256))))
        stored = await h.job(job)
    assert response.status_code == 422
    assert stored.error_code == "invalid_image"


# Scenario: Malformed body
async def test_malformed_bodies_are_422_and_fail_the_job() -> None:
    bodies: list[object] = [
        b"{not json",
        b"\xff\xfe",
        {"data": []},
        [1, 2],
        {"data": [{"url": "https://x/y.png"}]},
    ]
    async with _harness() as h:
        for body in bodies:
            job = await _pending(h)
            response = await h.post(job.id, body)
            stored = await h.job(job)
            assert response.status_code == 422, body
            assert stored.status is ImageBridgeJobStatus.FAILED
            assert stored.error_code == "malformed_callback"


async def test_deeply_nested_json_is_422_not_500() -> None:
    async with _harness() as h:
        job = await _pending(h)
        response = await h.post(job.id, b"[" * 100_000 + b"]" * 100_000)
    assert response.status_code == 422


# Scenario: Oversized body
async def test_declared_oversized_body_is_413() -> None:
    async with _harness() as h:
        job = await _pending(h)
        response = await h.client.post(
            f"/api/v1/image-bridge/jobs/{job.id}/result",
            content=b"{}",
            headers={HEADER: TOKEN, "Content-Length": str(MAX_CALLBACK_BODY_BYTES + 1)},
        )
        stored = await h.job(job)
    assert response.status_code == 413
    assert stored.status is ImageBridgeJobStatus.PENDING


async def test_streamed_oversized_body_is_413() -> None:
    chunk = b"a" * (1024 * 1024)

    async def stream() -> AsyncIterator[bytes]:
        for _ in range(17):
            yield chunk

    async with _harness() as h:
        job = await _pending(h)
        response = await h.client.post(
            f"/api/v1/image-bridge/jobs/{job.id}/result",
            content=stream(),
            headers={HEADER: TOKEN},
        )
        stored = await h.job(job)
    assert response.status_code == 413
    assert response.json() == {"detail": "callback body too large"}
    assert stored.status is ImageBridgeJobStatus.PENDING


# Scenario: Grok Bot never answers -> a late callback answers 409
async def test_callback_after_the_deadline_is_409_and_expires_the_job() -> None:
    async with _harness() as h:
        job = await _pending(h)
        h.clock.current = job.expires_at + timedelta(seconds=1)
        response = await h.post(job.id, images_response(png_bytes()))
        stored = await h.job(job)
    assert response.status_code == 409
    assert stored.status is ImageBridgeJobStatus.EXPIRED


async def test_callback_for_an_expired_job_is_409() -> None:
    async with _harness() as h:
        job = await _pending(h)
        await h.repo.expire(JobDeadline(job.id, h.clock.now()))
        response = await h.post(job.id, images_response(png_bytes()))
    assert response.status_code == 409


# Scenario: Tokens are never stored or logged in clear
async def test_logs_never_carry_the_token_or_base64() -> None:
    image = png_bytes((600, 600))
    encoded = b64(image)
    async with _harness() as h:
        job = await _pending(h)
        with capture_logs() as logs:
            await h.post(job.id, images_response(image), token="wrong-token")
            await h.post(job.id, images_response(image))
            await h.post(job.id, images_response(image))
    rendered = repr(logs)
    assert logs
    assert TOKEN not in rendered
    assert "wrong-token" not in rendered
    assert encoded[:64] not in rendered
