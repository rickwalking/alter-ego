"""Shared helpers for agent chat streaming."""


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


__all__ = ["extract_message_text", "extract_stream_token"]
