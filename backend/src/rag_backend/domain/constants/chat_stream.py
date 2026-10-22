"""SSE constants for chat streaming service."""

from __future__ import annotations

SSE_EVENT_TOKEN = "token"  # noqa: S105  — SSE event type name, not a password token
SSE_EVENT_SOURCES = "sources"
SSE_EVENT_COMPLETE = "complete"
SSE_EVENT_ERROR = "error"
SSE_EVENT_TOOL_RESULT = "tool_result"
SSE_KEEP_ALIVE_INTERVAL_SECONDS = 15
ERR_EMPTY_MESSAGE = "Message content cannot be empty"
CHAT_FAILED_REPLY = "Sorry, I couldn't answer that one. Please try again."
ALTER_EGO_RECURSION_LIMIT = 25
ALTER_EGO_SEARCH_BUDGET = 3
SEARCH_NO_RESULTS = "No relevant documents found."
SEARCH_BUDGET_EXHAUSTED = (
    "Search limit reached for this question. Answer with what you already found."
)
NO_KNOWLEDGE_REPLY_EN = (
    "I don't have that in my knowledge yet, so I'd rather not guess. "
    "Ask me something else about my work?"
)
NO_KNOWLEDGE_REPLY_PT = (
    "Ainda não tenho isso no meu conhecimento, então prefiro não chutar. "
    "Quer perguntar outra coisa sobre o meu trabalho?"
)
