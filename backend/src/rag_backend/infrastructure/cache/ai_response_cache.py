"""In-memory cache for AI prompt responses (CACHE-001).

Production can swap this for Redis-backed storage without changing callers.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass


@dataclass(frozen=True)
class CacheEntry:
    """Cached LLM response with expiry."""

    value: str
    expires_at: float


class AIResponseCache:
    """TTL cache keyed by hash of prompt + model identifier."""

    def __init__(self, default_ttl_seconds: int = 3600) -> None:
        self._default_ttl = default_ttl_seconds
        self._store: dict[str, CacheEntry] = {}

    @staticmethod
    def _make_key(prompt: str, model_id: str, scope: str = "global") -> str:
        return hashlib.sha256(f"{scope}:{model_id}:{prompt}".encode()).hexdigest()

    def get(self, prompt: str, model_id: str, scope: str = "global") -> str | None:
        key = self._make_key(prompt, model_id, scope)
        entry = self._store.get(key)
        if entry is None:
            return None
        if entry.expires_at < time.time():
            del self._store[key]
            return None
        return entry.value

    def set(
        self,
        prompt: str,
        model_id: str,
        value: str,
        ttl_seconds: int | None = None,
        scope: str = "global",
    ) -> None:
        key = self._make_key(prompt, model_id, scope)
        ttl = ttl_seconds if ttl_seconds is not None else self._default_ttl
        self._store[key] = CacheEntry(value=value, expires_at=time.time() + ttl)

    def clear(self) -> None:
        self._store.clear()


_GLOBAL_AI_CACHE = AIResponseCache()


def get_ai_response_cache() -> AIResponseCache:
    """Return the process-wide AI response cache."""
    return _GLOBAL_AI_CACHE


__all__ = ["AIResponseCache", "CacheEntry", "get_ai_response_cache"]
