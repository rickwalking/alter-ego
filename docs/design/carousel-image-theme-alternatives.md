# Carousel image — color & theme alternatives (draft)

**Why:** today every palette in `backend/src/rag_backend/domain/constants/carousel_themes.py`
is **dark-background neon** (`#0a0e17`-ish bg + saturated primary/accent), and every image
preset (`image_style_strategies.py`) is **tech/cyberpunk** ("Concrete tech scene only"). That
is one strong look, but it limits visual range. Below are drop-in palette alternatives (same
`{primary, accent, background}` schema, so they slot straight into `CAROUSEL_THEMES`) paired
with a **style direction** for the matching image strategy.

> Pairing model (see the brand+backdrop ticket): the **palette** is the brand-locked layer
> (fed to `strategy.wrap(scene, theme)` via `_palette_fragment`); the **style direction** is a
> per-preset strategy variant; the **scene/backdrop** stays the per-slide variable. Adding a
> palette here does NOT require touching the brand lock.

## A. Stay-dark variants (same energy, new range)

| # | Name | primary | accent | background | Mood / when |
|---|------|---------|--------|-----------|-------------|
| 1 | Plasma Magenta | `#ec4899` | `#22d3ee` | `#0a0a14` | bold, provocative, "hot take" topics |
| 2 | Acid Lime | `#a3e635` | `#06b6d4` | `#0b0f0a` | energetic, dev-tooling, hacker vibe |
| 3 | Royal Gold | `#fbbf24` | `#7c3aed` | `#0c0a14` | premium, "deep dive", authority |
| 4 | Ember Crimson | `#f43f5e` | `#fb923c` | `#140a0c` | urgent, controversy, breaking news |

**Style direction (dark):** keep the Neo-Anime / comic-neon directives, swap the
`_palette_fragment` glow colors to the pair above. No change to the "no text / tech scene" lock.

## B. Light & editorial (breaks the dark-only mold — biggest visual gain)

| # | Name | primary (ink) | accent | background | Mood / when |
|---|------|---------------|--------|-----------|-------------|
| 5 | Paper Editorial | `#111827` | `#2563eb` | `#f7f5f0` | credible, magazine/long-form, "analysis" |
| 6 | Warm Sand | `#1c1917` | `#ea580c` | `#faf6ef` | human, approachable, founder voice |
| 7 | Clinical Mint | `#0f172a` | `#0d9488` | `#f0fdfa` | calm, explainer, health/process |

**Style direction (light):** a *new* `*FlatEditorialStrategy` — "Flat editorial vector
illustration, generous negative space, single-weight line art, matte fills, soft paper grain.
STRICT: no text. Light background ({background}) with {primary} ink and {accent} highlights."
This is the alternative that most changes the feel — worth one preset.

## C. Duotone / restrained (high-contrast, low-noise)

| # | Name | primary | accent | background | Mood / when |
|---|------|---------|--------|-----------|-------------|
| 8 | Mono Indigo | `#6366f1` | `#e5e7eb` | `#0b0b14` | minimalist, technical, "less is more" |
| 9 | Blueprint | `#38bdf8` | `#f8fafc` | `#0a192f` | schematic, architecture, how-it-works |
| 10 | Risograph | `#ff5c39` | `#1d4ed8` | `#fbf7f0` | retro-print, two-ink, design-forward |

**Style direction (duotone):** "Two-tone {primary}/{accent} screenprint, halftone texture,
hard shapes, no gradients, no text." Maps cleanly onto an OpenAI strategy variant.

## D. Locale / backdrop tints (ties to the brand+backdrop feature)

When a project sets a custom backdrop (e.g. *Rio de Janeiro*), shift the palette to read the
setting while the **style stays locked**:

| # | Name | primary | accent | background | Backdrop it complements |
|---|------|---------|--------|-----------|-------------------------|
| 11 | Carioca Dusk | `#fb7185` | `#22d3ee` | `#10131f` | Rio skyline at golden hour, Sugarloaf silhouette |
| 12 | Tropical Noir | `#34d399` | `#fbbf24` | `#0a1410` | Atlantic-forest greens, Guanabara Bay |

## How to wire these (low-risk increments)

1. **Palettes only (T1):** add chosen entries to `CAROUSEL_THEMES` + the theme `combobox` /
   `theme_resolver.py`. Zero image-pipeline change — the existing strategies already read
   `theme` colors via `_palette_fragment`. Ship 4–6 first, measure.
2. **One light preset (T2):** add `*FlatEditorialStrategy` to `image_style_strategies.py` +
   register in `image_provider_registry.py` + `SUPPORTED_IMAGE_COMBOS`. The single highest-impact
   visual addition.
3. **Backdrop tints (depends on the brand+backdrop ticket):** the palette auto-selects from the
   chosen backdrop.

> Best produced/tuned with impeccable's `/colorize` + `/palette` once it's loaded in the
> session — this draft is the seed; `/palette.mjs` can refine each into OKLCH-balanced ramps.
