"""Chat LLM service implementation using LangChain.

Provider-agnostic despite the legacy ``AnthropicLLMService`` name: the
underlying chat model is selected by ``settings.llm_provider`` via
``build_chat_model`` (Anthropic Claude or GLM 5.2 over the OpenCode Go endpoint).

The temperature is bound on the model, so it reaches the request; ``with_config``
would keep it in the run config. There is no ``max_tokens`` argument: every model
here spends its output budget on reasoning before it answers, so a cap below the
factory's 32000 can leave no visible answer at all.
"""

from collections.abc import AsyncIterator, Callable
from contextlib import AbstractContextManager, nullcontext

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

from rag_backend.application.services.carousel.editorial_workflow_types import (
    ChatModelRoles,
)
from rag_backend.domain.constants import ROLE_ASSISTANT, ROLE_SYSTEM, ROLE_USER
from rag_backend.domain.constants.langfuse_tracing import (
    TRACE_FIELD_AGENT_NAME,
    TRACE_FIELD_CONTENT_TYPE,
    TRACE_FIELD_PHASE,
    TRACE_FIELD_PROJECT_ID,
    TRACE_FIELD_USER_ID,
)
from rag_backend.domain.protocols import LlmCallTrace
from rag_backend.infrastructure.config.settings import Settings
from rag_backend.infrastructure.external.chat_model_factory import (
    build_chat_model,
    build_role_models,
)
from rag_backend.infrastructure.external.routed_chat_model import (
    EmptyLLMResponseError,
    model_id_of,
)
from rag_backend.infrastructure.monitoring_langfuse import (
    get_langfuse_runnable_config,
    propagate_attributes,
)

_ROLE_TO_MESSAGE: dict[str, Callable[[str], BaseMessage]] = {
    ROLE_SYSTEM: lambda content: SystemMessage(content=content),
    ROLE_ASSISTANT: lambda content: AIMessage(content=content),
    ROLE_USER: lambda content: HumanMessage(content=content),
}


def _call_scope(trace: LlmCallTrace | None) -> AbstractContextManager[object]:
    """The phase ``trace`` names; a call without one stays in the enclosing phase."""
    if trace is None:
        return nullcontext()
    return propagate_attributes(
        metadata={
            TRACE_FIELD_PROJECT_ID: trace.project_id,
            TRACE_FIELD_USER_ID: trace.user_id,
            TRACE_FIELD_PHASE: trace.phase,
            TRACE_FIELD_AGENT_NAME: trace.agent_name,
            TRACE_FIELD_CONTENT_TYPE: trace.content_type,
        },
    )


class AnthropicLLMService:
    """LLMService implementation; the provider is chosen by ``llm_provider``."""

    def __init__(self, settings: Settings, role: str | None = None) -> None:
        """Build the chat model; a ``role`` (reasoning/fast) routes calls to its model.

        With a role the calls get that role's model plus the fallback; ``None`` keeps
        the single chat model.
        """
        self._settings = settings
        self._llm = build_chat_model(settings, role)
        self._role_models: ChatModelRoles | None = None

    @property
    def chat_model(self) -> BaseChatModel:
        """Expose the underlying LangChain chat model."""
        return self._llm

    @property
    def role_models(self) -> ChatModelRoles:
        """The carousel pipeline's reasoning + fast models (built once)."""
        if self._role_models is None:
            self._role_models = build_role_models(self._settings)
        return self._role_models

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
        trace: LlmCallTrace | None = None,
    ) -> str:
        """Generate a complete response, recorded as a Langfuse generation.

        An answer with no visible text raises ``EmptyLLMResponseError``: a model
        with a fallback has already tried it, and one without has nothing to try.
        """
        with _call_scope(trace):
            response = await self._llm.bind(temperature=temperature).ainvoke(
                self._to_lc_messages(messages), get_langfuse_runnable_config()
            )
            answer = str(response.content)
            if not answer.strip():
                raise EmptyLLMResponseError(model_id_of(self._llm))
        return answer

    async def generate_stream(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
    ) -> AsyncIterator[str]:
        """Generate a streaming response, recorded as a Langfuse generation."""
        async for chunk in self._llm.bind(temperature=temperature).astream(
            self._to_lc_messages(messages), get_langfuse_runnable_config()
        ):
            if chunk.content:
                yield str(chunk.content)
