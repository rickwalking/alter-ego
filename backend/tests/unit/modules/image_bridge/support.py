"""Shared fakes for the image bridge tests.

Gherkin: tests/features/image_bridge.feature
"""

from __future__ import annotations

import base64
import io
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from rag_backend.modules.image_bridge.domain.models import (
    ImageBridgeJob,
    ImageBridgeJobStatus,
    WebhookRequest,
)
from rag_backend.modules.image_bridge.domain.tokens import token_digest
from rag_backend.modules.image_bridge.infrastructure.models import (
    ImageBridgeJobModel,
)
from rag_backend.modules.image_bridge.infrastructure.repository import (
    SqlImageBridgeJobRepository,
)

T0 = datetime(2026, 10, 15, 20, 0, tzinfo=UTC)
TOKEN = "callback-token-for-tests-0123456789abcdefghij"
TIMEOUT_SECONDS = 600


def png_bytes(size: tuple[int, int] = (1024, 1024), fmt: str = "PNG") -> bytes:
    """A solid image of ``size`` encoded as ``fmt``."""
    out = io.BytesIO()
    Image.new("RGB", size, (200, 30, 90)).save(out, format=fmt)
    return out.getvalue()


def b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def images_response(data: bytes) -> dict[str, object]:
    """The OpenAI ImagesResponse body the Grok Bot posts."""
    return {"created": 1760558400, "data": [{"b64_json": b64(data)}]}


def pending_job(now: datetime = T0, token: str = TOKEN) -> ImageBridgeJob:
    return ImageBridgeJob(
        id=uuid4(),
        status=ImageBridgeJobStatus.PENDING,
        size="1536x1024",
        token_sha256=token_digest(token),
        created_at=now,
        expires_at=now + timedelta(seconds=TIMEOUT_SECONDS),
    )


@asynccontextmanager
async def sqlite_repository() -> AsyncIterator[SqlImageBridgeJobRepository]:
    """A repository over a private in-memory SQLite database."""
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(
            ImageBridgeJobModel.metadata.create_all,
            tables=[ImageBridgeJobModel.__table__],
        )
    maker: async_sessionmaker[AsyncSession] = async_sessionmaker(
        engine, expire_on_commit=False
    )
    try:
        yield SqlImageBridgeJobRepository(lambda: maker)
    finally:
        await engine.dispose()


@dataclass
class FakeClock:
    """Manual clock; ``on_sleep`` lets a test act as the other worker."""

    current: datetime = T0
    sleeps: list[float] = field(default_factory=list)
    on_sleep: Callable[[], Awaitable[None]] | None = None

    def now(self) -> datetime:
        return self.current

    async def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.current += timedelta(seconds=seconds)
        if self.on_sleep is not None:
            await self.on_sleep()


@dataclass
class FakeWebhook:
    """Records deliveries; raises ``error`` when set."""

    requests: list[WebhookRequest] = field(default_factory=list)
    error: Exception | None = None

    async def deliver(self, request: WebhookRequest) -> None:
        self.requests.append(request)
        if self.error is not None:
            raise self.error
