"""Chat model served by the OpenCode sidecar (``opencode serve``).

OpenCode's free models only answer requests made from within OpenCode, and
OpenCode is a coding agent with shell and file tools. The sidecar runs it in
its own container with no secrets, a read-only root filesystem and a
throwaway working directory, so a prompt that steers the agent can only touch
that container. This model is its HTTP client: one session per call, the
system messages as ``system``, the rest as one text part, Basic auth.
"""

from __future__ import annotations

import asyncio
import json

import httpx
from langchain_core.callbacks import (
    AsyncCallbackManagerForLLMRun,
    CallbackManagerForLLMRun,
)
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, SystemMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import ConfigDict, Field, PrivateAttr, SecretStr

from rag_backend.infrastructure.config.llm_queue_constants import (
    DEFAULT_SIDECAR_CONCURRENCY,
    DEFAULT_SIDECAR_TIMEOUT_SECONDS,
    ERR_SIDECAR_EMPTY,
    ERR_SIDECAR_SYNC,
    SIDECAR_BASIC_USER,
    SIDECAR_PART_TEXT,
    SIDECAR_PATH_MESSAGE,
    SIDECAR_PATH_SESSION,
    SIDECAR_PATH_SESSION_ID,
    SIDECAR_PROVIDER_SEPARATOR,
    SIDECAR_SESSION_TITLE,
)
from rag_backend.infrastructure.llm.model_breaker import EmptyModelAnswerError

_LLM_TYPE = "opencode-sidecar"
_ROLE_PREFIX = {"human": "", "ai": "Assistant: "}
_FIELD_INFO = "info"
_FIELD_ERROR = "error"
_FIELD_PARTS = "parts"
_FIELD_DATA = "data"
_FIELD_STATUS = "statusCode"
_FIELD_MESSAGE = "message"
_FIELD_RESPONSE_BODY = "responseBody"


class OpenCodeSidecarError(RuntimeError):
    """The sidecar (or the model behind it) refused or failed the call."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class OpenCodeSidecarChatModel(BaseChatModel):
    """``<provider>/<model>`` through the OpenCode sidecar's HTTP API."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    model_name: str
    base_url: str
    password: SecretStr = SecretStr("")
    timeout_seconds: float = DEFAULT_SIDECAR_TIMEOUT_SECONDS
    concurrency: int = Field(default=DEFAULT_SIDECAR_CONCURRENCY, ge=1)
    _gate: asyncio.Semaphore | None = PrivateAttr(default=None)

    @property
    def _llm_type(self) -> str:
        return _LLM_TYPE

    async def _agenerate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: AsyncCallbackManagerForLLMRun | None = None,
        **kwargs: object,
    ) -> ChatResult:
        """Ask the sidecar; sampling knobs are the sidecar's own, so they are ignored."""
        del stop, run_manager, kwargs
        async with self._semaphore():
            text = await self._ask(_body(self.model_name, messages))
        message = AIMessage(content=text)
        return ChatResult(generations=[ChatGeneration(message=message)])

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: object,
    ) -> ChatResult:
        raise NotImplementedError(ERR_SIDECAR_SYNC)

    def _semaphore(self) -> asyncio.Semaphore:
        if self._gate is None:
            self._gate = asyncio.Semaphore(self.concurrency)
        return self._gate

    async def _ask(self, body: dict[str, object]) -> str:
        auth = (SIDECAR_BASIC_USER, self.password.get_secret_value())
        async with httpx.AsyncClient(
            base_url=self.base_url, auth=auth, timeout=self.timeout_seconds
        ) as client:
            session = await _post_json(client, SIDECAR_PATH_SESSION, _session_body())
            session_id = str(session.get("id", ""))
            try:
                path = SIDECAR_PATH_MESSAGE.format(session_id=session_id)
                return _answer_text(await _post_json(client, path, body))
            finally:
                await _delete_quietly(client, session_id)


def _session_body() -> dict[str, object]:
    return {"title": SIDECAR_SESSION_TITLE}


def _body(model_name: str, messages: list[BaseMessage]) -> dict[str, object]:
    provider, _, model_id = model_name.partition(SIDECAR_PROVIDER_SEPARATOR)
    system = "\n\n".join(
        str(m.content) for m in messages if isinstance(m, SystemMessage)
    )
    text = "\n\n".join(
        f"{_ROLE_PREFIX.get(m.type, '')}{m.content}"
        for m in messages
        if not isinstance(m, SystemMessage)
    )
    body: dict[str, object] = {
        "model": {"providerID": provider, "modelID": model_id},
        "parts": [{"type": SIDECAR_PART_TEXT, "text": text}],
    }
    if system:
        body["system"] = system
    return body


async def _post_json(
    client: httpx.AsyncClient, path: str, body: dict[str, object]
) -> dict[str, object]:
    response = await client.post(path, json=body)
    if response.status_code >= httpx.codes.BAD_REQUEST:
        raise OpenCodeSidecarError(response.text[:500], response.status_code)
    data = response.json()
    return data if isinstance(data, dict) else {}


async def _delete_quietly(client: httpx.AsyncClient, session_id: str) -> None:
    if not session_id:
        return
    try:
        await client.delete(SIDECAR_PATH_SESSION_ID.format(session_id=session_id))
    except httpx.HTTPError:
        return


def _answer_text(reply: dict[str, object]) -> str:
    info = reply.get(_FIELD_INFO)
    error = info.get(_FIELD_ERROR) if isinstance(info, dict) else None
    if isinstance(error, dict):
        raise _model_error(error)
    parts = reply.get(_FIELD_PARTS)
    texts = [
        str(part.get(SIDECAR_PART_TEXT, ""))
        for part in (parts if isinstance(parts, list) else [])
        if isinstance(part, dict) and part.get("type") == SIDECAR_PART_TEXT
    ]
    text = "".join(texts).strip()
    if not text:
        raise EmptyModelAnswerError(ERR_SIDECAR_EMPTY)
    return text


def _model_error(error: dict[str, object]) -> OpenCodeSidecarError:
    """The model's error as raised, keeping the provider's status and body."""
    data = error.get(_FIELD_DATA)
    details = data if isinstance(data, dict) else {}
    status = details.get(_FIELD_STATUS)
    message = (
        " ".join(
            str(details.get(key, ""))
            for key in (_FIELD_MESSAGE, _FIELD_RESPONSE_BODY)
            if details.get(key)
        )
        or json.dumps(error)[:500]
    )
    return OpenCodeSidecarError(message, status if isinstance(status, int) else None)


__all__ = ["OpenCodeSidecarChatModel", "OpenCodeSidecarError"]
