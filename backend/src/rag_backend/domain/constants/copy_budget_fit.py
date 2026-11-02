"""Constants for fitting generated slide copy into the contract's copy budgets.

The shorten step runs before the presentation validation: every field over its
budget goes to the fast model, which rewrites it within the limit. At most
``COPY_BUDGET_FIT_MAX_ATTEMPTS`` model calls; what still does not fit goes to
the normal validation. The limits themselves are never stored here: they come
from the presentation contract through the validator's resolvers.
"""

from __future__ import annotations

from typing import Final

COPY_BUDGET_FIT_MAX_ATTEMPTS: Final[int] = 2
COPY_BUDGET_FIT_TIMEOUT_SECONDS: Final[float] = 180.0

COPY_BUDGET_PROMPT_DOMAIN: Final[str] = "carousel_copy_budget"
COPY_BUDGET_PROMPT_VERSION: Final[str] = "v1"
COPY_BUDGET_PROMPT_FIT: Final[str] = "fit_fields"
COPY_BUDGET_PROMPT_LIMITS: Final[str] = "slide_limits"

COPY_BUDGET_VAR_FIELDS_JSON: Final[str] = "fields_json"
COPY_BUDGET_VAR_STYLE_GUIDE: Final[str] = "style_guide"
COPY_BUDGET_VAR_SLIDE_TYPE: Final[str] = "slide_type"
COPY_BUDGET_VAR_LIMITS: Final[str] = "limits"

LIMIT_KEY_FIELD: Final[str] = "field"
LIMIT_KEY_MAX_CHARACTERS: Final[str] = "max_characters"
LIMIT_KEY_MAX_LINES: Final[str] = "max_lines"
LIMIT_KEY_MAX_WORDS: Final[str] = "max_words"
LIMIT_KEY_MIN_WORDS: Final[str] = "min_words"

TRANSLATION_LIMITS_KEY: Final[str] = "limits"
BINDABLE_MODEL_KEYS: Final[tuple[str, ...]] = ("temperature", "max_tokens")
COPY_BUDGET_TRACE_DETAIL: Final[str] = "copy budget fit"
ITEM_FIELD_PATTERN: Final[str] = "{list_field}[].{item_field}"

LOG_COPY_BUDGET_FIT_ATTEMPT: Final[str] = "copy_budget_fit_attempt"
LOG_COPY_BUDGET_FIT_DONE: Final[str] = "copy_budget_fit_done"
LOG_COPY_BUDGET_FIT_MODEL_FAILED: Final[str] = "copy_budget_fit_model_failed"

__all__ = [
    "BINDABLE_MODEL_KEYS",
    "COPY_BUDGET_FIT_MAX_ATTEMPTS",
    "COPY_BUDGET_FIT_TIMEOUT_SECONDS",
    "COPY_BUDGET_PROMPT_DOMAIN",
    "COPY_BUDGET_PROMPT_FIT",
    "COPY_BUDGET_PROMPT_LIMITS",
    "COPY_BUDGET_PROMPT_VERSION",
    "COPY_BUDGET_TRACE_DETAIL",
    "COPY_BUDGET_VAR_FIELDS_JSON",
    "COPY_BUDGET_VAR_LIMITS",
    "COPY_BUDGET_VAR_SLIDE_TYPE",
    "COPY_BUDGET_VAR_STYLE_GUIDE",
    "ITEM_FIELD_PATTERN",
    "LIMIT_KEY_FIELD",
    "LIMIT_KEY_MAX_CHARACTERS",
    "LIMIT_KEY_MAX_LINES",
    "LIMIT_KEY_MAX_WORDS",
    "LIMIT_KEY_MIN_WORDS",
    "LOG_COPY_BUDGET_FIT_ATTEMPT",
    "LOG_COPY_BUDGET_FIT_DONE",
    "LOG_COPY_BUDGET_FIT_MODEL_FAILED",
    "TRANSLATION_LIMITS_KEY",
]
