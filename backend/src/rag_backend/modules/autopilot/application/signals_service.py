"""Run every signal collector and return one deduped bundle.

A collector that raises or exceeds its timeout is logged and skipped.
The HTTP status stays 200. Results are cached for 30 minutes.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

import structlog

from rag_backend.modules.autopilot.application.signal_cache import SignalBundleCache
from rag_backend.modules.autopilot.constants import (
    ERROR_FAILED,
    ERROR_TIMEOUT,
    LOG_COLLECTOR_FAILED,
    LOG_COLLECTOR_TIMEOUT,
    MAX_SIGNALS,
)
from rag_backend.modules.autopilot.domain.ports import Clock, Collector
from rag_backend.modules.autopilot.domain.signals import (
    CollectorError,
    CollectWindow,
    Signal,
    SignalsBundle,
    ensure_utc,
)
from rag_backend.modules.autopilot.domain.x_status import canonical_url

logger = structlog.get_logger()


@dataclass(frozen=True, kw_only=True)
class SignalsServiceDependencies:
    """Collaborators for one signals service. One object keeps the constructor small."""

    collectors: tuple[Collector, ...]
    clock: Clock
    cache: SignalBundleCache
    timeout_seconds: float
    max_signals: int = MAX_SIGNALS


@dataclass(frozen=True, kw_only=True)
class _CollectorOutcome:
    signals: tuple[Signal, ...]
    error: CollectorError | None


class SignalsService:
    """Collect, isolate, dedupe, cap, and cache the scout bundle."""

    def __init__(self, deps: SignalsServiceDependencies) -> None:
        self._deps = deps

    async def collect_all(self) -> SignalsBundle:
        """Return the cached bundle, refreshing it after the TTL."""
        return await self._deps.cache.get_or_load(self._load)

    async def _load(self) -> SignalsBundle:
        window = CollectWindow(as_of=ensure_utc(self._deps.clock.now()))
        outcomes = await asyncio.gather(
            *(self._run(collector, window) for collector in self._deps.collectors)
        )
        return self._bundle(outcomes)

    async def _run(
        self,
        collector: Collector,
        window: CollectWindow,
    ) -> _CollectorOutcome:
        try:
            found = await asyncio.wait_for(
                collector.collect(window),
                timeout=self._deps.timeout_seconds,
            )
        except TimeoutError:
            _log_timeout(collector)
            return _failed(collector, ERROR_TIMEOUT)
        except Exception as exc:
            _log_failed(collector, exc)
            return _failed(collector, ERROR_FAILED)
        return _CollectorOutcome(signals=tuple(found), error=None)

    def _bundle(self, outcomes: list[_CollectorOutcome]) -> SignalsBundle:
        signals: list[Signal] = []
        errors: list[CollectorError] = []
        for outcome in outcomes:
            signals.extend(outcome.signals)
            if outcome.error is not None:
                errors.append(outcome.error)
        return SignalsBundle(
            generated_at=ensure_utc(self._deps.clock.now()),
            signals=dedupe_signals(signals, self._deps.max_signals),
            errors=errors,
        )


def _log_timeout(collector: Collector) -> None:
    logger.warning(LOG_COLLECTOR_TIMEOUT, source=collector.source_name())


def _log_failed(collector: Collector, exc: Exception) -> None:
    logger.warning(
        LOG_COLLECTOR_FAILED,
        source=collector.source_name(),
        error_type=type(exc).__name__,
    )


def dedupe_signals(signals: list[Signal], limit: int) -> list[Signal]:
    """Keep the first signal for each canonical URL, then stop at ``limit``."""
    seen: set[str] = set()
    kept: list[Signal] = []
    for signal in signals:
        key = canonical_url(signal.url)
        if key in seen:
            continue
        seen.add(key)
        kept.append(signal)
        if len(kept) == limit:
            return kept
    return kept


def _failed(collector: Collector, message: str) -> _CollectorOutcome:
    error = CollectorError(source=collector.source_name(), message=message)
    return _CollectorOutcome(signals=(), error=error)
