"""Shared helpers for agent chat streaming."""

from collections.abc import Sequence

from langchain_core.messages import AIMessage
from langchain_core.runnables.schema import StreamEvent

from rag_backend.domain.types import ChatEvent

_EVENT_TOOL_END = "on_tool_end"
_EVENT_MODEL_STREAM = "on_chat_model_stream"
_CHAT_EVENT_TOOL_RESULT = "tool_result"
_CHAT_EVENT_STREAMED_TEXT = "token"


def extract_stream_token(content: object) -> str:
    """Extract text token from Anthropic/OpenAI stream chunk content."""
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        token = ""
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                token += str(block.get("text", ""))
        return token

    return ""


def extract_message_text(raw: object) -> str:
    """Extract plain text from a LangChain AIMessage content payload."""
    if isinstance(raw, str):
        return raw

    if isinstance(raw, list):
        response = ""
        for block in raw:
            if isinstance(block, dict) and block.get("type") == "text":
                response += str(block.get("text", ""))
        return response

    return ""


def chat_event_from_stream(event: StreamEvent) -> ChatEvent | None:
    """Map one ``astream_events`` (v2) event to a chat event, or None to skip it.

    A finished tool becomes a ``tool_result``; a model stream chunk with text
    becomes a ``token``; everything else is skipped.
    """
    name = event.get("event")
    data = event.get("data", {})
    if name == _EVENT_TOOL_END:
        output = data.get("output")
        if output is None:
            return None
        return {
            "type": _CHAT_EVENT_TOOL_RESULT,
            "tool": event.get("name", ""),
            "result": output,
        }
    if name != _EVENT_MODEL_STREAM:
        return None
    chunk = data.get("chunk")
    content = getattr(chunk, "content", None) if chunk is not None else None
    token = extract_stream_token(content) if content else ""
    return {"type": _CHAT_EVENT_STREAMED_TEXT, "content": token} if token else None


def is_token_event(event: ChatEvent) -> bool:
    """True for a streamed text token (the part that builds the reply)."""
    return event.get("type") == _CHAT_EVENT_STREAMED_TEXT


def last_ai_message_text(messages: Sequence[object]) -> str:
    """The text of the newest AI message that has any, else ""."""
    for message in reversed(messages):
        if isinstance(message, AIMessage) and message.content:
            text = extract_message_text(message.content)
            if text:
                return text
    return ""


__all__ = [
    "chat_event_from_stream",
    "extract_message_text",
    "extract_stream_token",
    "is_token_event",
    "last_ai_message_text",
]
