"""SSRF guard for URLs the research scraper is asked to open (QA r1 S-W1).

Scraped URLs come from untrusted places: LLM tool calls, user sources, and
third-party story links collected by autopilot. A URL is safe only when:

- its scheme is http(s);
- its host is not a known-internal name (loopback alias, metadata service,
  a docker-compose service name) and is not a single-label host;
- every address the host resolves to is globally routable (no private,
  loopback, link-local incl. ``169.254.169.254``, ULA ``fc00::/7``,
  unspecified, multicast, reserved, or CGNAT ``100.64.0.0/10``).

The scraper re-runs this check on every request the page makes, which covers
redirect hops (see ``application/services/tools/research_tool.py``).

Residual risk: DNS rebinding between this lookup and the browser's own lookup.
The window is small and every hop is re-checked.

Stdlib only, so both ``agents`` and ``application`` may import it.
"""

from __future__ import annotations

import asyncio
import ipaddress
import socket
from collections.abc import Awaitable, Callable
from urllib.parse import urlparse

from rag_backend.domain.constants.url_safety import (
    ALLOWED_URL_SCHEMES,
    BLOCKED_HOST_SUFFIXES,
    BLOCKED_NETWORKS,
    BLOCKED_URL_HOSTNAMES,
    HOST_LABEL_SEPARATOR,
    IPV6_ZONE_SEPARATOR,
)

HostResolver = Callable[[str], Awaitable[tuple[str, ...]]]

_IpAddress = ipaddress.IPv4Address | ipaddress.IPv6Address
_EXTRA_BLOCKED = tuple(ipaddress.ip_network(net) for net in BLOCKED_NETWORKS)


def url_host(url: str) -> str | None:
    """Lower-case host of an http(s) URL, or None when the URL is not one."""
    try:
        parsed = urlparse(url.strip())
        host = parsed.hostname
    except ValueError:
        return None
    if parsed.scheme.lower() not in ALLOWED_URL_SCHEMES or not host:
        return None
    return host.lower().rstrip(HOST_LABEL_SEPARATOR)


def is_disallowed_ip(address: str) -> bool:
    """True when ``address`` is not a globally routable unicast IP."""
    try:
        ip = ipaddress.ip_address(address.split(IPV6_ZONE_SEPARATOR, 1)[0])
    except ValueError:
        return True
    return _is_internal(ip)


def is_blocked_hostname(host: str) -> bool:
    """True for internal names and single-label hosts. IP literals are judged by IP."""
    if _ip_literal(host) is not None:
        return False
    if host in BLOCKED_URL_HOSTNAMES:
        return True
    if HOST_LABEL_SEPARATOR not in host:
        return True
    return host.endswith(BLOCKED_HOST_SUFFIXES)


def is_safe_url_syntax(url: str) -> bool:
    """Checks that need no DNS: scheme, internal names, and internal IP literals."""
    host = url_host(url)
    if host is None or is_blocked_hostname(host):
        return False
    literal = _ip_literal(host)
    return literal is None or not _is_internal(literal)


async def system_resolve(host: str) -> tuple[str, ...]:
    """Every address the host resolves to. Raises ``OSError`` on failure."""
    loop = asyncio.get_running_loop()
    infos = await loop.getaddrinfo(host, None, type=socket.SOCK_STREAM)
    return tuple(str(info[4][0]) for info in infos)


async def is_safe_url_target(url: str, resolver: HostResolver | None = None) -> bool:
    """Syntax check plus DNS: every resolved address must be public.

    A lookup failure, or a host that resolves to nothing, is unsafe (fail closed).
    """
    if not is_safe_url_syntax(url):
        return False
    host = url_host(url) or ""
    if _ip_literal(host) is not None:
        return True
    resolve = resolver or system_resolve
    try:
        addresses = await resolve(host)
    except (OSError, UnicodeError):
        return False
    if not addresses:
        return False
    return not any(is_disallowed_ip(address) for address in addresses)


def _ip_literal(host: str) -> _IpAddress | None:
    try:
        return ipaddress.ip_address(host)
    except ValueError:
        return None


def _is_internal(ip: _IpAddress) -> bool:
    mapped = ip.ipv4_mapped if isinstance(ip, ipaddress.IPv6Address) else None
    if mapped is not None:
        return _is_internal(mapped)
    if not ip.is_global or ip.is_multicast or ip.is_reserved:
        return True
    return any(ip in network for network in _EXTRA_BLOCKED)


__all__ = [
    "HostResolver",
    "is_blocked_hostname",
    "is_disallowed_ip",
    "is_safe_url_syntax",
    "is_safe_url_target",
    "system_resolve",
    "url_host",
]
