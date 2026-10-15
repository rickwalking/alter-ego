"""Hook-face strategy: the owner's photo + a big hook (AE-0376, POV slide 1)."""

import html
from collections.abc import Mapping

from typing_extensions import override

from rag_backend.application.services.carousel_template.constants import swipe_text_for
from rag_backend.application.services.carousel_template.helpers import (
    _plain_text_for_attribute,
    _render_inline,
)
from rag_backend.application.services.carousel_template.pov_shell import (
    PovShellConfig,
    render_pov_shell,
)
from rag_backend.domain.constants import LANGUAGE_PT
from rag_backend.domain.models import CarouselProject
from rag_backend.domain.protocols.carousel import _RenderOptions

HOOK_FACE_STRATEGY = "hook_face"
_LAYOUT = "pov-hook"


def hook_photo_src(project: CarouselProject) -> str:
    """The slide-1 photo staged in the artifact, or "" (no generated artwork)."""
    if project.hook_asset_id is not None and project.hook_asset_staged_path:
        return project.hook_asset_staged_path
    return ""


def _photo_html(project: CarouselProject, alt: str) -> str:
    src = hook_photo_src(project)
    if not src:
        return ""
    return (
        f'<div class="pov-hook-photo">'
        f'<img src="{html.escape(src, quote=True)}" '
        f'alt="{html.escape(_plain_text_for_attribute(alt), quote=True)}" />'
        f"</div>"
    )


class HookFaceStrategy:
    """Slide 1 of a POV deck: big hook top-left, the owner's cut-out photo."""

    strategy_name = HOOK_FACE_STRATEGY
    display_name = "Hook + Face"
    supported_slide_types = frozenset({"intro"})

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
        language = str(opts.get("language", LANGUAGE_PT))
        heading = str(slide.get("heading") or "")
        sub_raw = str(slide.get("body") or "").strip()
        sub_html = (
            f'<p class="pov-hook-sub">{_render_inline(sub_raw)}</p>' if sub_raw else ""
        )
        return render_pov_shell(
            PovShellConfig(
                slide_number=str(slide.get("number", "1")),
                total_slides=int(str(opts.get("total_slides", 0))),
                copy_inner_html=(
                    f'<h1 class="pov-hook-heading">{_render_inline(heading)}</h1>\n'
                    f"      {sub_html}"
                ),
                layout=_LAYOUT,
                background_html=_photo_html(project, heading),
                footer_extra_html=(
                    f'<span class="s1-swipe">{swipe_text_for(language)}</span>'
                ),
                include_counter=False,
            ),
            project,
        )


__all__ = ["HOOK_FACE_STRATEGY", "HookFaceStrategy", "hook_photo_src"]
