"""Role class mapping for LangChain OpenAI message conversion."""

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

ROLE_CLASS_MAPPING: dict[str, type[BaseMessage]] = {
    "system": SystemMessage,
    "assistant": AIMessage,
    "user": HumanMessage,
}

DEFAULT_MESSAGE_ROLE = "user"

__all__ = ["DEFAULT_MESSAGE_ROLE", "ROLE_CLASS_MAPPING"]
