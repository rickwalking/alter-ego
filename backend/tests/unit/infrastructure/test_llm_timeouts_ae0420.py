"""AE-0420: per-call budgets cover the slow Go endpoint (llm_timeouts_ae0420.feature)."""

from __future__ import annotations

from rag_backend.infrastructure.config.llm_routing_constants import (
    LLM_ROLE_FAST,
    LLM_ROLE_REASONING,
    LLM_TIMEOUT_FALLBACK_SECONDS,
)
from rag_backend.infrastructure.external.chat_model_factory import role_timeout

_SLOWEST_MEASURED_DRAFT_SECONDS = 134.0


def test_fast_role_waits_for_a_slow_long_draft() -> None:
    """Scenario: The fast role waits long enough for a slow long draft."""
    assert role_timeout(LLM_ROLE_FAST) >= 300.0
    assert role_timeout(LLM_ROLE_FAST) > _SLOWEST_MEASURED_DRAFT_SECONDS * 2


def test_reasoning_role_keeps_the_larger_budget() -> None:
    """Scenario: The reasoning role keeps a larger budget than the fast role."""
    assert role_timeout(LLM_ROLE_REASONING) >= 360.0
    assert role_timeout(LLM_ROLE_REASONING) > role_timeout(LLM_ROLE_FAST)


def test_fallback_budget_is_no_shorter_than_fast() -> None:
    """Scenario: The fallback budget is no shorter than the fast role's."""
    assert LLM_TIMEOUT_FALLBACK_SECONDS >= 300.0
    assert LLM_TIMEOUT_FALLBACK_SECONDS >= role_timeout(LLM_ROLE_FAST)
