"""Helper functions for carousel HTML rendering."""

import html
import re

from rag_backend.application.services.carousel.types import SlideDict

FEATURE_GRID_TWO_COLUMNS = 2

_EM_DASH_RE = re.compile(r"\s*[—-]+\s*")
_BOLD_RE = re.compile(r"\*\*(.+?)\*\*", re.DOTALL)
_CODE_RE = re.compile(r"`([^`\n]+?)`")


def _render_inline(text: str) -> str:
    escaped = html.escape(text, quote=False)
    without_dashes = _EM_DASH_RE.sub(". ", escaped)
    with_code = _CODE_RE.sub(r'<span class="code-tag">\1</span>', without_dashes)
    return _BOLD_RE.sub(r"<strong>\1</strong>", with_code)


def _feature_items(slide: SlideDict) -> list[dict[str, str]] | None:
    features = slide.get("features")
    if not isinstance(features, list) or not features:
        return None
    items: list[dict[str, str]] = []
    for entry in features:
        if not isinstance(entry, dict):
            continue
        title = entry.get("title") or ""
        body = entry.get("body") or ""
        if not title and not body:
            continue
        items.append({
            "icon": str(entry.get("icon") or "✅"),
            "title": str(title),
            "body": str(body),
        })
    return items or None


def _stat_items(slide: SlideDict) -> list[dict[str, str]] | None:
    stats = slide.get("stats")
    if not isinstance(stats, list) or not stats:
        return None
    items: list[dict[str, str]] = []
    for entry in stats:
        if not isinstance(entry, dict):
            continue
        value = str(entry.get("value") or "").strip()
        label = str(entry.get("label") or "").strip()
        if not value:
            continue
        items.append({
            "value": value,
            "label": label,
            "detail": str(entry.get("detail") or ""),
        })
    return items or None


def _insight_quote(slide: SlideDict) -> dict[str, str] | None:
    raw = slide.get("insight")
    if not isinstance(raw, dict):
        return None
    quote = str(raw.get("quote") or "").strip()
    if not quote:
        return None
    return {"quote": quote, "attribution": str(raw.get("attribution") or "").strip()}


def _render_stat_row(items: list[dict[str, str]]) -> str:
    cards: list[str] = []
    for item in items:
        detail_html = (
            f'<div class="stat-detail">{_render_inline(item["detail"])}</div>'
            if item.get("detail")
            else ""
        )
        cards.append(
            '<div class="stat-card">'
            f'<div class="stat-number">{_render_inline(item["value"])}</div>'
            f'<div class="stat-label">{_render_inline(item["label"])}</div>'
            f"{detail_html}"
            "</div>"
        )
    return '<div class="stat-row">' + "".join(cards) + "</div>"


def _render_feature_grid(items: list[dict[str, str]], *, columns: int = 1) -> str:
    cls = (
        "feature-grid cols-2" if columns == FEATURE_GRID_TWO_COLUMNS else "feature-grid"
    )
    cards: list[str] = [
        '<div class="feature-item">'
        f'<div class="feature-icon">{html.escape(item["icon"], quote=False)}</div>'
        '<div class="feature-text">'
        f'<div class="feature-title">{_render_inline(item["title"])}</div>'
        f'<div class="feature-body">{_render_inline(item["body"])}</div>'
        "</div></div>"
        for item in items
    ]
    return f'<div class="{cls}">' + "".join(cards) + "</div>"


def _render_insight_card(insight: dict[str, str]) -> str:
    quote_html = _render_inline(f'"{insight["quote"]}"')
    if insight.get("attribution"):
        quote_html += f'<span class="insight-attribution">{_render_inline(insight["attribution"])}</span>'
    return f'<div class="insight-card">{quote_html}</div>'
