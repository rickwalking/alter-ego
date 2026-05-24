"""Unit tests for AI response cache."""

import time
from unittest.mock import patch

from rag_backend.infrastructure.cache.ai_response_cache import AIResponseCache


class TestAIResponseCache:
    def test_set_and_get_returns_cached_value(self) -> None:
        cache = AIResponseCache(default_ttl_seconds=60)
        cache.set("prompt", "model-a", "response")

        assert cache.get("prompt", "model-a") == "response"

    def test_get_returns_none_for_missing_key(self) -> None:
        cache = AIResponseCache()

        assert cache.get("missing", "model-a") is None

    def test_clear_removes_entries(self) -> None:
        cache = AIResponseCache()
        cache.set("prompt", "model-a", "response")
        cache.clear()

        assert cache.get("prompt", "model-a") is None

    def test_get_returns_none_after_ttl_expires(self) -> None:
        cache = AIResponseCache(default_ttl_seconds=1)
        cache.set("prompt", "model-a", "response", ttl_seconds=1)

        with patch(
            "rag_backend.infrastructure.cache.ai_response_cache.time.time",
            return_value=time.time() + 2,
        ):
            assert cache.get("prompt", "model-a") is None

    def test_scope_prefix_isolates_cache_entries(self) -> None:
        cache = AIResponseCache()
        cache.set("prompt", "model-a", "global-value", scope="global")
        cache.set("prompt", "model-a", "user-value", scope="user-1")

        assert cache.get("prompt", "model-a", scope="global") == "global-value"
        assert cache.get("prompt", "model-a", scope="user-1") == "user-value"
