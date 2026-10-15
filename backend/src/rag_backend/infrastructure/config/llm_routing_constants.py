"""Per-task LLM model routing defaults (AE-0391).

GLM-5.3 (a reasoning model) made a carousel content phase take 60+ minutes:
~15 sequential calls of 3-10 min each. Carousel calls are now routed by role to
DeepSeek models on the same OpenCode Go endpoint, with GLM-5.3 kept as the
automatic fallback. Benchmarks (prod endpoint, 2026-10-15) live in
``docs/backend/llm-model-routing.md``.

The model ids here are only the defaults; ``Settings`` reads the live values
from ``LLM_MODEL_REASONING`` / ``LLM_MODEL_FAST`` / ``LLM_MODEL_FALLBACK``.
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
DEFAULT_LLM_MODEL_FALLBACK = "glm-5.3"

# Per-call wall-clock budgets of the primary model. The fallback is GLM-5.3,
# which routinely needs 3-10 min, so it gets its own, longer budget.
LLM_TIMEOUT_REASONING_SECONDS = 240.0
LLM_TIMEOUT_FAST_SECONDS = 120.0
LLM_TIMEOUT_FALLBACK_SECONDS = 900.0

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
FALLBACK_REASON_TIMEOUT = "timeout"
FALLBACK_REASON_EMPTY = "empty_content"
FALLBACK_REASON_ERROR = "error"
FALLBACK_REASON_BAD_JSON = "bad_json"

# Primary failures that must surface instead of being masked by the fallback:
# the fallback uses the same key, so it would fail the same way.
AUTH_STATUS_CODES = frozenset({401, 403})
