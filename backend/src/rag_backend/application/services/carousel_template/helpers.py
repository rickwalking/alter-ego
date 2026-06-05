"""Helper functions for carousel HTML rendering."""

import html as html_module
import re

from rag_backend.domain.models import CarouselProject

_BOLD_RE = re.compile(r"\*\*(.+?)\*\*", re.DOTALL)
_CODE_RE = re.compile(r"`([^`\n]+?)`")


def _render_inline(text: str) -> str:
    """Render inline text with HTML escaping, newline→<br>, code tags, and bold."""
    escaped = html_module.escape(text, quote=True)
    with_breaks = escaped.replace("\n", "<br>")
    with_code = _CODE_RE.sub(r'<span class="code-tag">\1</span>', with_breaks)
    return _BOLD_RE.sub(r"<strong>\1</strong>", with_code)


def _build_watermark_html(project: CarouselProject) -> str:
    """Return creator watermark HTML if creator metadata is present."""
    name = project.creator_name
    if not name:
        return ""
    handle = project.creator_handle or ""
    avatar = project.creator_avatar_url or ""
    handle_text = f"@{handle}" if handle else ""
    esc = html_module.escape
    avatar_html = (
        f'<div class="creator-watermark-avatar">'
        f'<img src="{esc(avatar, quote=True)}" alt="{esc(name, quote=True)}" />'
        f"</div>"
        if avatar
        else ""
    )
    return (
        f'<div class="creator-watermark">'
        f"{avatar_html}"
        f'<div class="creator-watermark-text">'
        f'<span class="creator-watermark-name">{esc(name, quote=True)}</span>'
        f'<span class="creator-watermark-handle">{esc(handle_text, quote=True)}</span>'
        f"</div></div>"
    )
