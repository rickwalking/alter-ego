"""Role class mapping for LangChain messages."""

ROLE_CLASS_MAPPING: dict[str, type] = {
    "system": "SystemMessage",
    "assistant": "AIMessage",
    "user": "HumanMessage",
}
