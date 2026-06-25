"""Chat LLM service implementation using LangChain.

Provider-agnostic despite the legacy ``AnthropicLLMService`` name (AE-0285): the
underlying chat model is selected by ``settings.llm_provider`` via
``build_chat_model`` (Anthropic Claude or GLM 5.2 over the OpenCode Go endpoint).
"""

from collections.abc import AsyncIterator, Callable

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

from rag_backend.domain.constants import ROLE_ASSISTANT, ROLE_SYSTEM, ROLE_USER
from rag_backend.infrastructure.config.settings import Settings
from rag_backend.infrastructure.external.chat_model_factory import build_chat_model

# Role → LangChain message constructor dispatch.
_ROLE_TO_MESSAGE: dict[str, Callable[[str], BaseMessage]] = {
    ROLE_SYSTEM: lambda content: SystemMessage(content=content),
    ROLE_ASSISTANT: lambda content: AIMessage(content=content),
    ROLE_USER: lambda content: HumanMessage(content=content),
}

DEFAULT_TEMPERATURE = 0.7


class AnthropicLLMService:
    """LLMService implementation; the provider is chosen by ``llm_provider``."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._llm = build_chat_model(settings)

    @property
    def chat_model(self) -> BaseChatModel:
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
