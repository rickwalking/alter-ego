"""Langfuse tracing needs both Cloud keys; otherwise it stays quietly off.

Feature: backend/tests/features/langfuse_cloud_ae0545.feature
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from rag_backend import monitoring_langfuse as root_monitoring
from rag_backend.infrastructure import langfuse_client
from rag_backend.infrastructure.config.settings import Settings

CLOUD_HOST = "https://cloud.langfuse.com"


@pytest.fixture
def constructors(monkeypatch: pytest.MonkeyPatch) -> dict[str, MagicMock]:
    """Replace every Langfuse constructor and restore the module globals."""
    mocks = {
        "client": MagicMock(name="Langfuse"),
        "root_client": MagicMock(name="RootLangfuse"),
        "handler": MagicMock(name="CallbackHandler"),
    }
    monkeypatch.setattr(langfuse_client, "Langfuse", mocks["client"])
    monkeypatch.setattr(root_monitoring, "Langfuse", mocks["root_client"])
    monkeypatch.setattr(root_monitoring, "CallbackHandler", mocks["handler"])
    monkeypatch.setattr(langfuse_client, "LANGFUSE_CLIENT", None)
    monkeypatch.setattr(root_monitoring, "_langfuse_client", None)
    monkeypatch.setattr(root_monitoring, "_langfuse_handler", None)
    for name in (
        "LANGFUSE_SECRET_KEY",
        "LANGFUSE_PUBLIC_KEY",
        "LANGFUSE_HOST",
        "LANGFUSE_BASE_URL",
    ):
        monkeypatch.delenv(name, raising=False)
    return mocks


def _nothing_created(mocks: dict[str, MagicMock]) -> None:
    for mock in mocks.values():
        mock.assert_not_called()
    assert root_monitoring.get_langfuse_client() is None
    assert root_monitoring.get_langfuse_handler() is None


def test_tracing_is_disabled_without_keys(constructors: dict[str, MagicMock]) -> None:
    """Scenario: Tracing is disabled when the Langfuse keys are not set"""
    assert langfuse_client.init_langfuse(None, "", CLOUD_HOST) is None
    assert langfuse_client.init_langfuse("", "", CLOUD_HOST) is None
    assert root_monitoring.init_langfuse("", "", CLOUD_HOST) is None
    _nothing_created(constructors)


@pytest.mark.parametrize(
    ("public_key", "secret_key"),
    [("pk-lf-public", ""), ("", "sk-lf-secret"), (None, "sk-lf-secret")],
)
def test_tracing_stays_disabled_with_one_key(
    constructors: dict[str, MagicMock], public_key: str | None, secret_key: str
) -> None:
    """Scenario: Tracing stays disabled when only one Langfuse key is set"""
    assert langfuse_client.init_langfuse(public_key, secret_key, CLOUD_HOST) is None
    assert (
        root_monitoring.init_langfuse(public_key or "", secret_key, CLOUD_HOST) is None
    )
    _nothing_created(constructors)


def test_tracing_reports_to_the_cloud_host_with_both_keys(
    constructors: dict[str, MagicMock],
) -> None:
    """Scenario: Tracing reports to Langfuse Cloud when both keys are set"""
    client = langfuse_client.init_langfuse("pk-lf-public", "sk-lf-secret", CLOUD_HOST)
    assert client is constructors["client"].return_value
    constructors["client"].assert_called_once_with(
        public_key="pk-lf-public", secret_key="sk-lf-secret", base_url=CLOUD_HOST
    )
    constructors["root_client"].assert_called_once_with(
        secret_key="sk-lf-secret", public_key="pk-lf-public", base_url=CLOUD_HOST
    )
    constructors["handler"].assert_called_once_with(public_key="pk-lf-public")
    assert (
        root_monitoring.get_langfuse_handler() is constructors["handler"].return_value
    )


def test_the_backend_defaults_to_the_langfuse_cloud_host(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Scenario: The backend defaults to the Langfuse Cloud host"""
    monkeypatch.delenv("LANGFUSE_HOST", raising=False)
    monkeypatch.delenv("LANGFUSE_BASE_URL", raising=False)
    settings = Settings(
        _env_file=None,
        secret_key="s" * 40,
        anon_secret_key="a" * 40,
    )
    assert settings.langfuse_host == CLOUD_HOST
