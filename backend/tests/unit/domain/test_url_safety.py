"""SSRF guard rules with mocked DNS (QA r1 S-W1).

Feature: tests/features/url_safety_ssrf.feature

_REAL_RESOLVE is captured at import, before the conftest autouse stub replaces it per
test.
"""

from __future__ import annotations

import ipaddress
import socket

import pytest

from rag_backend.agents.tools.url_safety import (
    is_safe_research_target,
    is_safe_research_url,
)
from rag_backend.domain import url_safety
from rag_backend.domain.url_safety import (
    is_blocked_hostname,
    is_disallowed_ip,
    is_safe_url_target,
)

_PUBLIC = "93.184.216.34"
_URL = "https://news.example.com/story"
_REAL_RESOLVE = url_safety.system_resolve


def _answers(*addresses: str) -> url_safety.HostResolver:
    async def resolve(_host: str) -> tuple[str, ...]:
        return addresses

    return resolve


class _Spy:
    def __init__(self) -> None:
        self.calls: list[str] = []

    async def __call__(self, host: str) -> tuple[str, ...]:
        self.calls.append(host)
        return (_PUBLIC,)


# Scenario: Public host is allowed
@pytest.mark.asyncio
async def test_public_host_is_allowed() -> None:
    assert await is_safe_url_target(_URL, _answers(_PUBLIC)) is True


# Scenario Outline: Host resolving to an internal address is refused
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "address",
    [
        "10.0.0.5",
        "192.168.1.10",
        "127.0.0.1",
        "169.254.169.254",
        "100.64.0.1",
        "fd00::1",
        "::1",
        "fe80::1%eth0",
        str(ipaddress.IPv4Address(0)),
        "224.0.0.1",
        "::ffff:10.0.0.1",
    ],
)
async def test_internal_answer_is_refused(address: str) -> None:
    assert await is_safe_url_target(_URL, _answers(address)) is False


# Scenario: One internal answer among public ones is refused
@pytest.mark.asyncio
async def test_mixed_answers_are_refused() -> None:
    assert await is_safe_url_target(_URL, _answers(_PUBLIC, "10.1.2.3")) is False


# Scenario: DNS failure fails closed
@pytest.mark.asyncio
async def test_dns_failure_is_refused() -> None:
    async def fail(_host: str) -> tuple[str, ...]:
        raise socket.gaierror("no such host")

    assert await is_safe_url_target(_URL, fail) is False
    assert await is_safe_url_target(_URL, _answers()) is False


# Scenario Outline: Docker service names and single-label hosts are refused without DNS
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "url",
    [
        "http://redis:6379/",
        "http://postgres/",
        "http://minio:9000/bucket",
        "http://langfuse:3000/",
        "http://clickhouse:8123/",
        "http://backend:8000/api",
        "http://frontend:3000/",
        "http://nginx/",
        "http://intranet/",
        "http://localhost/",
        "http://metadata.google.internal/",
        "http://db.internal/",
        "ftp://example.com/file",
        "not a url",
    ],
)
async def test_internal_names_are_refused_without_dns(url: str) -> None:
    spy = _Spy()
    assert await is_safe_url_target(url, spy) is False
    assert is_safe_research_url(url) is False
    assert spy.calls == []


@pytest.mark.asyncio
async def test_ip_literals_are_judged_without_dns() -> None:
    spy = _Spy()
    assert await is_safe_url_target("http://169.254.169.254/latest", spy) is False
    assert await is_safe_url_target("http://[::1]/", spy) is False
    assert await is_safe_url_target(f"http://{_PUBLIC}/", spy) is True
    assert spy.calls == []


def test_hostname_and_ip_helpers() -> None:
    assert is_blocked_hostname("redis") is True
    assert is_blocked_hostname("10.0.0.1") is False
    assert is_blocked_hostname("example.com") is False
    assert is_disallowed_ip("not-an-ip") is True
    assert is_disallowed_ip(_PUBLIC) is False


@pytest.mark.asyncio
async def test_agents_target_check_uses_the_system_resolver(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The agents guard resolves through ``system_resolve`` (stubbed in conftest)."""
    monkeypatch.setattr(url_safety, "system_resolve", _answers("10.0.0.9"))
    assert await is_safe_research_target(_URL) is False
    monkeypatch.setattr(url_safety, "system_resolve", _answers(_PUBLIC))
    assert await is_safe_research_target(_URL) is True


@pytest.mark.asyncio
async def test_system_resolve_reads_getaddrinfo(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The real resolver returns every address getaddrinfo answers, with no network."""
    import asyncio

    loop = asyncio.get_running_loop()

    async def fake_getaddrinfo(
        host: str, port: object, **_: object
    ) -> list[tuple[object, ...]]:
        return [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", (_PUBLIC, 0)),
            (socket.AF_INET6, socket.SOCK_STREAM, 6, "", ("fd00::1", 0, 0, 0)),
        ]

    monkeypatch.setattr(loop, "getaddrinfo", fake_getaddrinfo)
    addresses = await _REAL_RESOLVE("news.example.com")
    assert addresses == (_PUBLIC, "fd00::1")
