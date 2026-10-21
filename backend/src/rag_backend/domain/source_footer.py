"""The ``pov_news`` caption footer, built by code (spec §5). Pure.

``Fontes: @kanishksj01, @alexcovo_eth, anthropic.com``: an X source shows as
``@handle``, any other source as its domain; duplicates are dropped
(case-insensitively, first spelling kept) and the
order is the topic's ``sources`` order. The model never writes this line.
"""

from __future__ import annotations

from collections.abc import Iterable
from urllib.parse import urlsplit

from rag_backend.domain.constants.news_quotes import (
    CAPTION_FOOTER_JOIN,
    HANDLE_PREFIX,
    HOST_PREFIXES_DROPPED,
    SOURCE_FOOTER_PREFIX,
    SOURCE_FOOTER_SEPARATOR,
    X_SOURCE_HOSTS,
)


def source_label(url: str) -> str:
    """``@handle`` for an X post, else the bare domain; empty when unparseable."""
    parts = urlsplit(url.strip())
    host = _bare_host(parts.hostname or "")
    if not host:
        return ""
    if host not in X_SOURCE_HOSTS:
        return host
    handle = parts.path.strip("/").split("/")[0]
    return f"{HANDLE_PREFIX}{handle}" if handle else host


def source_footer(sources: Iterable[str]) -> str:
    """The footer line, or empty when no source has a label.

    PR #124 review: deduped case-insensitively (``@Handle`` = ``@handle``),
    keeping the first spelling.
    """
    labels: dict[str, str] = {}
    for label in map(source_label, sources):
        if label:
            labels.setdefault(label.casefold(), label)
    if not labels:
        return ""
    return SOURCE_FOOTER_PREFIX + SOURCE_FOOTER_SEPARATOR.join(labels.values())


def with_source_footer(caption: str, sources: Iterable[str]) -> str:
    """The caption with the footer appended once (idempotent)."""
    footer = source_footer(sources)
    body = caption.rstrip()
    if not footer or body.endswith(footer):
        return caption
    if not body:
        return footer
    return f"{body}{CAPTION_FOOTER_JOIN}{footer}"


def _bare_host(host: str) -> str:
    lowered = host.lower()
    for prefix in HOST_PREFIXES_DROPPED:
        if lowered.startswith(prefix):
            return lowered[len(prefix) :]
    return lowered


__all__ = ["source_footer", "source_label", "with_source_footer"]
