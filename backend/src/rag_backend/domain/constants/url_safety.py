"""SSRF guard constants shared by the research scraper and its adapters (QA r1 S-W1)."""

from __future__ import annotations

ALLOWED_URL_SCHEMES: tuple[str, ...] = ("http", "https")

# Hostnames that always point inside the deployment: loopback aliases, the cloud
# metadata service, and the docker-compose service names of this stack.
BLOCKED_URL_HOSTNAMES: frozenset[str] = frozenset({
    "localhost",
    "metadata.google.internal",
    "langfuse",
    "minio",
    "clickhouse",
    "redis",
    "backend",
    "postgres",
    "frontend",
    "nginx",
})

# Suffixes that only resolve inside a private network.
BLOCKED_HOST_SUFFIXES: tuple[str, ...] = (".localhost", ".internal", ".local")

# A public hostname has at least one dot; ``redis`` or ``db`` do not.
HOST_LABEL_SEPARATOR = "."
# getaddrinfo may append a scope id to link-local IPv6 (``fe80::1%eth0``).
IPV6_ZONE_SEPARATOR = "%"

# Carrier-grade NAT is not ``is_private`` in every Python version, so it is
# listed explicitly.
BLOCKED_NETWORKS: tuple[str, ...] = ("100.64.0.0/10",)

# QA r2 R2: Chromium never follows a redirect. The document is fetched with
# redirects off, each hop is checked (scheme, names, every DNS answer) before
# it is requested, then the HTML is rendered with every page request aborted.
ROUTE_ALL_REQUESTS = "**/*"
RESEARCH_MAX_REDIRECTS = 5
RESEARCH_FETCH_TIMEOUT_SECONDS = 15.0
RESEARCH_FETCH_MAX_BYTES = 2_000_000
REDIRECT_STATUSES: frozenset[int] = frozenset({301, 302, 303, 307, 308})
HEADER_LOCATION = "location"
HTTP_METHOD_GET = "GET"
TEXT_ENCODING_FALLBACK = "utf-8"

LOG_URL_BLOCKED = "research_url_hop_blocked"
LOG_URL_RESOLVE_FAILED = "research_url_resolve_failed"
ERR_UNSAFE_REDIRECT = "research_url_redirected_to_unsafe_target"
ERR_TOO_MANY_REDIRECTS = "research_url_too_many_redirects"
