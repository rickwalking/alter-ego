"""Save-checklist strategy: a one-screen checklist to save (POV save)."""

from collections.abc import Mapping

from typing_extensions import override

from rag_backend.application.services.carousel_template.helpers import _render_inline
from rag_backend.application.services.carousel_template.pov_shell import (
    PovShellConfig,
    render_pov_shell,
)
from rag_backend.application.services.carousel_template.strategies.statement import (
    StatementStrategy,
)
from rag_backend.domain.models import CarouselProject
from rag_backend.domain.protocols.carousel import _RenderOptions

SAVE_CHECKLIST_STRATEGY = "save_checklist"
SAVE_CHECKLIST_MAX_ITEMS = 5
_LAYOUT = "pov-save"
_ITEM_KEYS = ("summary_points", "actions", "features")
_CHECK_ICON = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" '
    'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
    '<path d="M20 6 9 17l-5-5"/></svg>'
)
_FALLBACK = StatementStrategy()


def checklist_items(slide: Mapping[str, object]) -> list[str]:
    """Item texts from the slide's structured list (title, else body), max 5."""
    for key in _ITEM_KEYS:
        raw = slide.get(key)
        if not isinstance(raw, list):
            continue
        texts = [
            str(item.get("title") or item.get("body") or "").strip()
            for item in raw
            if isinstance(item, dict)
        ]
        texts = [text for text in texts if text]
        if texts:
            return texts[:SAVE_CHECKLIST_MAX_ITEMS]
    return []


class SaveChecklistStrategy:
    """Heading plus a 3-5 item checklist, built to be screenshotted and saved."""

    strategy_name = SAVE_CHECKLIST_STRATEGY
    display_name = "Save Checklist"
    supported_slide_types = frozenset({"summary", "closing"})

    @override
    def render(
        self,
        slide: Mapping[str, object],
        project: CarouselProject,
        theme: Mapping[str, str],
        *,
        options: _RenderOptions | None = None,
    ) -> str:
        items = checklist_items(slide)
        if not items:
            return _FALLBACK.render(slide, project, theme, options=options)
        opts = options or {}
        heading = _render_inline(str(slide.get("heading") or ""))
        rows = "".join(
            f'<li class="pov-check-item"><span class="pov-check-icon">{_CHECK_ICON}'
            f"</span><span>{_render_inline(text)}</span></li>"
            for text in items
        )
        return render_pov_shell(
            PovShellConfig(
                slide_number=str(slide.get("number", "")),
                total_slides=int(str(opts.get("total_slides", 0))),
                copy_inner_html=(
                    f'<h2 class="pov-statement-heading">{heading}</h2>\n'
                    f'      <ul class="pov-checklist">{rows}</ul>'
                ),
                layout=_LAYOUT,
            ),
            project,
        )


__all__ = [
    "SAVE_CHECKLIST_MAX_ITEMS",
    "SAVE_CHECKLIST_STRATEGY",
    "SaveChecklistStrategy",
    "checklist_items",
]
