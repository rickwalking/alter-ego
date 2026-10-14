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

# Playwright resource types the text scraper never needs; aborting them avoids
# a DNS check per asset and keeps the page load small.
SKIPPED_RESOURCE_TYPES: frozenset[str] = frozenset({"image", "media", "font"})

# Route glob that matches every request a page makes, including redirect hops.
ROUTE_ALL_REQUESTS = "**/*"
PAGE_EVENT_REQUEST = "request"

LOG_URL_BLOCKED = "research_url_hop_blocked"
LOG_URL_RESOLVE_FAILED = "research_url_resolve_failed"
ERR_UNSAFE_REDIRECT = "research_url_redirected_to_unsafe_target"
