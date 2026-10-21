"""Shared chat-stream event mapping (AE-0446: one copy for both chat agents)."""

from types import SimpleNamespace

from langchain_core.messages import AIMessage, HumanMessage

from rag_backend.agents.chat_streaming import (
    chat_event_from_stream,
    is_token_event,
    last_ai_message_text,
)


def _event(name: str, **data: object) -> dict[str, object]:
    return {"event": name, "name": "search", "data": data}


# Scenario: a finished tool streams its result to the client.
def test_tool_end_becomes_a_tool_result() -> None:
    event = chat_event_from_stream(_event("on_tool_end", output="3 docs"))
    assert event == {"type": "tool_result", "tool": "search", "result": "3 docs"}
    assert event is not None and not is_token_event(event)


def test_tool_end_without_output_is_skipped() -> None:
    assert chat_event_from_stream(_event("on_tool_end", output=None)) is None


# Scenario: model text streams token by token.
def test_model_chunk_text_becomes_a_token() -> None:
    chunk = SimpleNamespace(content=[{"type": "text", "text": "Olá"}])
    event = chat_event_from_stream(_event("on_chat_model_stream", chunk=chunk))
    assert event == {"type": "token", "content": "Olá"}
    assert event is not None and is_token_event(event)


def test_empty_chunks_and_other_events_are_skipped() -> None:
    empty = SimpleNamespace(content="")
    assert chat_event_from_stream(_event("on_chat_model_stream", chunk=empty)) is None
    assert chat_event_from_stream(_event("on_chat_model_stream")) is None
    assert chat_event_from_stream(_event("on_chain_start")) is None


# Scenario: a non-streamed reply is the newest AI message with text.
def test_last_ai_message_text_skips_empty_and_human_messages() -> None:
    messages = [
        AIMessage(content="first"),
        HumanMessage(content="question"),
        AIMessage(content=[{"type": "text", "text": "final"}]),
        AIMessage(content=""),
    ]
    assert last_ai_message_text(messages) == "final"
    assert last_ai_message_text([HumanMessage(content="only human")]) == ""
