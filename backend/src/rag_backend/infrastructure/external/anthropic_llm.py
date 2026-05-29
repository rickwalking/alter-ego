"""Anthropic LLM service implementation using LangChain."""

from collections.abc import AsyncIterator, Callable

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

from rag_backend.domain.constants import ROLE_ASSISTANT, ROLE_SYSTEM, ROLE_USER
from rag_backend.infrastructure.config.settings import Settings

# Role → LangChain message constructor dispatch.
_ROLE_TO_MESSAGE: dict[str, Callable[[str], BaseMessage]] = {
    ROLE_SYSTEM: lambda content: SystemMessage(content=content),
    ROLE_ASSISTANT: lambda content: AIMessage(content=content),
    ROLE_USER: lambda content: HumanMessage(content=content),
}

DEFAULT_TEMPERATURE = 0.7


class AnthropicLLMService:
    """Anthropic implementation of the LLMService protocol."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._llm = ChatAnthropic(
            api_key=settings.anthropic_api_key.get_secret_value(),
            model=settings.anthropic_model,
            temperature=0.7,
            streaming=True,
            # Bilingual content synthesis emits PT + EN slide arrays plus
            # two full blog posts — 8K default was cutting the JSON off
            # mid-string. 32K gives plenty of headroom for Sonnet/Opus.
            max_tokens=32000,
            max_retries=3,
        )

    @property
    def chat_model(self) -> ChatAnthropic:
        """Expose the underlying LangChain chat model."""
        return self._llm

    @staticmethod
    def _to_lc_messages(
        messages: list[dict[str, str]],
    ) -> list[BaseMessage]:
        return [
            _ROLE_TO_MESSAGE.get(
                msg.get("role", ROLE_USER), _ROLE_TO_MESSAGE[ROLE_USER]
            )(msg.get("content", ""))
            for msg in messages
        ]

    async def generate(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> str:
        """Generate a complete response."""
        lc_messages = self._to_lc_messages(messages)

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
        lc_messages = self._to_lc_messages(messages)

        llm = self._llm
        if temperature != DEFAULT_TEMPERATURE or max_tokens:
            llm = self._llm.with_config(temperature=temperature, max_tokens=max_tokens)

        async for chunk in llm.astream(lc_messages):
            if chunk.content:
                yield str(chunk.content)
