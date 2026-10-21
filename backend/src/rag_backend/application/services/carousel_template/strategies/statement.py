"""Statement strategy: big text, no artwork (POV rehook/pov/point)."""

from collections.abc import Mapping

from typing_extensions import override

from rag_backend.application.services.carousel_template.helpers import (
    _render_inline,
    slide_body_html,
)
from rag_backend.application.services.carousel_template.pov_shell import (
    PovShellConfig,
    render_pov_shell,
)
from rag_backend.domain.models import CarouselProject
from rag_backend.domain.protocols.carousel import _RenderOptions

STATEMENT_STRATEGY = "statement"
_LAYOUT = "pov-statement"


class StatementStrategy:
    """One idea per slide in large type on a solid palette background."""

    strategy_name = STATEMENT_STRATEGY
    display_name = "Statement"
    supported_slide_types = frozenset({"content", "summary", "closing"})

    @override
    def render(
        self,
        slide: Mapping[str, object],
        project: CarouselProject,
        _theme: Mapping[str, str],
        *,
        options: _RenderOptions | None = None,
    ) -> str:
        opts = options or {}
        heading = _render_inline(str(slide.get("heading") or ""))
        body_html = slide_body_html(slide, "pov-statement-body")
        return render_pov_shell(
            PovShellConfig(
                slide_number=str(slide.get("number", "")),
                total_slides=int(str(opts.get("total_slides", 0))),
                copy_inner_html=(
                    f'<h2 class="pov-statement-heading">{heading}</h2>\n'
                    f"      {body_html}"
                ),
                layout=_LAYOUT,
            ),
            project,
        )


__all__ = ["STATEMENT_STRATEGY", "StatementStrategy"]
