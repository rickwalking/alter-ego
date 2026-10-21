"""Carousel defaults for GrokBot topics.

Pure rules: the image presets the scout may pick, the simple-words checks
on audience, niche and brief, the fallback image guidance, and the review
line the owner sees. The backend always uses the OpenAI image model and the
``auto`` palette theme, so neither is part of the scout contract.

The POV preset needs the owner's photo, so the Radar IA scout never picks it; POV
autopilot runs set it themselves. The scout presets are derived from
``SUPPORTED_IMAGE_COMBOS`` so a new preset cannot drift, and the default style matches
the API and the wizard (flat editorial). The autopilot rotates the palette per São Paulo
day instead of ``auto``, which put nearly every AI topic on the same blue/amber theme;
only dark built-in themes rotate, so neo-anime art and the POV scrim stay legible.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from rag_backend.domain.constants import (
    IMAGE_MODEL_OPENAI,
    IMAGE_STYLE_DEFAULT,
    IMAGE_STYLE_NEO_ANIME,
    IMAGE_STYLE_POV_EDITORIAL,
    SUPPORTED_IMAGE_COMBOS,
)
from rag_backend.modules.autopilot.carousel_constants import (
    BRIEF_STOP_WORDS,
    GUIDANCE_BACKGROUND_TEMPLATE,
    GUIDANCE_JOIN,
    GUIDANCE_NEO_ANIME,
    GUIDANCE_STYLE_NEUTRAL,
    LABEL_AUDIENCE,
    LABEL_NICHE,
    LABEL_STYLE,
    PROFILE_LINE_TEMPLATE,
    PROFILE_SEPARATOR,
    REASON_AUDIENCE_NOT_SIMPLE,
    REASON_BRIEF_NOT_SIMPLE,
    REASON_BRIEF_OFF_THEME,
    REASON_IMAGE_STYLE_UNSUPPORTED,
    REASON_NICHE_NOT_SIMPLE,
    SIMPLE_BRIEF_MAX_CHARS,
    SIMPLE_WORDS_MAX,
    SIMPLE_WORDS_MIN,
)
from rag_backend.modules.autopilot.constants import DAILY_CAP_TIMEZONE
from rag_backend.modules.autopilot.domain.topic_text import tokens

POV_ONLY_IMAGE_STYLES: frozenset[str] = frozenset({IMAGE_STYLE_POV_EDITORIAL})

SCOUT_IMAGE_STYLES: frozenset[str] = frozenset(
    style
    for model, style in SUPPORTED_IMAGE_COMBOS
    if model == IMAGE_MODEL_OPENAI and style not in POV_ONLY_IMAGE_STYLES
)

DEFAULT_IMAGE_STYLE = IMAGE_STYLE_DEFAULT


@dataclass(frozen=True, kw_only=True)
class CarouselText:
    """The proposal fields the simple-words rules read, already stripped."""

    title: str
    audience: str
    niche: str
    brief: str
    image_style: str


@dataclass(frozen=True, kw_only=True)
class GuidanceRequest:
    """Inputs for the image guidance sent to the carousel."""

    image_style: str
    niche: str
    image_guidance: str | None


def carousel_reason(text: CarouselText) -> str | None:
    """The first carousel-default rule the proposal breaks, or None."""
    for reason, passes in _RULES:
        if not passes(text):
            return reason
    return None


def _brief_is_short(text: CarouselText) -> bool:
    return len(text.brief) <= SIMPLE_BRIEF_MAX_CHARS


def is_supported_style(style: str) -> bool:
    """True when ``style`` is one of the scout's OpenAI presets."""
    return style in SCOUT_IMAGE_STYLES


def is_simple(value: str) -> bool:
    """True for one to three whitespace-separated words."""
    count = len(value.split())
    return SIMPLE_WORDS_MIN <= count <= SIMPLE_WORDS_MAX


def theme_keywords(title: str) -> frozenset[str]:
    """Casefolded title words that are not stop words."""
    return tokens(title) - BRIEF_STOP_WORDS


def brief_on_theme(title: str, brief: str) -> bool:
    """True when the brief names a title keyword, or the title has none."""
    keywords = theme_keywords(title)
    if not keywords:
        return True
    return not keywords.isdisjoint(tokens(brief))


_RULES: tuple[tuple[str, Callable[[CarouselText], bool]], ...] = (
    (REASON_IMAGE_STYLE_UNSUPPORTED, lambda text: is_supported_style(text.image_style)),
    (REASON_AUDIENCE_NOT_SIMPLE, lambda text: is_simple(text.audience)),
    (REASON_NICHE_NOT_SIMPLE, lambda text: is_simple(text.niche)),
    (REASON_BRIEF_NOT_SIMPLE, _brief_is_short),
    (REASON_BRIEF_OFF_THEME, lambda text: brief_on_theme(text.title, text.brief)),
)


def image_guidance_for(request: GuidanceRequest) -> str:
    """The scout's guidance, or the template for the style and niche."""
    if request.image_guidance:
        return request.image_guidance
    lead = GUIDANCE_STYLE_NEUTRAL
    if request.image_style == IMAGE_STYLE_NEO_ANIME:
        lead = GUIDANCE_NEO_ANIME
    background = GUIDANCE_BACKGROUND_TEMPLATE.format(niche=request.niche)
    return GUIDANCE_JOIN.join((lead, background))


def profile_line(audience: str, niche: str, image_style: str) -> str:
    """``Audience: … · Niche: … · Style: …``. Empty when nothing is known."""
    if not (audience or niche or image_style):
        return ""
    return PROFILE_LINE_TEMPLATE.format(
        audience_label=LABEL_AUDIENCE,
        audience=audience,
        niche_label=LABEL_NICHE,
        niche=niche,
        style_label=LABEL_STYLE,
        style=image_style,
    )


def with_profile(profile: str, body: str) -> str:
    """Put the profile line above the review body."""
    if not profile:
        return body
    return f"{profile}{PROFILE_SEPARATOR}{body}"


AUTOPILOT_THEME_ROTATION: tuple[str, ...] = (
    "developer_skills",
    "plasma_magenta",
    "ember_crimson",
    "blueprint",
    "source_code",
    "acid_lime",
    "mono_indigo",
    "cybersecurity",
    "social_engineering",
)


def rotated_theme(moment: datetime) -> str:
    """The palette of the São Paulo day containing ``moment``."""
    day = moment.astimezone(ZoneInfo(DAILY_CAP_TIMEZONE)).date()
    return AUTOPILOT_THEME_ROTATION[day.toordinal() % len(AUTOPILOT_THEME_ROTATION)]
