"""SSRF boundary guard for the research ``scrape_url`` @tool (AE-0249, QA F-1).

The researcher subagent is LLM-driven, so the URL handed to ``scrape_url`` is
untrusted input. This guard runs at the adapter boundary, before the Playwright
service is invoked, and refuses:

- non-``http(s)`` schemes (``file://``, ``ftp://``, ``data:``, …); and
- targets that point at the host's own network — a literal loopback/private/
  link-local/reserved IP (covering the cloud metadata endpoint
  ``169.254.169.254``) or a known-internal hostname.

Pure stdlib — no ``application``/``infrastructure`` imports, so the
``agents -> application`` edge stays frozen at its AE-0082 baseline.

Residual risk (documented, not closed here): a *public* hostname that DNS-resolves
to an internal address is not caught — the guard does not resolve DNS. The scraping
service remains the deeper control for that class.
"""

from __future__ import annotations

import ipaddress
from urllib.parse import urlparse

from rag_backend.agents.tools.constants import (
    ALLOWED_URL_SCHEMES,
    BLOCKED_URL_HOSTNAMES,
)


def _is_internal_ip_literal(host: str) -> bool:
    """True only when ``host`` is a literal IP that is not globally routable."""
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return False  # a hostname, not an IP literal
    return not ip.is_global


def is_safe_research_url(url: str) -> bool:
    """Return True when ``url`` is an http(s) target that is not host-internal."""
    try:
        parsed = urlparse(url.strip())
    except ValueError:
        return False
    if parsed.scheme.lower() not in ALLOWED_URL_SCHEMES:
        return False
    host = parsed.hostname
    if host is None or host.lower() in BLOCKED_URL_HOSTNAMES:
        return False
    return not _is_internal_ip_literal(host)


__all__ = ["is_safe_research_url"]
