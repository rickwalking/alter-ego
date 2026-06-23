"""Generation-time palette resolver over the root + custom union (AE-0269).

`resolve_theme` stays a PURE registry/snapshot reader on the render path. THIS
service runs ONCE per generation (where a repository is available): it resolves
``project.theme`` — a root key, the ``"auto"`` sentinel, or a custom-palette
UUID — into a concrete palette, derives the image style from the mode (D3, so a
light palette can never get a dark strategy), and produces the snapshot the
carousel freezes (D9).

Reliability (skeptical G2): the repository sits on the generation path, which
``resolve_theme`` previously could not fail on. Any repository error degrades to
**registry-only** resolution (logged + counted) instead of raising — a custom
palette may be missed, but generation never 500s.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

import structlog

from rag_backend.application.services.carousel.theme_resolver import (
    _detect_brand,
    _detect_category,
    _hash_to_theme_key,
    _score_keyword_list,
)
from rag_backend.domain.constants import (
    BRAND_PALETTES,
    CAROUSEL_THEMES,
    IMAGE_STYLE_DEFAULT,
    IMAGE_STYLE_FLAT_EDITORIAL,
    LIGHT_THEME_KEYS,
)
from rag_backend.domain.constants.palette_types import PaletteMode
from rag_backend.domain.models import CarouselProject
from rag_backend.domain.models.palette import CustomPalette
from rag_backend.domain.protocols.palette import PaletteRepository

_logger = structlog.get_logger(__name__)

_THEME_AUTO = "auto"


@dataclass(frozen=True)
class ResolvedPalette:
    """A concretely resolved palette + the style derived from its mode."""

    primary: str
    accent: str
    background: str
    mode: str
    image_style: str
    resolved_ref: str

    def as_snapshot(self, resolved_at: str) -> dict[str, str]:
        """The JSON written to ``carousel_projects.theme_snapshot`` (D9)."""
        return {
            "primary": self.primary,
            "accent": self.accent,
            "background": self.background,
            "mode": self.mode,
            "resolved_ref": self.resolved_ref,
            "resolved_at": resolved_at,
        }


def _derive_image_style(mode: str) -> str:
    """Light palettes pair with the editorial style; dark with the default (D3)."""
    if mode == PaletteMode.LIGHT.value:
        return IMAGE_STYLE_FLAT_EDITORIAL
    return IMAGE_STYLE_DEFAULT


def _root_mode(key: str) -> str:
    """Mode of a root palette key (light if in the light set, else dark)."""
    if key in LIGHT_THEME_KEYS:
        return PaletteMode.LIGHT.value
    return PaletteMode.DARK.value


def _root_resolved(key: str, colors: dict[str, str]) -> ResolvedPalette:
    mode = _root_mode(key)
    return ResolvedPalette(
        primary=colors["primary"],
        accent=colors["accent"],
        background=colors["background"],
        mode=mode,
        image_style=_derive_image_style(mode),
        resolved_ref=key,
    )


def _custom_resolved(palette: CustomPalette) -> ResolvedPalette:
    mode = palette.mode.value
    return ResolvedPalette(
        primary=palette.palette.primary,
        accent=palette.palette.accent,
        background=palette.palette.background,
        mode=mode,
        image_style=_derive_image_style(mode),
        resolved_ref=str(palette.id),
    )


def _as_uuid(ref: str) -> UUID | None:
    try:
        return UUID(ref)
    except ValueError:
        return None


class PaletteResolverService:
    """Resolves a project's theme over root (registry) + custom (DB)."""

    def __init__(self, repo: PaletteRepository) -> None:
        self._repo = repo

    async def resolve(self, project: CarouselProject) -> ResolvedPalette:
        """Resolve ``project.theme`` to a concrete palette (never raises)."""
        try:
            return await self._resolve_union(project)
        except Exception:  # degrade to registry, never fail generation (G2)
            _logger.warning(
                "palette_resolve_fallback_registry_only",
                theme=project.theme,
                project_id=str(project.id),
            )
            return _registry_only(project)

    async def _resolve_union(self, project: CarouselProject) -> ResolvedPalette:
        ref = project.theme
        custom_id = _as_uuid(ref) if ref != _THEME_AUTO else None
        if custom_id is not None:
            found = await self._repo.get_by_id(custom_id)
            if found is not None:
                return _custom_resolved(found)
            return _registry_only(project)

        if ref != _THEME_AUTO:
            return _root_resolved(ref, _root_colors(ref))

        return await self._resolve_auto(project)

    async def _resolve_auto(self, project: CarouselProject) -> ResolvedPalette:
        text = _analysis_text(project)
        brand = _detect_brand(text)
        if brand is not None:
            return _root_resolved(
                brand, BRAND_PALETTES.get(brand, _fallback_colors(text))
            )

        custom = _match_custom(text, await self._repo.list_active())
        if custom is not None:
            return _custom_resolved(custom)

        category = _detect_category(text)
        if category is not None:
            return _root_resolved(category, _root_colors(category))

        key = _hash_to_theme_key(text)
        return _root_resolved(key, CAROUSEL_THEMES[key])


def _registry_only(project: CarouselProject) -> ResolvedPalette:
    """Pure root resolution — the degraded path + non-custom themes."""
    ref = project.theme
    if ref != _THEME_AUTO and _as_uuid(ref) is None:
        return _root_resolved(ref, _root_colors(ref))
    text = _analysis_text(project)
    brand = _detect_brand(text)
    if brand is not None:
        return _root_resolved(brand, BRAND_PALETTES.get(brand, _fallback_colors(text)))
    category = _detect_category(text)
    if category is not None:
        return _root_resolved(category, _root_colors(category))
    key = _hash_to_theme_key(text)
    return _root_resolved(key, CAROUSEL_THEMES[key])


def _analysis_text(project: CarouselProject) -> str:
    return " ".join([project.topic or "", project.title or "", project.niche or ""])


def _root_colors(key: str) -> dict[str, str]:
    first_key = next(iter(CAROUSEL_THEMES))
    return CAROUSEL_THEMES.get(key, CAROUSEL_THEMES[first_key])


def _fallback_colors(text: str) -> dict[str, str]:
    return CAROUSEL_THEMES[_hash_to_theme_key(text)]


def _match_custom(text: str, customs: list[CustomPalette]) -> CustomPalette | None:
    """Highest-scoring active custom palette by keyword match, or None."""
    lowered = text.lower()
    best: CustomPalette | None = None
    best_score = 0
    for palette in customs:
        score = _score_keyword_list(lowered, palette.keywords)
        if score > best_score:
            best_score = score
            best = palette
    return best
