"""Asynchronous Langfuse startup authentication checks with safe diagnostics.

Feature: backend/tests/features/langfuse_auth_check_ae0561.feature
"""

from __future__ import annotations

import asyncio
import threading
from unittest.mock import MagicMock

import httpx
import pytest
from langfuse import Langfuse
from langfuse.api.resources.commons.errors.unauthorized_error import UnauthorizedError
from pydantic import SecretStr
from structlog.testing import capture_logs

from rag_backend.bootstrap import observability
from rag_backend.infrastructure import langfuse_client
from rag_backend.infrastructure.config.settings import Settings

_HOST = "https://cloud.langfuse.com"
_PUBLIC_KEY = "pk-lf-planted-public"
_SECRET_KEY = "sk-lf-planted-secret"
_CREDENTIAL_URL = f"https://{_PUBLIC_KEY}:{_SECRET_KEY}@cloud.langfuse.com"


def _settings() -> Settings:
    return Settings(
        _env_file=None,
        secret_key="s" * 40,
        anon_secret_key="a" * 40,
        langfuse_public_key=_PUBLIC_KEY,
        langfuse_secret_key=SecretStr(_SECRET_KEY),
        langfuse_host=_HOST,
    )


def _auth_events(logs: list[dict[str, object]]) -> list[dict[str, object]]:
    return [entry for entry in logs if str(entry["event"]).startswith("langfuse_auth_")]


def _assert_safe(logs: list[dict[str, object]]) -> None:
    rendered = repr(logs)
    for secret in (_PUBLIC_KEY, _SECRET_KEY, _CREDENTIAL_URL, "Authorization"):
        assert secret not in rendered
    for entry in logs:
        assert "exception" not in entry
        assert "exc_info" not in entry
        assert "traceback" not in entry


async def _run_auth_check(client: Langfuse) -> list[dict[str, object]]:
    with capture_logs() as logs:
        task = langfuse_client.schedule_langfuse_auth_check(client, _HOST)
        await asyncio.wait_for(task, 1)
    return logs


async def test_valid_credentials_do_not_delay_startup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Scenario: Valid Langfuse credentials log success without delaying startup"""
    client = MagicMock(spec=Langfuse)
    started = threading.Event()
    release = threading.Event()

    def blocked_auth_check() -> bool:
        started.set()
        release.wait(2)
        return True

    client.auth_check.side_effect = blocked_auth_check
    monkeypatch.setattr(observability, "setup_logging", MagicMock())
    monkeypatch.setattr(observability, "init_langsmith", MagicMock())
    monkeypatch.setattr(observability, "init_opentelemetry", MagicMock())
    monkeypatch.setattr(observability, "init_langfuse", lambda *_: client)
    scheduled: list[asyncio.Task[None]] = []
    schedule = langfuse_client.schedule_langfuse_auth_check

    def capture_task(client_arg: Langfuse, host: str) -> asyncio.Task[None]:
        task = schedule(client_arg, host)
        scheduled.append(task)
        return task

    monkeypatch.setattr(observability, "schedule_langfuse_auth_check", capture_task)
    with capture_logs() as logs:
        observability.init_observability(_settings())
        assert len(scheduled) == 1
        assert not scheduled[0].done()
        release.set()
        await asyncio.wait_for(scheduled[0], 1)
    assert started.is_set()
    assert client.auth_check.call_count == 1
    events = _auth_events(logs)
    assert len(events) == 1
    assert events[0]["event"] == "langfuse_auth_ok"
    assert events[0]["host"] == _HOST
    assert events[0]["log_level"] == "info"
    _assert_safe(logs)


async def test_false_auth_result_logs_authentication_failure() -> None:
    """Scenario: Rejected Langfuse credentials log an authentication failure"""
    client = MagicMock(spec=Langfuse)
    client.auth_check.return_value = False
    logs = await _run_auth_check(client)
    events = _auth_events(logs)
    assert len(events) == 1
    assert events[0]["event"] == "langfuse_auth_failed"
    assert events[0]["reason"] == "AuthCheckFailedError"
    assert events[0]["log_level"] == "warning"
    _assert_safe(logs)


async def test_401_logs_status_without_response_content() -> None:
    """Scenario: Rejected Langfuse credentials log an authentication failure"""
    client = MagicMock(spec=Langfuse)
    client.auth_check.side_effect = UnauthorizedError(
        body={"secret": _SECRET_KEY, "url": _CREDENTIAL_URL}
    )
    logs = await _run_auth_check(client)
    events = _auth_events(logs)
    assert len(events) == 1
    assert events[0]["event"] == "langfuse_auth_failed"
    assert events[0]["reason"] == "401"
    assert events[0]["log_level"] == "warning"
    _assert_safe(logs)


@pytest.mark.parametrize(
    ("error", "event", "reason"),
    [
        (
            httpx.ConnectError(f"{_SECRET_KEY} {_CREDENTIAL_URL}"),
            "langfuse_auth_unreachable",
            "ConnectError",
        ),
        (
            RuntimeError(f"{_PUBLIC_KEY} Authorization {_CREDENTIAL_URL}"),
            "langfuse_auth_failed",
            "RuntimeError",
        ),
    ],
    ids=["transport", "unexpected"],
)
async def test_exceptions_are_contained_without_secrets(
    error: Exception, event: str, reason: str
) -> None:
    """Scenario: A credential check exception is contained without secrets"""
    client = MagicMock(spec=Langfuse)
    client.auth_check.side_effect = error
    logs = await _run_auth_check(client)
    events = _auth_events(logs)
    assert len(events) == 1
    assert events[0]["event"] == event
    assert events[0]["host"] == _HOST
    assert events[0]["reason"] == reason
    assert events[0]["log_level"] == "warning"
    _assert_safe(logs)


async def test_timeout_logs_unreachable_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Scenario: A timed out credential check logs unreachable"""
    client = MagicMock(spec=Langfuse)
    release = threading.Event()
    finished = threading.Event()

    def slow_auth_check() -> bool:
        release.wait(2)
        finished.set()
        return True

    client.auth_check.side_effect = slow_auth_check
    monkeypatch.setattr(langfuse_client, "_LANGFUSE_AUTH_TIMEOUT_SECONDS", 0.01)
    with capture_logs() as logs:
        try:
            task = langfuse_client.schedule_langfuse_auth_check(client, _HOST)
            await asyncio.wait_for(task, 1)
        finally:
            release.set()
        await asyncio.to_thread(finished.wait, 1)
    assert finished.is_set()
    events = _auth_events(logs)
    assert len(events) == 1
    assert events[0]["event"] == "langfuse_auth_unreachable"
    assert events[0]["reason"] == "TimeoutError"
    assert events[0]["log_level"] == "warning"
    _assert_safe(logs)
