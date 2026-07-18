"""LLM-provider error classification for synchronous workflow routes (AE-0319).

Observed live 2026-07-17: the OpenCode Go GLM endpoint returned 429
``GoUsageLimitError`` during ``POST workflow/start`` and the route surfaced a
generic ``500 Internal Server Error`` — no retry hint, no actionable detail.
This module maps vendor SDK exceptions onto the two workflow-start error
details so the route can answer 429 (rate limited — retry later) or 503
(provider down — try again) instead. Classification lives in the application
layer because both configured chat vendors (OpenAI-compatible GLM endpoint and
Anthropic) are already application-visible via LangChain.
"""

from __future__ import annotations

import anthropic
import openai

from rag_backend.domain.constants.carousel_workflow import (
    ERR_PROVIDER_RATE_LIMITED,
    ERR_PROVIDER_UNAVAILABLE,
)

_RATE_LIMIT_ERRORS: tuple[type[Exception], ...] = (
    openai.RateLimitError,
    anthropic.RateLimitError,
)

_PROVIDER_ERRORS: tuple[type[Exception], ...] = (
    openai.APIError,
    anthropic.APIError,
)


def classify_provider_error(exc: BaseException) -> str | None:
    """Map a vendor SDK exception onto a workflow error detail, else ``None``.

    Order matters: rate limits are ``APIError`` subclasses and must win.
    ``None`` means "not a provider error" — the caller re-raises unchanged.
    """
    if isinstance(exc, _RATE_LIMIT_ERRORS):
        return ERR_PROVIDER_RATE_LIMITED
    if isinstance(exc, _PROVIDER_ERRORS):
        return ERR_PROVIDER_UNAVAILABLE
    return None


__all__ = ["classify_provider_error"]
