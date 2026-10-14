"""Signals service: isolation, dedupe, cap, and cache (AE-0352).

Gherkin: tests/features/autopilot_signals.feature
  Scenario: Bundle combines all free sources
  Scenario: One source failing does not fail the bundle
  Scenario: Repeated requests reuse the cached bundle
  Scenario: The bundle is capped
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timedelta

import pytest
from structlog.testing import capture_logs

from rag_backend.modules.autopilot.application.signal_cache import SignalBundleCache
from rag_backend.modules.autopilot.application.signals_service import (
    SignalsService,
    SignalsServiceDependencies,
)
from rag_backend.modules.autopilot.constants import (
    ERROR_FAILED,
    ERROR_TIMEOUT,
    MAX_SIGNALS,
    SIGNAL_CACHE_TTL_SECONDS,
    SOURCE_BLUESKY,
    SOURCE_GITHUB,
    SOURCE_HF_PAPERS,
    SOURCE_HN,
    SOURCE_RSS,
    SOURCE_X_SEARCH,
)
from rag_backend.modules.autopilot.domain.ports import Collector
from rag_backend.modules.autopilot.domain.signals import (
    CollectWindow,
    Signal,
    SignalDraft,
    SignalSource,
    signal_from,
)
from tests.unit.autopilot.support import AS_OF, make_signal

_SOURCES = (
    SOURCE_X_SEARCH,
    SOURCE_HN,
    SOURCE_HF_PAPERS,
    SOURCE_RSS,
    SOURCE_BLUESKY,
    SOURCE_GITHUB,
)


class _Clock:
    def __init__(self) -> None:
        self.current = AS_OF

    def now(self) -> datetime:
        return self.current


class _Collector:
    def __init__(self, source: str, signals: list[Signal] | None = None) -> None:
        self.source = source
        self.signals = signals if signals is not None else [_one(source)]
        self.calls = 0

    def source_name(self) -> str:
        return self.source

    async def collect(self, window: CollectWindow) -> list[Signal]:
        del window
        self.calls += 1
        return list(self.signals)


class _Boom:
    def __init__(self, source: str, message: str) -> None:
        self.source = source
        self.message = message

    def source_name(self) -> str:
        return self.source

    async def collect(self, window: CollectWindow) -> list[Signal]:
        del window
        raise RuntimeError(self.message)


class _Sleep:
    def __init__(self, source: str, seconds: float) -> None:
        self.source = source
        self.seconds = seconds

    def source_name(self) -> str:
        return self.source

    async def collect(self, window: CollectWindow) -> list[Signal]:
        del window
        await asyncio.sleep(self.seconds)
        return []


def _one(source: str, url: str | None = None) -> Signal:
    return make_signal(SignalSource(source), url or f"https://example.com/{source}")


def _service(
    collectors: tuple[Collector, ...],
    *,
    clock: _Clock | None = None,
    timeout: float = 5.0,
    ttl: float = SIGNAL_CACHE_TTL_SECONDS,
    limit: int = MAX_SIGNALS,
) -> tuple[SignalsService, _Clock]:
    used = clock or _Clock()
    cache = SignalBundleCache(used, ttl)
    service = SignalsService(
        SignalsServiceDependencies(
            collectors=collectors,
            clock=used,
            cache=cache,
            timeout_seconds=timeout,
            max_signals=limit,
        )
    )
    return service, used


# Scenario: Bundle combines all free sources
@pytest.mark.asyncio
async def test_bundle_contains_each_source_once_per_url() -> None:
    shared = "https://example.com/shared"
    collectors = tuple(
        _Collector(source, [_one(source, shared if source == SOURCE_RSS else None)])
        for source in _SOURCES
    )
    service, _clock = _service(collectors)
    bundle = await service.collect_all()
    urls = [signal.url for signal in bundle.signals]
    assert urls == [
        "https://example.com/x_search",
        "https://example.com/hn",
        "https://example.com/hf_papers",
        "https://example.com/shared",
        "https://example.com/bluesky",
        "https://example.com/github",
    ]
    assert len(urls) == len(set(urls))
    assert bundle.errors == []
    assert {signal.source.value for signal in bundle.signals} == set(_SOURCES)


# Scenario: One source failing does not fail the bundle
@pytest.mark.asyncio
async def test_timeout_is_isolated() -> None:
    collectors = (
        _Collector(SOURCE_HN),
        _Sleep(SOURCE_BLUESKY, 5),
    )
    service, _clock = _service(collectors, timeout=0.05)
    bundle = await service.collect_all()
    assert [signal.source.value for signal in bundle.signals] == [SOURCE_HN]
    assert bundle.errors[0].source == SOURCE_BLUESKY
    assert bundle.errors[0].message == ERROR_TIMEOUT


@pytest.mark.asyncio
async def test_exception_is_isolated_and_the_secret_is_not_logged() -> None:
    secret = "super-secret-token"
    collectors = (_Collector(SOURCE_HN), _Boom(SOURCE_GITHUB, secret))
    service, _clock = _service(collectors)
    with capture_logs() as logs:
        bundle = await service.collect_all()
    assert bundle.errors[0].source == SOURCE_GITHUB
    assert bundle.errors[0].message == ERROR_FAILED
    assert secret not in json.dumps(logs)
    assert bundle.signals[0].source.value == SOURCE_HN


# Scenario: Repeated requests reuse the cached bundle
@pytest.mark.asyncio
async def test_cache_skips_collectors_until_the_ttl() -> None:
    collector = _Collector(SOURCE_HN)
    service, clock = _service((collector,), ttl=SIGNAL_CACHE_TTL_SECONDS)
    first = await service.collect_all()
    second = await service.collect_all()
    assert second == first
    assert collector.calls == 1
    clock.current = AS_OF + timedelta(seconds=SIGNAL_CACHE_TTL_SECONDS)
    await service.collect_all()
    assert collector.calls == 2


@pytest.mark.asyncio
async def test_concurrent_calls_collect_once() -> None:
    class _Slow(_Collector):
        async def collect(self, window: CollectWindow) -> list[Signal]:
            self.calls += 1
            await asyncio.sleep(0.05)
            return list(self.signals)

    slow = _Slow(SOURCE_HN)
    service, _clock = _service((slow,))
    await asyncio.gather(service.collect_all(), service.collect_all())
    assert slow.calls == 1


@pytest.mark.asyncio
async def test_canonical_host_and_slash_dedupe() -> None:
    collectors = (
        _Collector(SOURCE_HN, [make_signal(SignalSource.HN, "https://Example.com/a/")]),
        _Collector(
            SOURCE_RSS, [make_signal(SignalSource.RSS, "https://example.com/a")]
        ),
    )
    service, _clock = _service(collectors)
    bundle = await service.collect_all()
    assert len(bundle.signals) == 1
    assert bundle.signals[0].source.value == SOURCE_HN


# Scenario: The bundle is capped
@pytest.mark.asyncio
async def test_bundle_is_capped_at_200() -> None:
    signals = [
        make_signal(SignalSource.HN, f"https://example.com/{index}")
        for index in range(MAX_SIGNALS + 1)
    ]
    service, _clock = _service((_Collector(SOURCE_HN, signals),))
    bundle = await service.collect_all()
    assert len(bundle.signals) == MAX_SIGNALS
    assert bundle.signals[-1].url == f"https://example.com/{MAX_SIGNALS - 1}"


def test_signal_from_rejects_empty_copy_and_clips() -> None:
    from rag_backend.modules.autopilot.constants import MAX_SIGNAL_TEXT_CHARS

    assert (
        signal_from(
            SignalDraft(
                source=SignalSource.HN,
                url="  ",
                title="t",
                text="x",
                posted_at=AS_OF,
            )
        )
        is None
    )
    assert (
        signal_from(
            SignalDraft(
                source=SignalSource.HN,
                url="https://example.com/a",
                title="  ",
                text=" ",
                posted_at=AS_OF,
            )
        )
        is None
    )
    long = "a" * (MAX_SIGNAL_TEXT_CHARS + 5)
    kept = signal_from(
        SignalDraft(
            source=SignalSource.HN,
            url="https://example.com/a",
            title=long,
            text="ok",
            posted_at=AS_OF.replace(tzinfo=None),
        )
    )
    assert kept is not None
    assert len(kept.title) == MAX_SIGNAL_TEXT_CHARS
    assert kept.posted_at.tzinfo is not None
