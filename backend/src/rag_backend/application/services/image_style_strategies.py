"""Image style strategies.

Each strategy implements `ImageStyleStrategy` and turns an LLM-produced
scene description into a provider- and style-specific prompt. Strategies
never rewrite the scene text — they prepend directives and let the
user-owned scene appear verbatim at the end. This keeps the contract
documented in `tests/features/image_generation_provider.feature`.
"""

from collections.abc import Mapping

from rag_backend.domain.protocols import ImageStyleStrategy


def _palette_fragment(theme: Mapping[str, str]) -> str:
    """Render a single line referencing the project's palette.

    Kept in one place so every strategy speaks the same palette vocabulary.
    Missing keys degrade to empty strings instead of KeyError so a partial
    theme doesn't break image generation.
    """
    primary = theme.get("primary", "")
    accent = theme.get("accent", "")
    background = theme.get("background", "")
    return (
        f"Dark background ({background}) with {primary} and {accent} "
        "neon glow accents, subtle radial light bloom."
    )


def _editorial_palette_fragment(theme: Mapping[str, str]) -> str:
    """Render the palette line for the light/editorial strategy.

    The light counterpart of :func:`_palette_fragment`: a light background
    carrying the primary as ink and the accent as a highlight, with no neon
    glow. Missing keys degrade to empty strings, matching the dark fragment.
    """
    primary = theme.get("primary", "")
    accent = theme.get("accent", "")
    background = theme.get("background", "")
    return (
        f"Light background ({background}) with {primary} ink and {accent} "
        "highlights, matte fills, generous negative space."
    )


class GeminiComicNeonStrategy(ImageStyleStrategy):
    """Comic/manga cyberpunk preset tuned for Gemini 3.1 Flash Image.

    This mirrors the original `_build_gemini_prompt` that shipped with the
    first carousel pipeline — kept as the default so existing projects
    render identically after the DIP refactor.
    """

    @staticmethod
    def wrap(scene: str, theme: Mapping[str, str]) -> str:
        return (
            "Comic/manga style illustration, cyberpunk/sci-fi tech aesthetic, "
            "bold outlines, detailed crosshatching shading, dynamic composition. "
            "Wide panoramic 3:1 ratio. "
            "STRICT: no text, no words, no letters, no labels, no speech bubbles, "
            "no signs, no captions, no code readable as text — purely visual. "
            f"{_palette_fragment(theme)} "
            "Concrete tech scene only — acceptable elements: monitors, terminals, "
            "code streams as abstract glowing glyphs, holographic UI panels, "
            "circuit boards, neon cityscapes, robots, hooded figures, servers, "
            "data pipelines, abstract geometric networks. "
            "No traditional/dojo/warm-lighting/black-and-white/grid-panel layouts. "
            f"Scene: {scene.strip()}"
        )


class OpenAICinematicStrategy(ImageStyleStrategy):
    """Blade Runner / cinematic photoreal preset for gpt-image-2."""

    @staticmethod
    def wrap(scene: str, theme: Mapping[str, str]) -> str:
        return (
            "Cinematic photoreal still frame, anamorphic 2.39:1 composition, "
            "shallow depth of field, volumetric haze, practical neon lighting, "
            "Roger Deakins / Blade Runner 2049 mood — moody, high-contrast, "
            "desaturated base with neon bloom in key lights. "
            "STRICT: no readable text, no logos, no captions, no UI labels, "
            "no watermarks — purely visual storytelling. "
            "ALSO STRICT: no real-world brand names, no celebrity or CEO "
            "likenesses, no company logos, no identifiable product packaging. "
            "Use generic analogies: a rocket ship instead of a named rocket, "
            "a sleek sedan instead of a Tesla, a server room instead of a "
            "named data center, an abstract tech campus instead of a known HQ. "
            f"{_palette_fragment(theme)} "
            f"Scene: {scene.strip()}"
        )


class OpenAIHyperrealStrategy(ImageStyleStrategy):
    """Graphic-novel hyperreal preset — the bake-off winner for gpt-image-2.

    Hyperreal illustration with heavy ink, painterly textures, a touch of
    grain. Keeps the cyberpunk palette but reads more like a comic splash
    page than a photo.
    """

    @staticmethod
    def wrap(scene: str, theme: Mapping[str, str]) -> str:
        return (
            "Hyperreal illustration, graphic-novel splash page aesthetic, "
            "painterly digital ink, heavy chiaroscuro, subtle film grain, "
            "precise anatomy, intricate material detail (metal, glass, "
            "fabric, circuitry), dynamic wide composition. "
            "STRICT: no readable text, no logos, no captions, no UI labels, "
            "no speech bubbles — purely visual. "
            "ALSO STRICT: no real-world brand names, no celebrity or CEO "
            "likenesses, no company logos. Use generic analogies only. "
            f"{_palette_fragment(theme)} "
            f"Scene: {scene.strip()}"
        )


class OpenAIFlatEditorialStrategy(ImageStyleStrategy):
    """Flat editorial vector preset for gpt-image-2.

    The light/editorial counterpart to the dark neon presets: matte vector
    illustration on a light ground, paired with the light palettes
    (risograph, paper_editorial, clinical_mint). Uses the light palette
    fragment so the prompt does not contradict a light background.
    """

    @staticmethod
    def wrap(scene: str, theme: Mapping[str, str]) -> str:
        return (
            "Flat editorial vector illustration, single-weight line art, "
            "matte fills, generous negative space, soft paper grain, calm "
            "magazine-explainer mood. Wide panoramic 3:1 composition. "
            "STRICT: no readable text, no logos, no captions, no UI labels, "
            "no speech bubbles — purely visual. "
            "ALSO STRICT: no real-world brand names, no celebrity or CEO "
            "likenesses, no company logos. Use generic analogies only. "
            f"{_editorial_palette_fragment(theme)} "
            f"Scene: {scene.strip()}"
        )


class OpenAINeoAnimeStrategy(ImageStyleStrategy):
    """Ghost in the Shell / Akira cel-animated preset for gpt-image-2."""

    @staticmethod
    def wrap(scene: str, theme: Mapping[str, str]) -> str:
        return (
            "Cel-animated feature film still, neo-anime aesthetic in the "
            "spirit of Ghost in the Shell and Akira, crisp inked linework, "
            "flat color fills with airbrushed gradients, hand-painted "
            "background mattes, rim-lit characters against neon city haze. "
            "STRICT: no readable text, no logos, no captions, no UI labels, "
            "no speech bubbles — purely visual. "
            "ALSO STRICT: no real-world brand names, no celebrity or CEO "
            "likenesses, no company logos. Use generic analogies only. "
            f"{_palette_fragment(theme)} "
            f"Scene: {scene.strip()}"
        )
