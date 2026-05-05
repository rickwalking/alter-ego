"""Writing-style profile for LinkedIn post generation.

Loads voice samples from two sources, in priority order:

1. `backend/config/writing_style_samples.yml` — if present, its full post
   bodies are used as few-shot examples. Highest fidelity.
2. Auto-scraped preview snippets from the URLs in `settings.writing_style_urls`.
   LinkedIn walls the full post body behind auth, but `og:description`
   returns the first 200-400 chars of each post without login — that's
   enough voice signal for few-shot cloning.

Samples are cached to `settings.writing_style_cache_dir` so we only
pay the scrape cost once. Delete the cache to refresh.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

import yaml

from rag_backend.domain.constants import ENCODING_UTF8
from rag_backend.domain.protocols import ResearchTool
from rag_backend.infrastructure.logging import get_logger

logger = get_logger()

_OG_DESCRIPTION_RE = re.compile(
    r'<meta\s+[^>]*property="og:description"[^>]*content="([^"]*)"',
    re.IGNORECASE,
)
_CACHE_FILENAME = "scraped_snippets.json"


@dataclass(frozen=True)
class VoiceSample:
    """A single writing-style example."""

    source_url: str
    language: str  # "pt" | "en" | "mixed"
    text: str


class WritingStyleProfile:
    """Lazy-loaded voice profile backed by a disk cache.

    Call `get_samples()` to retrieve — first call scrapes and caches,
    later calls hit the cache.
    """

    def __init__(
        self,
        research_tool: ResearchTool,
        style_urls: str,
        cache_dir: str,
        manual_samples_path: str | None = None,
    ) -> None:
        self._research = research_tool
        self._urls = [u.strip() for u in style_urls.split(",") if u.strip()]
        self._cache_path = Path(cache_dir) / _CACHE_FILENAME
        self._manual_samples_path = Path(manual_samples_path) if manual_samples_path else None
        self._samples: list[VoiceSample] | None = None

    async def get_samples(self) -> list[VoiceSample]:
        """Return voice samples, loading from manual file or cache or scraping."""
        if self._samples is not None:
            return self._samples

        manual = self._load_manual_samples()
        if manual:
            self._samples = manual
            return manual

        cached = self._load_cached_samples()
        if cached:
            self._samples = cached
            return cached

        scraped = await self._scrape_samples()
        self._save_cached_samples(scraped)
        self._samples = scraped
        return scraped

    def _load_manual_samples(self) -> list[VoiceSample]:
        """Read full post bodies from the optional YAML override."""
        if not self._manual_samples_path or not self._manual_samples_path.exists():
            return []
        try:
            raw = yaml.safe_load(self._manual_samples_path.read_text(encoding=ENCODING_UTF8))
        except (yaml.YAMLError, OSError) as exc:
            logger.warning("writing_style_manual_load_failed", error=str(exc))
            return []
        if not isinstance(raw, dict):
            return []
        items = raw.get("samples", [])
        if not isinstance(items, list):
            return []
        return [
            VoiceSample(
                source_url=str(item.get("source", "manual")),
                language=str(item.get("language", "mixed")),
                text=str(item.get("text", "")).strip(),
            )
            for item in items
            if isinstance(item, dict) and item.get("text")
        ]

    def _load_cached_samples(self) -> list[VoiceSample]:
        if not self._cache_path.exists():
            return []
        try:
            raw = json.loads(self._cache_path.read_text(encoding=ENCODING_UTF8))
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("writing_style_cache_load_failed", error=str(exc))
            return []
        return [
            VoiceSample(
                source_url=str(item.get("source_url", "")),
                language=str(item.get("language", "mixed")),
                text=str(item.get("text", "")),
            )
            for item in raw
            if isinstance(item, dict) and item.get("text")
        ]

    def _save_cached_samples(self, samples: list[VoiceSample]) -> None:
        self._cache_path.parent.mkdir(parents=True, exist_ok=True)
        payload = [
            {"source_url": s.source_url, "language": s.language, "text": s.text} for s in samples
        ]
        try:
            self._cache_path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding=ENCODING_UTF8,
            )
        except OSError as exc:
            logger.warning("writing_style_cache_save_failed", error=str(exc))

    async def _scrape_samples(self) -> list[VoiceSample]:
        """Scrape og:description previews from each configured URL."""
        samples: list[VoiceSample] = []
        for url in self._urls:
            try:
                html = await self._research.scrape_url(url)
            except Exception as exc:
                logger.warning("writing_style_scrape_failed", url=url, error=str(exc))
                continue
            text = _extract_preview(html)
            if not text:
                continue
            samples.append(
                VoiceSample(
                    source_url=url,
                    language=_detect_language(text),
                    text=text,
                )
            )
        return samples


def _extract_preview(html: str) -> str:
    """Pull og:description from raw HTML; fallback to empty string."""
    match = _OG_DESCRIPTION_RE.search(html or "")
    if not match:
        return ""
    raw = match.group(1)
    return _html_unescape(raw).strip()


def _html_unescape(text: str) -> str:
    """Cheap entity decode for the handful that appear in LinkedIn previews."""
    return (
        text.replace("&quot;", '"')
        .replace("&amp;", "&")
        .replace("&#39;", "'")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&#x27;", "'")
    )


_PT_MARKERS = {"não", "são", "está", "código", "português", "vazou", "também"}
_EN_MARKERS = {"the", "and", "that", "with", "this", "english", "attended"}


def _detect_language(text: str) -> str:
    """Crude PT/EN detector; returns 'pt', 'en', or 'mixed'."""
    lowered = text.lower()
    tokens = set(re.findall(r"[a-záàâãéêíóôõúç]+", lowered))
    pt_hits = len(tokens & _PT_MARKERS)
    en_hits = len(tokens & _EN_MARKERS)
    if pt_hits > en_hits:
        return "pt"
    if en_hits > pt_hits:
        return "en"
    return "mixed"


def format_samples_for_prompt(samples: list[VoiceSample], language: str) -> str:
    """Render samples as a few-shot block for the LLM prompt.

    Prefers same-language samples but falls back to any voice sample so
    the model learns cadence even when the target language differs.
    """
    if not samples:
        return ""
    primary = [s for s in samples if s.language == language]
    secondary = [s for s in samples if s.language != language]
    chosen = primary + secondary
    lines = ["Voice examples from the author's own posts (copy this cadence):"]
    for idx, sample in enumerate(chosen, 1):
        lines.append(f'Example {idx} ({sample.language}): """{sample.text}"""')
    return "\n".join(lines)
