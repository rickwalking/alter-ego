"""Unit tests for shared agent chat streaming helpers."""

from rag_backend.agents.chat_streaming import extract_message_text, extract_stream_token


class TestExtractStreamToken:
    def test_extracts_plain_string_content(self) -> None:
        assert extract_stream_token("hello") == "hello"

    def test_extracts_text_blocks_from_list_content(self) -> None:
        content = [{"type": "text", "text": "hello"}, {"type": "tool_use", "id": "1"}]
        assert extract_stream_token(content) == "hello"

    def test_returns_empty_string_for_unknown_content(self) -> None:
        assert extract_stream_token(None) == ""


class TestExtractMessageText:
    def test_extracts_plain_string(self) -> None:
        assert extract_message_text("complete response") == "complete response"

    def test_extracts_text_blocks(self) -> None:
        content = [
            {"type": "text", "text": "part one"},
            {"type": "text", "text": " part two"},
        ]
        assert extract_message_text(content) == "part one part two"
