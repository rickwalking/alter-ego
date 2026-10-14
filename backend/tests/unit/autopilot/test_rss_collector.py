"""RSS, Atom, and the Anthropic sitemap (AE-0352).

Gherkin: tests/features/autopilot_signals.feature
  Scenario: Bundle combines all free sources
"""

from __future__ import annotations

import httpx
import pytest
import respx

from rag_backend.modules.autopilot.constants import ANTHROPIC_NEWS_PATH, SOURCE_RSS
from rag_backend.modules.autopilot.infrastructure.collectors.errors import UpstreamError
from rag_backend.modules.autopilot.infrastructure.collectors.http_get import HttpxGetter
from rag_backend.modules.autopilot.infrastructure.collectors.rss import RssCollector
from rag_backend.modules.autopilot.infrastructure.collectors.rss_parse import (
    FeedDocumentError,
    FeedSpec,
    parse_feed,
)
from tests.unit.autopilot.support import WINDOW

_OPENAI = "https://openai.example/rss.xml"
_ATOM = "https://verge.example/atom.xml"
_SITEMAP = "https://anthropic.example/sitemap.xml"
_HTTP = HttpxGetter(5.0)

_RSS = """<?xml version="1.0"?>
<rss><channel>
  <item>
    <title>New model &amp; agents</title>
    <link>https://openai.example/news/model</link>
    <description><![CDATA[<p>Ships today</p>]]></description>
    <pubDate>Tue, 13 Oct 2026 12:00:00 GMT</pubDate>
  </item>
  <item>
    <title>Ancient</title>
    <link>https://openai.example/news/old</link>
    <description>old</description>
    <pubDate>Tue, 13 Aug 2026 12:00:00 GMT</pubDate>
  </item>
</channel></rss>
"""

_ATOM_DOC = """<?xml version="1.0"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <title>Verge item</title>
    <link rel="alternate" href="https://verge.example/ai/story"/>
    <summary>A summary</summary>
    <updated>2026-10-12T00:00:00Z</updated>
  </entry>
</feed>
"""

_SITEMAP_DOC = """<?xml version="1.0"?>
<urlset>
  <url>
    <loc>https://www.anthropic.com/news/claude-update</loc>
    <lastmod>2026-10-10T00:00:00Z</lastmod>
  </url>
  <url>
    <loc>https://www.anthropic.com/careers/jobs</loc>
    <lastmod>2026-10-12T00:00:00Z</lastmod>
  </url>
  <url>
    <loc>https://www.anthropic.com/news/old-post</loc>
    <lastmod>2026-01-01T00:00:00Z</lastmod>
  </url>
</urlset>
"""


def test_rss_atom_and_sitemap_items() -> None:
    rss = parse_feed(_RSS, FeedSpec(url=_OPENAI), WINDOW)
    assert len(rss) == 1
    assert rss[0].source.value == SOURCE_RSS
    assert rss[0].title == "New model & agents"
    assert rss[0].text == "Ships today"
    atom = parse_feed(_ATOM_DOC, FeedSpec(url=_ATOM), WINDOW)
    assert atom[0].url == "https://verge.example/ai/story"
    assert atom[0].text == "A summary"
    news = parse_feed(
        _SITEMAP_DOC,
        FeedSpec(url=_SITEMAP, path_contains=ANTHROPIC_NEWS_PATH),
        WINDOW,
    )
    assert [signal.url for signal in news] == [
        "https://www.anthropic.com/news/claude-update"
    ]
    assert news[0].title == "claude update"


def test_invalid_xml_and_doctype_are_rejected() -> None:
    with pytest.raises(FeedDocumentError):
        parse_feed("this is not xml", FeedSpec(url=_OPENAI), WINDOW)
    doctype = """<?xml version="1.0"?>
    <!DOCTYPE foo [<!ENTITY x "y">]>
    <rss><channel></channel></rss>
    """
    with pytest.raises(FeedDocumentError):
        parse_feed(doctype, FeedSpec(url=_OPENAI), WINDOW)


@pytest.mark.asyncio
async def test_one_bad_feed_does_not_drop_the_others() -> None:
    feeds = (FeedSpec(url=_OPENAI), FeedSpec(url=_ATOM))
    with respx.mock(assert_all_called=False) as router:
        router.get(_OPENAI).mock(return_value=httpx.Response(500, text="down"))
        router.get(_ATOM).mock(return_value=httpx.Response(200, text=_ATOM_DOC))
        signals = await RssCollector(_HTTP, feeds).collect(WINDOW)
    assert [signal.url for signal in signals] == ["https://verge.example/ai/story"]


@pytest.mark.asyncio
async def test_every_feed_failing_raises() -> None:
    feeds = (FeedSpec(url=_OPENAI),)
    with respx.mock(assert_all_called=True) as router:
        router.get(_OPENAI).mock(return_value=httpx.Response(200, text="not xml"))
        with pytest.raises(UpstreamError):
            await RssCollector(_HTTP, feeds).collect(WINDOW)
    with respx.mock(assert_all_called=True) as router:
        router.get(_OPENAI).mock(side_effect=httpx.ConnectError("offline"))
        with pytest.raises(UpstreamError):
            await RssCollector(_HTTP, feeds).collect(WINDOW)


@pytest.mark.asyncio
async def test_empty_feed_list_returns_nothing() -> None:
    assert await RssCollector(_HTTP, ()).collect(WINDOW) == []
