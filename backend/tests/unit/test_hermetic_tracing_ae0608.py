"""The test run has no span exporter and no way to reach Langfuse.

Each test pins one of the switches set at the top of ``tests/conftest.py``. Nothing here
opens a socket: the span processor and tracer provider are replaced wherever one
could be built, and the base URL is a closed local port.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from langfuse import Langfuse
from langfuse._client import resource_manager
from opentelemetry import trace
from pydantic import SecretStr

from rag_backend import monitoring_langfuse as root_monitoring
from rag_backend.infrastructure import langfuse_client
from rag_backend.infrastructure.config.settings import Settings

_PUBLIC_KEY = "pk-lf-hermetic-probe"
_SECRET_KEY = "sk-lf-hermetic-probe"
_CLOSED_PORT_URL = "http://127.0.0.1:9"
_TRACING_SWITCH = "LANGFUSE_TRACING_ENABLED"


@pytest.fixture
def span_processor(monkeypatch: pytest.MonkeyPatch) -> Iterator[MagicMock]:
    """Stand in for the exporter's processor and drop the SDK singleton afterwards."""
    processor = MagicMock(name="LangfuseSpanProcessor")
    monkeypatch.setattr(resource_manager, "LangfuseSpanProcessor", processor)
    monkeypatch.setattr(resource_manager, "_init_tracer_provider", MagicMock())
    yield processor
    instance = resource_manager.LangfuseResourceManager._instances.pop(
        _PUBLIC_KEY, None
    )
    if instance is not None:
        instance.shutdown()


def _real_client() -> Langfuse:
    return Langfuse(
        public_key=_PUBLIC_KEY, secret_key=_SECRET_KEY, base_url=_CLOSED_PORT_URL
    )


def test_a_client_with_real_keys_gets_no_exporter(span_processor: MagicMock) -> None:
    """Even explicit keys cannot start an export in the test run."""
    client = _real_client()

    span_processor.assert_not_called()
    assert isinstance(client._otel_tracer, trace.NoOpTracer)


def test_the_same_client_exports_when_the_switch_is_gone(
    span_processor: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The check above would fail: without the switch the exporter is installed."""
    monkeypatch.delenv(_TRACING_SWITCH)

    _real_client()

    span_processor.assert_called_once()


def test_startup_settings_ignore_keys_in_a_dotenv_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A developer's real keys in ``.env`` never reach the app under test."""
    dotenv = tmp_path / ".env"
    dotenv.write_text(
        f"LANGFUSE_PUBLIC_KEY={_PUBLIC_KEY}\n"
        f"LANGFUSE_SECRET_KEY={_SECRET_KEY}\n"
        "OTEL_ENABLED=true\n"
    )
    constructor = MagicMock(name="Langfuse")
    monkeypatch.setattr(langfuse_client, "Langfuse", constructor)
    monkeypatch.setattr(langfuse_client, "LANGFUSE_CLIENT", None)

    settings = Settings(
        _env_file=dotenv, secret_key="s" * 40, anon_secret_key="a" * 40
    )
    secret = settings.langfuse_secret_key or SecretStr("")

    assert settings.otel_enabled is False
    assert (
        langfuse_client.init_langfuse(
            settings.langfuse_public_key,
            secret.get_secret_value(),
            settings.langfuse_host,
        )
        is None
    )
    constructor.assert_not_called()


def test_a_test_that_configures_langfuse_leaks_no_keys(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Fake keys given to init stay out of the environment later startups read."""
    monkeypatch.setattr(root_monitoring, "Langfuse", MagicMock())
    monkeypatch.setattr(root_monitoring, "CallbackHandler", MagicMock())
    monkeypatch.setattr(root_monitoring, "_langfuse_client", None)
    monkeypatch.setattr(root_monitoring, "_langfuse_handler", None)

    root_monitoring.init_langfuse(_PUBLIC_KEY, _SECRET_KEY, _CLOSED_PORT_URL)

    assert os.environ["LANGFUSE_PUBLIC_KEY"] == ""
    assert os.environ["LANGFUSE_SECRET_KEY"] == ""
