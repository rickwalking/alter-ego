"""Process-wide cache for the signals bundle.

The lock is held for the whole load so concurrent scout requests share
one collection. A hit returns the stored bundle, including its original
``generated_at``.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta

from rag_backend.modules.autopilot.domain.ports import Clock
from rag_backend.modules.autopilot.domain.signals import SignalsBundle

BundleLoader = Callable[[], Awaitable[SignalsBundle]]


class SignalBundleCache:
    """TTL cache. ``ttl_seconds`` of zero still stores, but the next read misses."""

    def __init__(self, clock: Clock, ttl_seconds: float) -> None:
        self._clock = clock
        self._ttl = timedelta(seconds=ttl_seconds)
        self._lock = asyncio.Lock()
        self._bundle: SignalsBundle | None = None
        self._stored_at: datetime | None = None

    async def get_or_load(self, loader: BundleLoader) -> SignalsBundle:
        """Return the fresh bundle, or call ``loader`` once and store it."""
        async with self._lock:
            fresh = self._fresh()
            if fresh is not None:
                return fresh
            bundle = await loader()
            self._bundle = bundle
            self._stored_at = self._clock.now()
            return bundle

    def _fresh(self) -> SignalsBundle | None:
        if self._bundle is None or self._stored_at is None:
            return None
        age = self._clock.now() - self._stored_at
        if age >= self._ttl:
            return None
        return self._bundle
