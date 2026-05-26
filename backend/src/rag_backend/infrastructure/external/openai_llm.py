"""OpenAI LLM service implementation using LangChain."""

from collections.abc import AsyncIterator

from langchain_core.messages import BaseMessage
from langchain_openai import ChatOpenAI

from rag_backend.domain.constants.openai_llm import (
    DEFAULT_MESSAGE_ROLE,
    ROLE_CLASS_MAPPING,
)
from rag_backend.infrastructure.config.settings import Settings

DEFAULT_TEMPERATURE = 0.7


def _to_lc_messages(messages: list[dict[str, str]]) -> list[BaseMessage]:
    """Convert role/content dicts to LangChain message objects."""
    lc_messages: list[BaseMessage] = []
    for msg in messages:
        role = msg.get("role", DEFAULT_MESSAGE_ROLE)
        content = msg.get("content", "")
        message_cls = ROLE_CLASS_MAPPING.get(
            role, ROLE_CLASS_MAPPING[DEFAULT_MESSAGE_ROLE]
        )
        lc_messages.append(message_cls(content=content))
    return lc_messages


class OpenAILLMService:
    """OpenAI implementation of LLMService protocol."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._llm = ChatOpenAI(
            api_key=settings.openai_api_key.get_secret_value(),
            model=settings.openai_model,
            temperature=0.7,
            streaming=True,
            max_retries=3,
        )

    @property
    def chat_model(self) -> ChatOpenAI:
        """Expose the underlying LangChain chat model."""
        return self._llm

    async def generate(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> str:
        """Generate a complete response."""
        lc_messages = _to_lc_messages(messages)

        # Configure temperature and max_tokens if provided
        llm = self._llm
        if temperature != DEFAULT_TEMPERATURE or max_tokens:
            llm = self._llm.with_config(temperature=temperature, max_tokens=max_tokens)

        response = await llm.ainvoke(lc_messages)
        return str(response.content)

    async def generate_stream(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> AsyncIterator[str]:
        """Generate a streaming response."""
        lc_messages = _to_lc_messages(messages)

        # Configure temperature and max_tokens if provided
        llm = self._llm
        if temperature != DEFAULT_TEMPERATURE or max_tokens:
            llm = self._llm.with_config(temperature=temperature, max_tokens=max_tokens)

        # Stream the response
        async for chunk in llm.astream(lc_messages):
            if chunk.content:
                yield str(chunk.content)
