"""Recording fake chat models for the AE-0391 routing / parallel-drafting tests.

A real ``BaseChatModel`` (not a MagicMock) so ``RoutedChatModel`` exercises the
genuine LangChain ``ainvoke`` path: callbacks, run tags and bound kwargs.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field

from langchain_core.callbacks import (
    AsyncCallbackManagerForLLMRun,
    CallbackManagerForLLMRun,
)
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import ConfigDict, Field


@dataclass
class CallLog:
    """Shared across fakes: which model ran, with which tags, how concurrently."""

    models: list[str] = field(default_factory=list)
    tags: list[list[str]] = field(default_factory=list)
    kwargs: list[dict[str, object]] = field(default_factory=list)
    in_flight: int = 0
    max_in_flight: int = 0


def _prompt_text(messages: list[BaseMessage]) -> str:
    return "\n".join(str(message.content) for message in messages)


class FakeChat(BaseChatModel):
    """Answers via ``reply(prompt)``; raises ``error`` when set."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    model_name: str = "fake-model"
    reply: Callable[[str], str] = Field(default=lambda _prompt: "ok")
    error: Exception | None = None
    delay: float = 0.0
    log: CallLog = Field(default_factory=CallLog)

    @property
    def _llm_type(self) -> str:
        return "fake-chat"

    async def _agenerate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: AsyncCallbackManagerForLLMRun | None = None,
        **kwargs: object,
    ) -> ChatResult:
        self.log.models.append(self.model_name)
        self.log.tags.append(list(run_manager.tags) if run_manager else [])
        self.log.kwargs.append(dict(kwargs))
        self.log.in_flight += 1
        self.log.max_in_flight = max(self.log.max_in_flight, self.log.in_flight)
        try:
            await asyncio.sleep(self.delay)
            if self.error is not None:
                raise self.error
            text = self.reply(_prompt_text(messages))
        finally:
            self.log.in_flight -= 1
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=text))])

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: object,
    ) -> ChatResult:
        self.log.models.append(self.model_name)
        text = self.reply(_prompt_text(messages))
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=text))])


class StatusError(Exception):
    """An SDK-style API error carrying an HTTP ``status_code``."""

    def __init__(self, status_code: int) -> None:
        super().__init__(f"HTTP {status_code}")
        self.status_code = status_code
