"""CTA-follow strategy: one specific action by goal (AE-0376, POV last slide)."""

import html
from collections.abc import Mapping

from typing_extensions import override

from rag_backend.application.services.carousel_template.cta_copy import cta_copy
from rag_backend.application.services.carousel_template.pov_shell import handle_html
from rag_backend.application.services.carousel_template.slide_number import (
    format_slide_counter,
)
from rag_backend.application.services.carousel_template.strategies.cta import (
    resolve_creator_avatar_src,
)
from rag_backend.domain.constants import LANGUAGE_PT
from rag_backend.domain.constants.carousel_cta import DEFAULT_CTA_HANDLE
from rag_backend.domain.models import CarouselProject
from rag_backend.domain.protocols.carousel import _RenderOptions

CTA_FOLLOW_STRATEGY = "cta_follow"
_DEFAULT_CREATOR_NAME = "Pedro Marins"
# Kept small: the goal is followers, not site visits (growth plan 16.3 F).
_CREATOR_WEBSITE = "marinssolutions.com"


class CtaFollowStrategy:
    """Avatar, handle and the CTA goal's sentence in large type."""

    strategy_name = CTA_FOLLOW_STRATEGY
    display_name = "CTA Follow"
    supported_slide_types = frozenset({"cta"})

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
        total_slides = int(str(opts.get("total_slides", 0)))
        name = html.escape(project.creator_name or _DEFAULT_CREATOR_NAME, quote=True)
        avatar = html.escape(resolve_creator_avatar_src(project), quote=True)
        sentence = cta_copy(
            project.cta_goal, language, project.creator_handle or DEFAULT_CTA_HANDLE
        )
        counter = format_slide_counter(str(slide.get("number", "")), total_slides)
        return f"""\
  <div class="pov-solid"></div>
  <div class="slide-content slide-closing pov-cta">
    <div class="closing-card creator-card pov-cta-card">
      <div class="slide-number">{counter}</div>
      <p class="pov-cta-sentence">{html.escape(sentence, quote=True)}</p>
      <div class="closing-avatar"><img src="{avatar}" alt="{name}" /></div>
      <div class="closing-name">{name}</div>
      <div class="closing-handle">{handle_html(project)}</div>
      <div class="pov-cta-website">{_CREATOR_WEBSITE}</div>
    </div>
  </div>"""


__all__ = ["CTA_FOLLOW_STRATEGY", "CtaFollowStrategy"]
