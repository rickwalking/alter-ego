"""OpenAI LLM service implementation using LangChain."""

from collections.abc import AsyncIterator

from langchain_openai import ChatOpenAI

from rag_backend.infrastructure.config.settings import Settings


class OpenAILLMService:
    """OpenAI implementation of LLMService protocol."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._llm = ChatOpenAI(
            api_key=settings.openai_api_key,
            model=settings.openai_model,
            temperature=0.7,
            streaming=True,
        )

    async def generate(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> str:
        """Generate a complete response."""
        from langchain_core.messages import (
            AIMessage,
            HumanMessage,
            SystemMessage,
        )

        # Convert dict messages to LangChain message objects
        lc_messages = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            if role == "system":
                lc_messages.append(SystemMessage(content=content))
            elif role == "assistant":
                lc_messages.append(AIMessage(content=content))
            else:
                lc_messages.append(HumanMessage(content=content))

        # Configure temperature and max_tokens if provided
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
        from langchain_core.messages import (
            AIMessage,
            HumanMessage,
            SystemMessage,
        )

        # Convert dict messages to LangChain message objects
        lc_messages = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            if role == "system":
                lc_messages.append(SystemMessage(content=content))
            elif role == "assistant":
                lc_messages.append(AIMessage(content=content))
            else:
                lc_messages.append(HumanMessage(content=content))

        # Configure temperature and max_tokens if provided
        llm = self._llm
        if temperature != 0.7 or max_tokens:
            llm = self._llm.with_config(temperature=temperature, max_tokens=max_tokens)

        # Stream the response
        async for chunk in llm.astream(lc_messages):
            if chunk.content:
                yield str(chunk.content)
