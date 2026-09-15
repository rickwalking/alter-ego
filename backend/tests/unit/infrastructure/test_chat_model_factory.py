"""Unit tests for the provider-agnostic chat-model factory (AE-0285, AE-0330).

Scenarios: see tests/features/llm_provider_toggle.feature
"""

import json
import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from rag_backend.infrastructure.config.settings import Settings
from rag_backend.infrastructure.external.chat_model_factory import build_chat_model

SESSION_HEADER = "x-opencode-session"
USER_AGENT_HEADER = "user-agent"


def _settings(
    *,
    llm_provider: str = "glm",
    glm_api_key: SecretStr = SecretStr(""),
    glm_model: str = "glm-5.3",
    glm_base_url: str = "https://opencode.ai/zen/go/v1",
) -> Settings:
    return Settings(
        anthropic_api_key=SecretStr("anthropic-key"),
        anthropic_model="claude-sonnet-4-6",
        llm_provider=llm_provider,
        glm_api_key=glm_api_key,
        glm_model=glm_model,
        glm_base_url=glm_base_url,
    )


def test_anthropic_provider_builds_chat_anthropic() -> None:
    # Scenario: Anthropic provider selected
    model = build_chat_model(_settings(llm_provider="anthropic"))
    assert isinstance(model, ChatAnthropic)
    assert model.model == "claude-sonnet-4-6"


def test_glm_provider_with_key_builds_openai_compatible_client() -> None:
    # Scenario: GLM provider selected with a key
    model = build_chat_model(
        _settings(
            llm_provider="glm",
            glm_api_key=SecretStr("glm-key"),
            glm_model="glm-5.3",
            glm_base_url="https://opencode.ai/zen/go/v1",
        )
    )
    assert isinstance(model, ChatOpenAI)
    assert model.model_name == "glm-5.3"


def test_glm_provider_without_key_falls_back_to_anthropic() -> None:
    # Scenario: GLM selected but no key (CI / prod not yet configured)
    model = build_chat_model(_settings(llm_provider="glm", glm_api_key=SecretStr("")))
    assert isinstance(model, ChatAnthropic)


def test_shipped_default_model_is_glm_5_3() -> None:
    # AE-0330: 5.2 returned empty content after spending 31999 of 32000 tokens
    # reasoning, failing a live carousel phase. Pin the default so the move to
    # 5.3 cannot be reverted silently.
    assert (
        Settings(
            anthropic_api_key=SecretStr("a"),
            secret_key=SecretStr("s"),
            anon_secret_key=SecretStr("s"),
        ).glm_model
        == "glm-5.3"
    )


def test_default_provider_is_glm_but_safe_without_a_key() -> None:
    # The shipped default is "glm"; with no GLM key it must not break — it
    # degrades to Anthropic so CI and an unconfigured prod keep working.
    settings = _settings()
    assert settings.llm_provider == "glm"
    assert isinstance(build_chat_model(settings), ChatAnthropic)


class _CapturedRequests(list[dict[str, str]]):
    """Headers of every request a stub OpenCode endpoint received."""


def _stub_handler(captured: _CapturedRequests) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            captured.append({k.lower(): v for k, v in self.headers.items()})
            chunk = json.dumps({
                "id": "stub",
                "object": "chat.completion.chunk",
                "created": 0,
                "model": "glm-5.3",
                "choices": [
                    {
                        "index": 0,
                        "finish_reason": "stop",
                        "delta": {"role": "assistant", "content": "ok"},
                    }
                ],
            })
            body = f"data: {chunk}\n\ndata: [DONE]\n\n".encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args: object) -> None:
            """Silence the stdlib access log."""

    return Handler


@pytest.fixture
def opencode_stub() -> Iterator[tuple[str, _CapturedRequests]]:
    """A local stand-in for the OpenCode Go endpoint that records its requests."""
    captured = _CapturedRequests()
    server = HTTPServer(("127.0.0.1", 0), _stub_handler(captured))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}/v1", captured
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def _glm_settings(base_url: str) -> Settings:
    return _settings(
        llm_provider="glm",
        glm_api_key=SecretStr("glm-key"),
        glm_base_url=base_url,
    )


async def test_glm_request_carries_the_opencode_session_header(
    opencode_stub: tuple[str, _CapturedRequests],
) -> None:
    # Scenario: GLM requests carry the OpenCode session header (AE-0330)
    # Without it OpenCode Go answers 400 MissingSessionID, which the
    # workflow-start route surfaced as 503 provider_unavailable in prod.
    base_url, captured = opencode_stub
    settings = _glm_settings(base_url)

    await build_chat_model(settings).ainvoke("hi")

    assert len(captured) == 1
    headers = captured[0]
    assert headers[SESSION_HEADER].startswith("alter-ego-")
    assert headers[USER_AGENT_HEADER] == f"alter-ego/{settings.app_version}"


async def test_session_id_is_stable_per_client_and_unique_across_clients(
    opencode_stub: tuple[str, _CapturedRequests],
) -> None:
    # Scenario: the session id is stable for the life of a client (AE-0330)
    base_url, captured = opencode_stub
    model = build_chat_model(_glm_settings(base_url))

    await model.ainvoke("first")
    await model.ainvoke("second")
    await build_chat_model(_glm_settings(base_url)).ainvoke("other client")

    first, second, other = (headers[SESSION_HEADER] for headers in captured)
    assert first == second
    assert other != first


def test_opencode_headers_do_not_leak_onto_anthropic() -> None:
    # Scenario: the OpenCode headers do not leak onto Anthropic (AE-0330)
    model = build_chat_model(_settings(llm_provider="anthropic"))
    assert isinstance(model, ChatAnthropic)
    assert SESSION_HEADER not in {key.lower() for key in (model.default_headers or {})}
