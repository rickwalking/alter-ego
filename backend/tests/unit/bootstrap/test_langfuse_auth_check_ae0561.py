"""Asynchronous Langfuse startup authentication checks with safe diagnostics.

Feature: backend/tests/features/langfuse_auth_check_ae0561.feature
"""

from __future__ import annotations

import asyncio
import logging
import threading
from types import SimpleNamespace
from unittest.mock import MagicMock

import httpx
import pytest
from langfuse import Langfuse
from langfuse.api.resources.projects.client import ProjectsClient
from pydantic import SecretStr
from structlog.testing import capture_logs

from rag_backend import monitoring_langfuse as root_monitoring
from rag_backend.bootstrap import observability
from rag_backend.infrastructure import langfuse_client
from rag_backend.infrastructure.config.settings import Settings

_HOST = "https://cloud.langfuse.com"
_PUBLIC_KEY = "pk-lf-planted-public"
_SECRET_KEY = "sk-lf-planted-secret"
_CREDENTIAL_URL = (
    f"https://{_PUBLIC_KEY}:{_SECRET_KEY}@cloud.langfuse.com"
    f"/trace?access_token={_SECRET_KEY}#{_PUBLIC_KEY}"
)


def _settings(host: str = _HOST) -> Settings:
    return Settings(
        _env_file=None,
        secret_key="s" * 40,
        anon_secret_key="a" * 40,
        langfuse_public_key=_PUBLIC_KEY,
        langfuse_secret_key=SecretStr(_SECRET_KEY),
        langfuse_host=host,
    )


def _client() -> MagicMock:
    client = MagicMock(spec=Langfuse)
    client.api = MagicMock()
    client.api.projects.get.return_value = SimpleNamespace(data=[object()])
    return client


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


async def _run_auth_check(
    client: Langfuse, host: str = _HOST
) -> list[dict[str, object]]:
    with capture_logs() as logs:
        task = langfuse_client.schedule_langfuse_auth_check(client, host)
        await asyncio.wait_for(task, 1)
    return logs


async def test_valid_credentials_do_not_delay_startup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Scenario: Valid Langfuse credentials log success without delaying startup"""
    client = _client()
    started = threading.Event()
    release = threading.Event()
    worker_threads: list[int] = []

    def blocked_projects_get(**_: object) -> SimpleNamespace:
        worker_threads.append(threading.get_ident())
        started.set()
        release.wait(2)
        return SimpleNamespace(data=[object()])

    client.api.projects.get.side_effect = blocked_projects_get
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
        observability.init_observability(_settings(_CREDENTIAL_URL))
        try:
            assert len(scheduled) == 1
            assert await asyncio.to_thread(started.wait, 1)
            assert not scheduled[0].done()
            assert scheduled[0] in langfuse_client._AUTH_TASKS
        finally:
            release.set()
        await asyncio.wait_for(scheduled[0], 1)
    assert scheduled[0] not in langfuse_client._AUTH_TASKS
    assert worker_threads != [threading.get_ident()]
    assert client.api.projects.get.call_count == 1
    client.auth_check.assert_not_called()
    events = _auth_events(logs)
    assert len(events) == 1
    assert events[0]["event"] == "langfuse_auth_ok"
    assert events[0]["host"] == _HOST
    assert events[0]["log_level"] == "info"
    initialized = [entry for entry in logs if entry["event"] == "langfuse_initialized"]
    assert initialized[0]["host"] == _HOST
    _assert_safe(logs)


async def test_empty_projects_response_logs_failure_and_preserves_tracing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Scenario: Rejected Langfuse credentials log an authentication failure"""
    client = _client()
    client.api.projects.get.return_value = SimpleNamespace(data=[])
    root_client = _client()
    handler = MagicMock()
    monkeypatch.setattr(langfuse_client, "LANGFUSE_CLIENT", client)
    monkeypatch.setattr(root_monitoring, "_langfuse_client", root_client)
    monkeypatch.setattr(root_monitoring, "_langfuse_handler", handler)
    logs = await _run_auth_check(client)
    events = _auth_events(logs)
    assert len(events) == 1
    assert events[0]["event"] == "langfuse_auth_failed"
    assert events[0]["reason"] == "AuthCheckFailedError"
    assert events[0]["log_level"] == "warning"
    client.api.projects.get.assert_called_once_with(
        request_options={"timeout_in_seconds": 5, "max_retries": 0}
    )
    assert langfuse_client.get_langfuse_client() is client
    assert root_monitoring.get_langfuse_client() is root_client
    assert root_monitoring.get_langfuse_handler() is handler
    _assert_safe(logs)


async def test_401_logs_status_without_response_content(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Scenario: Rejected Langfuse credentials log an authentication failure"""
    response = MagicMock()
    response.status_code = 401
    response.json.return_value = {
        "secret": _SECRET_KEY,
        "url": _CREDENTIAL_URL,
        "detail": "planted-response-body",
    }
    wrapper = SimpleNamespace(httpx_client=MagicMock())
    wrapper.httpx_client.request.return_value = response
    client = _client()
    client.api.projects = ProjectsClient(client_wrapper=wrapper)
    caplog.set_level(logging.DEBUG)
    caplog.clear()
    logs = await _run_auth_check(client, _CREDENTIAL_URL)
    events = _auth_events(logs)
    assert len(events) == 1
    assert events[0]["event"] == "langfuse_auth_failed"
    assert events[0]["host"] == _HOST
    assert events[0]["reason"] == "401"
    assert events[0]["log_level"] == "warning"
    wrapper.httpx_client.request.assert_called_once_with(
        "api/public/projects",
        method="GET",
        request_options={"timeout_in_seconds": 5, "max_retries": 0},
    )
    for unsafe in (
        _PUBLIC_KEY,
        _SECRET_KEY,
        _CREDENTIAL_URL,
        "Authorization",
        "planted-response-body",
    ):
        assert unsafe not in caplog.text
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
            httpx.ReadTimeout(f"{_SECRET_KEY} {_CREDENTIAL_URL}"),
            "langfuse_auth_unreachable",
            "ReadTimeout",
        ),
        (
            RuntimeError(f"{_PUBLIC_KEY} Authorization {_CREDENTIAL_URL}"),
            "langfuse_auth_failed",
            "RuntimeError",
        ),
    ],
    ids=["transport", "sdk-timeout", "unexpected"],
)
async def test_exceptions_are_contained_without_secrets(
    error: Exception, event: str, reason: str
) -> None:
    """Scenario: A credential check exception is contained without secrets"""
    client = _client()
    client.api.projects.get.side_effect = error
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
    client = _client()
    release = threading.Event()
    finished = threading.Event()

    def slow_projects_get(**_: object) -> SimpleNamespace:
        release.wait(2)
        finished.set()
        return SimpleNamespace(data=[object()])

    client.api.projects.get.side_effect = slow_projects_get
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


@pytest.mark.parametrize(
    ("host", "expected"),
    [
        ("http://[::1]:3000/private?token=secret", "http://[::1]:3000"),
        ("langfuse:3000", "<redacted>"),
        ("https://cloud.langfuse.com:invalid", "<redacted>"),
    ],
    ids=["ipv6-origin", "unsupported-scheme", "malformed-port"],
)
def test_diagnostic_hosts_contain_only_safe_origins(host: str, expected: str) -> None:
    """Scenario: Diagnostic hosts contain only credential-free origins"""
    assert langfuse_client.safe_langfuse_host(host) == expected
