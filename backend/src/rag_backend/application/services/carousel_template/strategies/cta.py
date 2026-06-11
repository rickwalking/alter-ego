"""CTA centered strategy for the persistent Alter-Ego brand footer."""

import html
from collections.abc import Mapping

from typing_extensions import override

from rag_backend.domain.constants import LANGUAGE_EN
from rag_backend.domain.models import CarouselProject
from rag_backend.domain.protocols.carousel import _RenderOptions

_SLIDE_TYPE_CTA = "cta"
_DEFAULT_CREATOR_NAME = "Pedro Marins"
_DEFAULT_CREATOR_HANDLE = "pedromarins.ai"
_DEFAULT_CREATOR_AVATAR = "images/about-pedro.jpg"
_CREATOR_WEBSITE = "marinssolutions.com"
_LINK_ICON = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
    'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" '
    'aria-hidden="true"><path d="M10 13a5 5 0 0 0 7.54.54l3-3'
    'a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11'
    'a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/></svg>'
)


class CtaCenteredStrategy:
    """Renders the final CTA slide with creator avatar, name, handle, and follow CTA."""

    strategy_name = "cta_centered"
    display_name = "CTA Centered"
    supported_slide_types = frozenset({_SLIDE_TYPE_CTA})

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
        total_slides: int = opts.get("total_slides", 0)  # type: ignore[assignment]
        language: str = opts.get("language", "pt")  # type: ignore[assignment]
        name = html.escape(
            project.creator_name or _DEFAULT_CREATOR_NAME,
            quote=True,
        )
        handle = project.creator_handle or _DEFAULT_CREATOR_HANDLE
        avatar = _resolve_creator_avatar_src(project)
        handle_text = handle if handle.startswith("@") else f"@{handle}"
        handle_html = html.escape(handle_text, quote=True)
        avatar_url = html.escape(avatar, quote=True)
        if language == LANGUAGE_EN:
            cta_text = "Follow for more content like this"
        else:
            cta_text = "Siga para mais conteúdo como esse"
        slide_number = str(slide.get("number", ""))
        return f"""\
  <div class="slide-content slide-closing">
    <div class="closing-card">
      <div class="slide-number">0{slide_number} / {total_slides:02d}</div>
      <div class="closing-avatar">
        <img src="{avatar_url}" alt="{name}" />
      </div>
      <div class="closing-name">{name}</div>
      <div class="closing-handle">{handle_html}</div>
      <div class="closing-website">{_LINK_ICON}{_CREATOR_WEBSITE}</div>
      <p class="closing-cta">{cta_text}</p>
    </div>
  </div>"""


def _resolve_creator_avatar_src(project: CarouselProject) -> str:
    """Prefer staged managed creator asset over legacy avatar URLs."""
    if project.creator_asset_id is not None and project.creator_asset_staged_path:
        return project.creator_asset_staged_path
    if project.creator_avatar_url:
        return project.creator_avatar_url
    return _DEFAULT_CREATOR_AVATAR


__all__ = ["CtaCenteredStrategy"]
