"""Shared Deep Agents harness — middleware presets (AE-0248).

Two thin presets over LangChain's built-in middleware so every agent composed
through the harness gets consistent context-window management and (where wanted)
human-in-the-loop tool gating:

- :func:`build_summarization_middleware` caps chat context-window growth by
  summarizing older turns once a message-count threshold is crossed. Chat agents
  adopt this (AE-0248) — it changes observable model context but does **not**
  touch ``message_repository`` persistence.
- :func:`build_human_in_the_loop_middleware` wraps ``HumanInTheLoopMiddleware``
  for tool-approval gates.

Kept minimal and generic: no carousel/chat domain coupling.
"""

from __future__ import annotations

from langchain.agents.middleware import (
    HumanInTheLoopMiddleware,
    SummarizationMiddleware,
)
from langchain.agents.middleware.human_in_the_loop import InterruptOnConfig
from langchain_core.language_models.chat_models import BaseChatModel

# Default summarization trigger/keep: summarize once the window exceeds
# SUMMARIZATION_TRIGGER_MESSAGES, retaining the most recent SUMMARIZATION_KEEP_MESSAGES.
SUMMARIZATION_TRIGGER_MESSAGES = 40
SUMMARIZATION_KEEP_MESSAGES = 20

_TRIGGER_KIND_MESSAGES = "messages"
_KEEP_KIND_MESSAGES = "messages"


def build_summarization_middleware(
    model: BaseChatModel,
) -> SummarizationMiddleware:
    """Build the chat summarization preset (caps context-window growth).

    Triggers a summary once the conversation exceeds
    ``SUMMARIZATION_TRIGGER_MESSAGES`` messages, keeping the most recent
    ``SUMMARIZATION_KEEP_MESSAGES`` verbatim.
    """
    return SummarizationMiddleware(
        model=model,
        trigger=(_TRIGGER_KIND_MESSAGES, SUMMARIZATION_TRIGGER_MESSAGES),
        keep=(_KEEP_KIND_MESSAGES, SUMMARIZATION_KEEP_MESSAGES),
    )


def build_human_in_the_loop_middleware(
    interrupt_on: dict[str, bool | InterruptOnConfig],
) -> HumanInTheLoopMiddleware:
    """Build a human-in-the-loop tool-approval preset for the given tools."""
    return HumanInTheLoopMiddleware(interrupt_on=interrupt_on)


__all__ = [
    "SUMMARIZATION_KEEP_MESSAGES",
    "SUMMARIZATION_TRIGGER_MESSAGES",
    "build_human_in_the_loop_middleware",
    "build_summarization_middleware",
]
