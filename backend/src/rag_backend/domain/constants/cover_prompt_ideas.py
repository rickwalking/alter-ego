"""Limits and contract strings of the cover-photo prompt ideas ("Mais ideias").

The create form shows a curated catalogue of prompts for a new cover photo;
"Mais ideias" asks the fast LLM queue for ``IDEA_REQUEST_COUNT`` ideas tailored to
the carousel topic and palette. Only the topic and the palette reach the model,
never personal data. An answer with fewer than ``IDEA_MIN_COUNT`` usable
ideas gets ``IDEA_ATTEMPTS`` tries in all; the response carries at most
``IDEA_MAX_COUNT``. ``IDEA_MAX_LEN`` bounds one prompt so it fits the prompt field.
Each call gets ``IDEAS_TIMEOUT_SECONDS``, so the two attempts stay under half a minute.
"""

from __future__ import annotations

from enum import StrEnum


class IdeaLocale(StrEnum):
    """The language the ideas are written in (the dashboard's locale)."""

    PT = "pt"
    EN = "en"


IDEA_MIN_COUNT: int = 3
IDEA_MAX_COUNT: int = 6
IDEA_REQUEST_COUNT: int = 6
IDEA_ATTEMPTS: int = 2
IDEA_MIN_LEN: int = 12
IDEA_MAX_LEN: int = 400
TOPIC_MIN_LEN: int = 3
TOPIC_MAX_LEN: int = 500

IDEAS_TEMPERATURE: float = 0.9
IDEAS_MAX_TOKENS: int = 1500
IDEAS_TIMEOUT_SECONDS: float = 12.0

KEY_IDEAS: str = "ideas"
IDEA_FORBIDDEN_CHARS: tuple[str, ...] = ("<", ">", "{", "}")

LANGUAGE_BY_LOCALE: dict[IdeaLocale, str] = {
    IdeaLocale.PT: "Brazilian Portuguese",
    IdeaLocale.EN: "English",
}
NO_PALETTE_HINT: str = "no fixed palette; pick colours that suit the topic"

PROMPT_DOMAIN_COVER_PROMPT: str = "cover_prompt"
PROMPT_COVER_PROMPT_IDEAS: str = "ideas"
TRACE_PHASE_COVER_PROMPT_IDEAS: str = "cover_prompt_ideas"
TRACE_AGENT_COVER_PROMPT_IDEAS: str = "cover_prompt_ideas"
TRACE_CONTENT_TYPE_CAROUSEL: str = "carousel"

ERR_COVER_PROMPT_IDEAS_UNAVAILABLE: str = "cover_prompt_ideas_unavailable"
ERR_TOPIC_TOO_SHORT: str = "topic is too short"
LOG_COVER_IDEAS_CALL_FAILED: str = "cover_prompt_ideas_call_failed"

__all__ = [
    "ERR_COVER_PROMPT_IDEAS_UNAVAILABLE",
    "ERR_TOPIC_TOO_SHORT",
    "IDEAS_MAX_TOKENS",
    "IDEAS_TEMPERATURE",
    "IDEAS_TIMEOUT_SECONDS",
    "IDEA_ATTEMPTS",
    "IDEA_FORBIDDEN_CHARS",
    "IDEA_MAX_COUNT",
    "IDEA_MAX_LEN",
    "IDEA_MIN_COUNT",
    "IDEA_MIN_LEN",
    "IDEA_REQUEST_COUNT",
    "KEY_IDEAS",
    "LANGUAGE_BY_LOCALE",
    "LOG_COVER_IDEAS_CALL_FAILED",
    "NO_PALETTE_HINT",
    "PROMPT_COVER_PROMPT_IDEAS",
    "PROMPT_DOMAIN_COVER_PROMPT",
    "TOPIC_MAX_LEN",
    "TOPIC_MIN_LEN",
    "TRACE_AGENT_COVER_PROMPT_IDEAS",
    "TRACE_CONTENT_TYPE_CAROUSEL",
    "TRACE_PHASE_COVER_PROMPT_IDEAS",
    "IdeaLocale",
]
