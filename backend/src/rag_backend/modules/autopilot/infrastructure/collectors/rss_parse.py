"""Parse RSS, Atom, and the Anthropic news sitemap into signals.

Invalid XML raises ``FeedDocumentError``. A valid document with no
matching items returns an empty list.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from html import unescape
from typing import Protocol, cast, runtime_checkable
from urllib.parse import urlsplit

from defusedxml.common import DefusedXmlException
from defusedxml.ElementTree import ParseError, fromstring

from rag_backend.modules.autopilot.constants import RSS_MAX_AGE_DAYS
from rag_backend.modules.autopilot.domain.signals import (
    CollectWindow,
    Signal,
    SignalDraft,
    SignalSource,
    signal_from,
)
from rag_backend.modules.autopilot.infrastructure.collectors.timestamps import (
    parse_timestamp,
)
from rag_backend.modules.autopilot.infrastructure.collectors.x_resolver import (
    strip_tags,
)

_TAG_URLSET = "urlset"
_TAG_URL = "url"
_TAG_LINK = "link"
_TAG_LOC = "loc"
_TAG_TITLE = "title"
_ATTR_HREF = "href"
_ATTR_REL = "rel"
_REL_OK = ("", "alternate")
_ENTRY_TAGS = ("item", "entry")
_DATE_TAGS = ("pubDate", "published", "updated", "lastmod", "date")
_BODY_TAGS = ("description", "summary", "content")


class FeedDocumentError(Exception):
    """The response was not a feed document."""


@dataclass(frozen=True, kw_only=True)
class FeedSpec:
    """One feed URL. ``path_contains`` limits sitemap entries to a section."""

    url: str
    path_contains: str = ""


@dataclass(frozen=True, kw_only=True)
class XmlNode:
    """A feed element after it has left the XML library."""

    tag: str
    text: str
    attrib: dict[str, str]
    children: tuple[XmlNode, ...]
    tail: str


def parse_feed(xml_text: str, spec: FeedSpec, window: CollectWindow) -> list[Signal]:
    """Return recent items from one document."""
    root = _parse_root(xml_text)
    cutoff = window.as_of - timedelta(days=RSS_MAX_AGE_DAYS)
    signals: list[Signal] = []
    for entry in _entries(root):
        signal = _entry_signal(entry, spec, cutoff)
        if signal is not None:
            signals.append(signal)
    return signals


def _parse_root(xml_text: str) -> XmlNode:
    try:
        parsed = fromstring(xml_text)
    except (ParseError, DefusedXmlException) as exc:
        raise FeedDocumentError from exc
    return _convert(cast(object, parsed))


def _entries(root: XmlNode) -> list[XmlNode]:
    if root.tag == _TAG_URLSET:
        return [child for child in root.children if child.tag == _TAG_URL]
    found: list[XmlNode] = []
    _walk(root, found)
    return found


def _walk(node: XmlNode, found: list[XmlNode]) -> None:
    for child in node.children:
        if child.tag in _ENTRY_TAGS:
            found.append(child)
            continue
        _walk(child, found)


def _entry_signal(entry: XmlNode, spec: FeedSpec, cutoff: datetime) -> Signal | None:
    url = _entry_link(entry).strip()
    if not url or not _path_allowed(url, spec.path_contains):
        return None
    posted_at = _posted_at(entry)
    if posted_at is None or posted_at < cutoff:
        return None
    title = _title(entry, url)
    return signal_from(
        SignalDraft(
            source=SignalSource.RSS,
            url=url,
            title=title,
            text=_body(entry, title),
            posted_at=posted_at,
        )
    )


def _path_allowed(url: str, path_contains: str) -> bool:
    if not path_contains:
        return True
    return path_contains in urlsplit(url).path


def _title(entry: XmlNode, url: str) -> str:
    title = _plain(_child_text(entry, _TAG_TITLE))
    if title:
        return title
    return _title_from_url(url)


def _body(entry: XmlNode, title: str) -> str:
    for name in _BODY_TAGS:
        text = _plain(_child_text(entry, name))
        if text:
            return text
    return title


def _posted_at(entry: XmlNode) -> datetime | None:
    for name in _DATE_TAGS:
        parsed = parse_timestamp(_child_text(entry, name))
        if parsed is not None:
            return parsed
    return None


def _entry_link(entry: XmlNode) -> str:
    loc = _child_text(entry, _TAG_LOC)
    if loc:
        return loc
    fallback = ""
    for child in entry.children:
        candidate = _link_candidate(child)
        if candidate is None:
            continue
        if child.attrib.get(_ATTR_REL, "") in _REL_OK:
            return candidate
        if not fallback:
            fallback = candidate
    return fallback


def _link_candidate(child: XmlNode) -> str | None:
    if child.tag != _TAG_LINK:
        return None
    candidate = child.attrib.get(_ATTR_HREF, "") or _node_text(child)
    if not candidate:
        return None
    return candidate


def _child_text(node: XmlNode, name: str) -> str:
    for child in node.children:
        if child.tag == name:
            return _node_text(child)
    return ""


def _node_text(node: XmlNode) -> str:
    parts = [node.text]
    for child in node.children:
        parts.append(_node_text(child))
        parts.append(child.tail)
    return "".join(parts).strip()


def _plain(value: str) -> str:
    return unescape(strip_tags(value)).strip()


def _title_from_url(url: str) -> str:
    slug = urlsplit(url).path.rstrip("/").rsplit("/", maxsplit=1)[-1]
    return slug.replace("-", " ").strip()


def _convert(element: object) -> XmlNode:
    return XmlNode(
        tag=_local(_read(element, "tag")),
        text=_string(_read(element, "text")),
        attrib=_attrib(_read(element, "attrib")),
        children=tuple(_convert(child) for child in _children(element)),
        tail=_string(_read(element, "tail")),
    )


def _read(element: object, name: str) -> object:
    return cast(object, getattr(element, name, None))


@runtime_checkable
class _Indexed(Protocol):
    """ElementTree nodes iterate by index, not by ``__iter__``."""

    def __getitem__(self, index: int) -> object:
        """Return the child at ``index``."""
        ...


def _children(element: object) -> list[object]:
    if isinstance(element, str | bytes) or not isinstance(element, _Indexed):
        return []
    collected: list[object] = []
    index = 0
    while True:
        try:
            collected.append(element[index])
        except (IndexError, TypeError, KeyError):
            return collected
        index += 1


def _local(tag: object) -> str:
    if not isinstance(tag, str):
        return ""
    if "}" in tag:
        return tag.rsplit("}", maxsplit=1)[-1]
    return tag


def _string(value: object) -> str:
    if isinstance(value, str):
        return value
    return ""


def _attrib(value: object) -> dict[str, str]:
    mapping = value if isinstance(value, dict) else None
    if mapping is None:
        return {}
    raw = cast(dict[object, object], mapping)
    return {
        key: item
        for key, item in raw.items()
        if isinstance(key, str) and isinstance(item, str)
    }
