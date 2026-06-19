# Image generation

Rules for Gemini-based slide images. Style is **server-enforced** — the LLM describes scenes only.

## Scope

Generate images for **intro + content slides only** (slides 1-4). Closing (5) and CTA (6) slides do not get images — closing is a checklist layout; CTA is save/share buttons.

**Anti-pattern:** Filtering to `slide_type == 'content'` only skips the intro hero image. See [`anti-patterns.md`](anti-patterns.md).

## Service

Use `ImageGenerationTool` wrapping Google Gemini `gemini-3.1-flash-image-preview` via `google-genai` SDK.

Requires `GEMINI_API_KEY` environment variable.

## image_prompt rules (scene description only)

The LLM's `image_prompt` is a **scene description only**. The server wraps it with mandatory style directives before calling Gemini. Do **not** trust the LLM to remember style rules — bake them into the wrapper.

- 1-2 sentences describing a concrete cyberpunk/sci-fi tech scene
- ❌ **DO NOT** specify style, colors, lighting, panel layouts, or aspect ratio
- ❌ **DO NOT** request text, words, labels, speech bubbles, signs, or captions
- ❌ **DO NOT** use metaphorical/cultural settings (dojos, sensei, crossroads, books being held up)
- ✅ **Favor:** monitors, terminals, code streams, neon cityscapes, robots, circuit boards, holographic UI panels, servers, data pipelines, hooded figures at consoles

Full contract and examples: [`content-contracts.md`](content-contracts.md#image_prompt-contract-scene-description-only).

## Server-side wrapper template

`_build_gemini_prompt`:

```
Comic/manga style illustration, cyberpunk/sci-fi tech aesthetic, bold outlines,
detailed crosshatching shading, dynamic composition. Wide panoramic 3:1 ratio.
STRICT: no text, no words, no letters, no labels, no speech bubbles, no signs,
no captions, no code readable as text — purely visual.
Dark background (<theme.background>) with <theme.primary> and <theme.accent>
neon glow accents, subtle radial light bloom.
Concrete tech scene only — acceptable elements: monitors, terminals, code
streams as abstract glowing glyphs, holographic UI panels, circuit boards,
neon cityscapes, robots, hooded figures, servers, data pipelines, abstract
geometric networks.
No traditional/dojo/warm-lighting/black-and-white/grid-panel layouts.
Scene: <LLM's scene description>
```

## Rate limiting and storage

- Add **2-3 second delay** between API calls to avoid rate limits
- Save to `{output_dir}/images/slide_{n}.jpg`
- Carousel HTML references images via relative paths (`images/slide_N.jpg`); Phase 6 export resolves these during Playwright screenshot

## Regeneration (editorial workflow)

Per-slide regeneration instructions re-invoke `render_images` for selected slides only — do not regenerate the full carousel unless requested.
