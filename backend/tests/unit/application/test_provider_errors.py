"""Unit tests for LLM-provider error classification (AE-0319).

Scenarios: tests/features/workflow_start_provider_errors.feature
"""

from __future__ import annotations

import anthropic
import httpx
import openai

from rag_backend.application.services.carousel.provider_errors import (
    classify_provider_error,
)
from rag_backend.domain.constants.carousel_workflow import (
    ERR_PROVIDER_RATE_LIMITED,
    ERR_PROVIDER_UNAVAILABLE,
)


def _response(status_code: int) -> httpx.Response:
    request = httpx.Request("POST", "https://provider.example.com/v1/chat")
    return httpx.Response(status_code, request=request, json={"error": {}})


def _openai_rate_limit() -> openai.RateLimitError:
    return openai.RateLimitError(
        "5-hour usage limit reached", response=_response(429), body=None
    )


def _anthropic_rate_limit() -> anthropic.RateLimitError:
    return anthropic.RateLimitError("rate limited", response=_response(429), body=None)


class TestClassifyProviderError:
    def test_openai_rate_limit_maps_to_rate_limited(self) -> None:
        """Scenario: Provider rate limit maps to 429."""
        assert classify_provider_error(_openai_rate_limit()) == (
            ERR_PROVIDER_RATE_LIMITED
        )

    def test_anthropic_rate_limit_maps_to_rate_limited(self) -> None:
        assert classify_provider_error(_anthropic_rate_limit()) == (
            ERR_PROVIDER_RATE_LIMITED
        )

    def test_openai_api_error_maps_to_unavailable(self) -> None:
        """Scenario: Provider outage maps to 503."""
        exc = openai.APIStatusError("bad gateway", response=_response(502), body=None)
        assert classify_provider_error(exc) == ERR_PROVIDER_UNAVAILABLE

    def test_openai_connection_error_maps_to_unavailable(self) -> None:
        request = httpx.Request("POST", "https://provider.example.com/v1/chat")
        exc = openai.APIConnectionError(request=request)
        assert classify_provider_error(exc) == ERR_PROVIDER_UNAVAILABLE

    def test_non_provider_error_is_unclassified(self) -> None:
        """Scenario: Non-provider errors are unchanged."""
        assert classify_provider_error(RuntimeError("boom")) is None
        assert classify_provider_error(ValueError("bad")) is None
