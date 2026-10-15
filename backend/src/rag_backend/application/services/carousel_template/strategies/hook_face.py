"""Hook-face strategy: the owner's photo + a big hook (AE-0376, POV slide 1).

PR #106 review: the photo is never optional. A missing or unreadable photo
raises ``HookPhotoError`` instead of silently rendering slide 1 without it.
"""

import html
import os
from collections.abc import Mapping
from pathlib import Path

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
from rag_backend.domain.constants.content_mode import (
    ERR_HOOK_PHOTO_MISSING,
    ERR_HOOK_PHOTO_UNREADABLE,
)
from rag_backend.domain.models import CarouselProject
from rag_backend.domain.protocols.carousel import _RenderOptions

HOOK_FACE_STRATEGY = "hook_face"
_LAYOUT = "pov-hook"


class HookPhotoError(RuntimeError):
    """Slide 1 of a POV deck cannot render: its photo is missing or unreadable."""

    def __init__(self, code: str, project_id: str) -> None:
        super().__init__(f"{code}: project {project_id}")
        self.code = code
        self.project_id = project_id


def hook_photo_src(project: CarouselProject) -> str:
    """The slide-1 photo staged in the artifact; raises when it is unusable.

    The staged path is relative to the project's output dir. When the output
    dir is known the file must exist and be readable there.
    """
    staged = project.hook_asset_staged_path
    if project.hook_asset_id is None or not staged:
        raise HookPhotoError(ERR_HOOK_PHOTO_MISSING, str(project.id))
    if project.output_dir and not _readable(Path(project.output_dir) / staged):
        raise HookPhotoError(ERR_HOOK_PHOTO_UNREADABLE, str(project.id))
    return staged


def _readable(path: Path) -> bool:
    return path.is_file() and os.access(path, os.R_OK)


def _photo_html(project: CarouselProject, alt: str) -> str:
    src = hook_photo_src(project)
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


__all__ = [
    "HOOK_FACE_STRATEGY",
    "HookFaceStrategy",
    "HookPhotoError",
    "hook_photo_src",
]
