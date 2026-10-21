"""SSRF guard constants shared by the research scraper and its adapters.

- ``BLOCKED_URL_HOSTNAMES`` always point inside the deployment (loopback aliases,
  the cloud metadata service, this stack's docker-compose service names);
  ``BLOCKED_HOST_SUFFIXES`` resolve only inside a private network. A public
  hostname has at least one dot (``redis`` or ``db`` do not).
- getaddrinfo may append a scope id to link-local IPv6 (``fe80::1%eth0``).
- Carrier-grade NAT is not ``is_private`` in every Python version, so it is
  listed in ``BLOCKED_NETWORKS`` explicitly.
- Chromium never follows a redirect: the document is fetched with redirects off,
  each hop is checked (scheme, names, every DNS answer) before it is requested,
  then the HTML is rendered with every page request aborted.
- One deadline covers the whole fetch (all hops); only text documents are
  rendered; the request looks like a browser; the charset comes from the header,
  then the page's ``<meta>``. Scraped text is cut to ``RESEARCH_TEXT_MAX_CHARS``.
- Rendered HTML must not make Chromium resolve or connect to a host (DNS
  prefetch off, resource hints stripped).
"""

from __future__ import annotations

ALLOWED_URL_SCHEMES: tuple[str, ...] = ("http", "https")

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

BLOCKED_HOST_SUFFIXES: tuple[str, ...] = (".localhost", ".internal", ".local")

HOST_LABEL_SEPARATOR = "."
IPV6_ZONE_SEPARATOR = "%"

BLOCKED_NETWORKS: tuple[str, ...] = ("100.64.0.0/10",)

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

RESEARCH_FETCH_DEADLINE_SECONDS = 15.0
HEADER_USER_AGENT = "user-agent"
HEADER_ACCEPT = "accept"
HEADER_ACCEPT_LANGUAGE = "accept-language"
HEADER_CONTENT_TYPE = "content-type"
RESEARCH_REQUEST_HEADERS: dict[str, str] = {
    HEADER_USER_AGENT: (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
    ),
    HEADER_ACCEPT: (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "text/plain;q=0.8,*/*;q=0.5"
    ),
    HEADER_ACCEPT_LANGUAGE: "en-US,en;q=0.9,pt-BR;q=0.8,pt;q=0.7",
}
MEDIA_TYPE_TEXT_HTML = "text/html"
MEDIA_TYPE_XHTML = "application/xhtml+xml"
MEDIA_TYPE_TEXT_PLAIN = "text/plain"
RESEARCH_TEXT_MEDIA_TYPES: frozenset[str] = frozenset({
    MEDIA_TYPE_TEXT_HTML,
    MEDIA_TYPE_XHTML,
    MEDIA_TYPE_TEXT_PLAIN,
})
MEDIA_TYPE_PARAM_SEPARATOR = ";"
ERR_UNSUPPORTED_CONTENT = "research_url_unsupported_content_type"
LOG_URL_UNSUPPORTED = "research_url_unsupported_content"
META_CHARSET_PATTERN = r"""<meta\b[^>]*?charset\s*=\s*["']?\s*([A-Za-z0-9._:-]+)"""
META_CHARSET_SCAN_BYTES = 4096
META_SCAN_ENCODING = "ascii"
DECODE_ERRORS = "replace"
RESEARCH_TEXT_MAX_CHARS = 10_000

CHROMIUM_DISABLE_DNS_PREFETCH = "--dns-prefetch-disable"
RESOURCE_HINT_PATTERN = (
    r"""<link\b[^>]*?\brel\s*=\s*["']?[^"'>]*?"""
    r"""\b(?:dns-prefetch|preconnect|prefetch|preload|modulepreload|prerender)\b"""
    r"""[^>]*>"""
)
