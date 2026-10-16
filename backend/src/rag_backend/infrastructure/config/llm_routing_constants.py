"""Per-task LLM model routing defaults (AE-0391).

GLM-5.3 (a reasoning model) made a carousel content phase take 60+ minutes:
~15 sequential calls of 3-10 min each. Carousel calls are now routed by role to
DeepSeek models on the same OpenCode Go endpoint, with GLM-5.3 kept as the
automatic fallback. Benchmarks (prod endpoint, 2026-10-15) live in
``docs/backend/llm-model-routing.md``.

AE-0395: GLM-5.3 was dropped as the fallback. In prod (2026-10-16) it answered
four calls in a row with empty content after ~8.5 minutes each. Each role now
falls back to a fast Qwen model (benchmarked on the same endpoint: valid JSON in
pt-BR in 9-24 s), and every model gets ``LLM_ATTEMPTS_PER_MODEL`` attempts
before the call moves on.

The model ids here are only the defaults; ``Settings`` reads the live values
from ``LLM_MODEL_REASONING`` / ``LLM_MODEL_FAST`` / ``LLM_MODEL_FALLBACK`` /
``LLM_MODEL_FALLBACK_REASONING``.
"""

from rag_backend.domain.constants.carousel_workflow import (
    DEFAULT_CONTENT_DRAFT_CONCURRENCY as _DOMAIN_DRAFT_CONCURRENCY,
)

# Roles a carousel LLM call can be routed to.
LLM_ROLE_REASONING = "reasoning"
LLM_ROLE_FAST = "fast"

# Default model ids (verified on GET /models of the OpenCode Go endpoint).
DEFAULT_LLM_MODEL_REASONING = "deepseek-v4-pro"
DEFAULT_LLM_MODEL_FAST = "deepseek-v4.1-flash"
# Fallback of the fast role (and the default fallback).
DEFAULT_LLM_MODEL_FALLBACK = "qwen3.8-flash"
# Fallback of the reasoning role (research, outline, rubric).
DEFAULT_LLM_MODEL_FALLBACK_REASONING = "qwen3.8-max"

# Per-call wall-clock budgets (one attempt).
LLM_TIMEOUT_REASONING_SECONDS = 240.0
LLM_TIMEOUT_FAST_SECONDS = 120.0
LLM_TIMEOUT_FALLBACK_SECONDS = 180.0

# AE-0395: attempts per model (primary, then fallback) for a timeout, an error
# (except auth) or empty content, with exponential backoff between attempts.
LLM_ATTEMPTS_PER_MODEL = 5
LLM_RETRY_BACKOFF_BASE_SECONDS = 2.0
LLM_RETRY_BACKOFF_MAX_SECONDS = 15.0

# Slides drafted concurrently in the content phase. Bounded: the endpoint's
# rate limits are unknown (429s are retried with backoff by the OpenAI SDK).
DEFAULT_CONTENT_DRAFT_CONCURRENCY = _DOMAIN_DRAFT_CONCURRENCY

# Langfuse run tags/metadata recording which model ran and in which role.
LLM_TAG_ROLE_PREFIX = "role:"
LLM_TAG_MODEL_PREFIX = "model:"
LLM_TAG_FALLBACK = "fallback:true"
LLM_METADATA_ROLE = "llm_role"
LLM_METADATA_MODEL = "llm_model"
LLM_METADATA_FALLBACK = "llm_fallback"

# Structured log events / reasons.
LOG_LLM_FALLBACK_USED = "llm_fallback_used"
LOG_LLM_JSON_FALLBACK_USED = "llm_json_fallback_used"
LOG_LLM_RETRY = "llm_retry"
LOG_LLM_JSON_RETRY = "llm_json_retry"
FALLBACK_REASON_TIMEOUT = "timeout"
FALLBACK_REASON_EMPTY = "empty_content"
FALLBACK_REASON_ERROR = "error"
FALLBACK_REASON_BAD_JSON = "bad_json"

# Primary failures that must surface instead of being masked by the fallback:
# the fallback uses the same key, so it would fail the same way.
AUTH_STATUS_CODES = frozenset({401, 403})
