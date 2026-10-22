"""Hugging Face daily papers."""

from __future__ import annotations

from rag_backend.modules.autopilot.constants import (
    HF_DAILY_PAPERS_URL,
    HF_PAPER_URL_PREFIX,
    SOURCE_HF_PAPERS,
)
from rag_backend.modules.autopilot.domain.signals import (
    CollectWindow,
    Signal,
    SignalDraft,
    SignalSource,
    signal_from,
)
from rag_backend.modules.autopilot.infrastructure.collectors.coerce import (
    as_int,
    as_list,
    as_mapping,
    as_str,
)
from rag_backend.modules.autopilot.infrastructure.collectors.fetch_json import (
    fetch_json,
)
from rag_backend.modules.autopilot.infrastructure.collectors.http_get import (
    HttpGet,
    HttpGetter,
)
from rag_backend.modules.autopilot.infrastructure.collectors.timestamps import (
    parse_timestamp,
)

_KEY_PAPER = "paper"
_KEY_ID = "id"
_KEY_TITLE = "title"
_KEY_SUMMARY = "summary"
_KEY_UPVOTES = "upvotes"
_KEY_PUBLISHED = "publishedAt"


class HuggingFacePapersCollector:
    """Daily papers as signals. ``window`` is part of the collector contract."""

    def __init__(self, http: HttpGetter) -> None:
        self._http = http
        self._source = SOURCE_HF_PAPERS

    def source_name(self) -> str:
        """Source id recorded when this collector fails."""
        return self._source

    async def collect(self, window: CollectWindow) -> list[Signal]:
        """Return today's papers. ``window`` is accepted to satisfy ``Collector``."""
        del window
        parsed = await fetch_json(self._http, HttpGet(url=HF_DAILY_PAPERS_URL))
        return signals_from_hf(parsed)


def signals_from_hf(payload: object) -> list[Signal]:
    """Map the daily-papers array. Items without an id or a time are skipped."""
    signals: list[Signal] = []
    for item in as_list(payload):
        signal = _paper(item)
        if signal is not None:
            signals.append(signal)
    return signals


def _paper(item: object) -> Signal | None:
    mapping = as_mapping(item)
    if mapping is None:
        return None
    paper = as_mapping(mapping.get(_KEY_PAPER)) or {}
    paper_id = as_str(paper.get(_KEY_ID))
    posted_at = parse_timestamp(
        as_str(mapping.get(_KEY_PUBLISHED)) or as_str(paper.get(_KEY_PUBLISHED))
    )
    if not paper_id or posted_at is None:
        return None
    title = as_str(mapping.get(_KEY_TITLE)) or as_str(paper.get(_KEY_TITLE))
    summary = as_str(mapping.get(_KEY_SUMMARY)) or as_str(paper.get(_KEY_SUMMARY))
    return signal_from(
        SignalDraft(
            source=SignalSource.HF_PAPERS,
            url=f"{HF_PAPER_URL_PREFIX}{paper_id}",
            title=title,
            text=summary or title,
            posted_at=posted_at,
            score_hint=as_int(paper.get(_KEY_UPVOTES)),
        )
    )
