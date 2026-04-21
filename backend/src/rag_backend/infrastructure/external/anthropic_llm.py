"""Anthropic LLM service implementation using LangChain."""

from collections.abc import AsyncIterator

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from rag_backend.infrastructure.config.settings import Settings


class AnthropicLLMService:
    """Anthropic implementation of the LLMService protocol."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._llm = ChatAnthropic(
            api_key=settings.anthropic_api_key,
            model=settings.anthropic_model,
            temperature=0.7,
            streaming=True,
        )

    @staticmethod
    def _to_lc_messages(messages: list[dict[str, str]]) -> list[SystemMessage | HumanMessage | AIMessage]:
        lc_messages: list[SystemMessage | HumanMessage | AIMessage] = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                lc_messages.append(SystemMessage(content=content))
            elif role == "assistant":
                lc_messages.append(AIMessage(content=content))
            else:
                lc_messages.append(HumanMessage(content=content))
        return lc_messages

    async def generate(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> str:
        """Generate a complete response."""
        lc_messages = self._to_lc_messages(messages)

        llm = self._llm
        if temperature != 0.7 or max_tokens:
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
        if temperature != 0.7 or max_tokens:
            llm = self._llm.with_config(temperature=temperature, max_tokens=max_tokens)

        async for chunk in llm.astream(lc_messages):
            if chunk.content:
                yield str(chunk.content)
