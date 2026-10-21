"""HTTP bundle for GET /api/autopilot/signals.

Gherkin: tests/features/autopilot_signals.feature
  Scenario: Bundle combines all free sources
  Scenario: One source failing does not fail the bundle
"""

from __future__ import annotations

import asyncio
import hashlib
import os
from collections.abc import AsyncIterator, Iterator
from datetime import datetime

import pytest
from httpx import ASGITransport, AsyncClient

from rag_backend.domain.constants import ENCODING_UTF8
from rag_backend.modules.autopilot.application.signal_cache import SignalBundleCache
from rag_backend.modules.autopilot.application.signals_service import (
    SignalsService,
    SignalsServiceDependencies,
)
from rag_backend.modules.autopilot.constants import (
    APP_STATE_SIGNALS,
    ERROR_TIMEOUT,
    HEADER_API_KEY,
    SOURCE_BLUESKY,
    SOURCE_GITHUB,
    SOURCE_HF_PAPERS,
    SOURCE_HN,
    SOURCE_RSS,
    SOURCE_X_SEARCH,
)
from rag_backend.modules.autopilot.domain.signals import (
    CollectWindow,
    Signal,
    SignalSource,
)
from tests.unit.autopilot.support import AS_OF, make_signal

_KEY = "k1"
_PATH = "/api/autopilot/signals"
_ENV_KEY = "GROKBOT_API_KEY_SHA256"
_SOURCES = (
    SOURCE_X_SEARCH,
    SOURCE_HN,
    SOURCE_HF_PAPERS,
    SOURCE_RSS,
    SOURCE_BLUESKY,
    SOURCE_GITHUB,
)


class _Clock:
    def now(self) -> datetime:
        return AS_OF


class _Collector:
    def __init__(self, source: str, url: str) -> None:
        self._source = source
        self._url = url

    def source_name(self) -> str:
        return self._source

    async def collect(self, window: CollectWindow) -> list[Signal]:
        del window
        return [make_signal(SignalSource(self._source), self._url)]


class _Timeout:
    def source_name(self) -> str:
        return SOURCE_BLUESKY

    async def collect(self, window: CollectWindow) -> list[Signal]:
        del window
        await asyncio.sleep(5)
        return []


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode(ENCODING_UTF8)).hexdigest()


def _service(
    *collectors: _Collector | _Timeout, timeout: float = 5.0
) -> SignalsService:
    return SignalsService(
        SignalsServiceDependencies(
            collectors=collectors,
            clock=_Clock(),
            cache=SignalBundleCache(_Clock(), 60),
            timeout_seconds=timeout,
        )
    )


@pytest.fixture
def configured_key() -> Iterator[None]:
    previous = os.environ.get(_ENV_KEY)
    os.environ[_ENV_KEY] = _digest(_KEY)
    from rag_backend.infrastructure.config.settings import get_settings

    get_settings.cache_clear()
    yield
    if previous is None:
        os.environ.pop(_ENV_KEY, None)
    else:
        os.environ[_ENV_KEY] = previous
    get_settings.cache_clear()


async def _client(service: SignalsService) -> AsyncIterator[AsyncClient]:
    from sqlalchemy.ext.asyncio import create_async_engine

    import rag_backend.infrastructure.database.config as db_config
    from rag_backend.api.app import create_app
    from rag_backend.api.middleware.rate_limiting import limiter
    from rag_backend.infrastructure.database.config import Base, close_db

    limiter.reset()
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    db_config.c_engine = engine
    app = create_app()
    setattr(app.state, APP_STATE_SIGNALS, service)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    limiter.reset()
    db_config.c_engine = None
    await close_db()
    await engine.dispose()


# Scenario: Bundle combines all free sources
@pytest.mark.asyncio
async def test_endpoint_returns_every_source_without_duplicate_urls(
    configured_key: None,
) -> None:
    """The second hn URL repeats the first source's URL and must be dropped."""
    del configured_key
    collectors = tuple(
        _Collector(source, f"https://example.com/{source}") for source in _SOURCES
    )
    repeated = (
        *collectors[:1],
        _Collector(SOURCE_HN, "https://example.com/x_search"),
        *collectors[1:],
    )
    async for client in _client(_service(*repeated)):
        response = await client.get(_PATH, headers={HEADER_API_KEY: _KEY})
    assert response.status_code == 200
    body = response.json()
    sources = {item["source"] for item in body["signals"]}
    assert sources == set(_SOURCES)
    urls = [item["url"] for item in body["signals"]]
    assert len(urls) == len(set(urls))
    assert body["errors"] == []
    assert body["generated_at"]


# Scenario: One source failing does not fail the bundle
@pytest.mark.asyncio
async def test_endpoint_isolates_a_bluesky_timeout(configured_key: None) -> None:
    del configured_key
    service = _service(
        _Collector(SOURCE_HN, "https://example.com/hn"), _Timeout(), timeout=0.05
    )
    async for client in _client(service):
        response = await client.get(_PATH, headers={HEADER_API_KEY: _KEY})
    assert response.status_code == 200
    body = response.json()
    assert body["signals"][0]["source"] == SOURCE_HN
    assert body["errors"][0]["source"] == SOURCE_BLUESKY
    assert body["errors"][0]["message"] == ERROR_TIMEOUT
    assert SOURCE_BLUESKY in response.text
