"""Versioned cover-photo idea prompts (``agents/prompts/cover_prompt/v2/``), trace and model.

The API composition edge injects these into the ideas service, so the application
layer imports neither the prompt registry, the Langfuse adapter nor LangChain.
:class:`CoverIdeasCompletion` binds the ideas' token cap and temperature on the fast
chat model itself. The topic and the palette line are sanitised (angle brackets
and injection phrases stripped), so neither can close the template's data markers.
"""

from __future__ import annotations

from contextlib import AbstractContextManager

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage

from rag_backend.agents.input_sanitizer import sanitize_llm_input
from rag_backend.agents.prompts.registry import render_prompt
from rag_backend.domain.constants.cover_prompt_ideas import (
    IDEA_MAX_LEN,
    IDEA_REQUEST_COUNT,
    IDEAS_MAX_TOKENS,
    IDEAS_TEMPERATURE,
    LANGUAGE_BY_LOCALE,
    PROMPT_COVER_PROMPT_IDEAS,
    PROMPT_COVER_PROMPT_IDEAS_VERSION,
    PROMPT_DOMAIN_COVER_PROMPT,
    TRACE_AGENT_COVER_PROMPT_IDEAS,
    TRACE_CONTENT_TYPE_CAROUSEL,
    TRACE_PHASE_COVER_PROMPT_IDEAS,
    IdeaLocale,
)
from rag_backend.domain.constants.langfuse_tracing import (
    TRACE_FIELD_AGENT_NAME,
    TRACE_FIELD_CONTENT_TYPE,
    TRACE_FIELD_PHASE,
    TRACE_FIELD_USER_ID,
)
from rag_backend.infrastructure.monitoring_langfuse import propagate_attributes


def cover_ideas_prompt(topic: str, palette: str, locale: IdeaLocale) -> str:
    """The prompt asking for cover-photo ideas about ``topic`` in ``palette``."""
    prompt, _ = render_prompt(
        PROMPT_DOMAIN_COVER_PROMPT,
        PROMPT_COVER_PROMPT_IDEAS,
        {
            "topic": sanitize_llm_input(topic),
            "palette": sanitize_llm_input(palette),
            "language": LANGUAGE_BY_LOCALE[locale],
            "count": IDEA_REQUEST_COUNT,
            "max_len": IDEA_MAX_LEN,
        },
        version=PROMPT_COVER_PROMPT_IDEAS_VERSION,
    )
    return prompt


def cover_ideas_trace(user_id: str) -> AbstractContextManager[object]:
    """The Langfuse phase trace of one "Mais ideias" call for ``user_id``."""
    return propagate_attributes(
        metadata={
            TRACE_FIELD_PHASE: TRACE_PHASE_COVER_PROMPT_IDEAS,
            TRACE_FIELD_AGENT_NAME: TRACE_AGENT_COVER_PROMPT_IDEAS,
            TRACE_FIELD_USER_ID: user_id,
            TRACE_FIELD_CONTENT_TYPE: TRACE_CONTENT_TYPE_CAROUSEL,
        },
    )


class CoverIdeasCompletion:
    """The fast chat model with the ideas' token cap and temperature bound."""

    def __init__(self, chat_model: BaseChatModel) -> None:
        self._bound = chat_model.bind(
            temperature=IDEAS_TEMPERATURE, max_tokens=IDEAS_MAX_TOKENS
        )

    async def complete(self, prompt: str) -> str:
        """The model's text answer to ``prompt``."""
        message = await self._bound.ainvoke([HumanMessage(content=prompt)])
        return str(message.content)


__all__ = ["CoverIdeasCompletion", "cover_ideas_prompt", "cover_ideas_trace"]
