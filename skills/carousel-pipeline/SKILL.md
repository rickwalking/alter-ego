---
name: carousel-pipeline
description: Generate Instagram carousel and blog content. Use when the user says "create a carousel", "create a new social media post", "generate carousel slides", "make an Instagram post", or "create blog content". Executes a 7-phase research-to-visual pipeline producing slides, blog post (bilingual pt-BR/en), design tokens, images, and Instagram caption. Never use for plain text generation without visual content.
version: 1.0.0
---

# Carousel Pipeline

## Purpose

Generate production-ready Instagram carousel content with a complete 7-phase pipeline: research, title optimization, bilingual content synthesis, visual design, image generation, HTML export, and caption creation. Produces a full blog post in Portuguese and English with a self-contained visual design system.

## Prerequisites

Before running, verify:
1. `GEMINI_API_KEY` environment variable is set (for image generation)
2. `CAROUSEL_OUTPUT_DIR` is configured (defaults to `./output/carousels`)
3. Playwright chromium browser is installed (`playwright install chromium`)
4. The backend API is running and accessible

## Critical Rules

- **Language**: Generate blog content in Brazilian Portuguese (informal but professional). NEVER use em dashes in either language.
- **Fact-checking**: Every factual claim must have at least one authoritative source from the research phase. Common trap: conflating *popularized* with *invented*. Example — Uncle Bob popularized the **SOLID acronym**, but LSP is Barbara Liskov's and OCP is Bertrand Meyer's. Always check attribution.
- **Title criteria**: Scroll-stop power, emotional pull, max ~60 chars, concrete over generic. Propose 3 alternatives with rationale if the original title is weak.
- **Image style**: Enforced server-side, not requested via prompt (see Phase 5).
- **Design tokens**: Every blog/carousel gets a unique, self-contained visual identity stored as structured tokens. The frontend is a theme consumer, never hardcoded.
- **Bilingual**: Always generate content in pt-BR (primary) and en (secondary). Store both in `blog_translations`.
- **Fail loudly**: If content synthesis returns unparseable/empty output, **raise** — never silently mark the project `completed` with a stub slide.

## Anti-patterns (learned from broken runs)

| Symptom | Root cause | Fix |
|---------|-----------|-----|
| Content drifts away from the user's actual topic (e.g., Uncle Bob's AI tweet → generic *Clean Coder* content) | User-provided `sources` ignored; DDG-only search returns the broadest-popular results for the topic string | User sources are **authoritative** — scrape first at higher relevance; DDG only supplements |
| Generated images have speech bubbles / warm dojo lighting / grid panels | LLM was allowed to specify style/ratio/layout in `image_prompt` | Treat `image_prompt` as **scene description only**; wrap with mandatory directives server-side (Phase 5) |
| Pipeline marks `completed` but blog is empty and only one intro slide saved | JSON parse failed and code silently fell back to a stub | `_extract_json` strips ```` ```json ```` fences and prose around JSON; on failure, **raise** |
| Slide 5 is a long paragraph floating at the top of an empty canvas | Content LLM returned prose instead of checklist structure | Closing slide must render as **checklist with icons**, not a paragraph (see Phase 3) |
| Intro slide has no hero image | Phase 5 filtered to `slide_type == 'content'` only | Intro + content slides get images; closing + CTA don't |
| Body text feels cramped / closing slide is a wall of prose | The content LLM returned a plain paragraph for a slide that should be a structured list | Require a `features` array on closing (and stat-heavy content) slides; render via `.feature-grid`. Do NOT shrink the font to make prose fit. |
| Intro footer sits right against the subtitle instead of pinned to the bottom | `.s1-main` missing `flex: 1` | Keep `.s1-content { display: flex; flex-direction: column; height: 100% }` AND `.s1-main { flex: 1 }` so the footer gets pushed to the bottom |
| Title/body contains em dashes (`—`/`–`) — the classic AI-writing tell | The content LLM ignores prompt-level bans | Ban em dashes in the prompt AND strip them defensively in the renderer (`_render_inline` replaces `—`/`–` with a period) |
| `**bold**` appears literally instead of bold text | Renderer was treating body as plain text | Run body through an inline renderer that escapes HTML, strips dashes, and converts `**text**` → `<strong>text</strong>` |
| CTA slide is exported at 1080×880 instead of 1080×1350 (crops weirdly in Instagram) | `.cta-slide { height: 100% }` overrode `.slide { height: 1350px }` and collapsed to intrinsic content height because `<body>` had no fixed height | Remove `height: 100%` from `.cta-slide` (and any slide-level class). All six slides must render at **exactly 1080×1350**; Playwright screenshots the element's own bounding box, so any slide with a collapsed height ships wrong to Instagram |

## Workflow

### Phase 1: Research

Dispatch 3-4 research agents IN PARALLEL targeting different source types:

**Source priority:** user-provided `sources` in the generate request are **authoritative primary context**. They are scraped first at `relevance_score=2.0`; broad web search only *supplements* them up to a cap (10 total). Without a user-provided URL, the research phase can drift toward whatever the topic string surfaces (e.g., "Uncle Bob" → broad Clean Code results instead of the specific tweet). **Always pass the source URL when the carousel is about a specific post, tweet, or announcement.**

| Agent | Source Type | Method |
|-------|------------|--------|
| Agent 1 | Twitter/X, primary sources | Playwright MCP `browser_navigate` + `browser_snapshot`. Use the https://xcancel.com/ website and paste the url after the /x/ with the post id or visit the profile because this tool will allow you to scrape the content of the post when X blocks it. |
| Agent 2 | News, blog articles | WebSearch + WebFetch across tech publications |
| Agent 3 | Reddit, community | r/programming, r/ClaudeAI, r/LocalLLaMA, Hacker News |
| Agent 4 | Technical sources | GitHub issues, CVEs, advisories, vendor analyses |

Each agent collects URLs, titles, and extracted content. Store as `ResearchSource` entities linked to the project.

**Server-side search fallback:** the backend uses the `ddgs` Python library (DuckDuckGo client with UA rotation and backend fallbacks). Do **not** try to scrape `google.com/search` or `html.duckduckgo.com/html/` directly from a server — Google blocks headless browsers and DDG's HTML endpoint returns 403 to server IPs.

### Phase 2: Title Optimization

Feed research context + working title to LLM with optimization criteria:
- Scroll-stop power (emotional hook)
- Max ~60 characters
- Concrete > generic
- If original title is weak, propose 3 alternatives with rationale

LLM returns: `{title, subtitle}` or `{title_pt, title_en, subtitle_pt, subtitle_en}`

### Phase 3: Content Synthesis

Generate 6-slide carousel + bilingual blog post:

**Slide structure:**
1. Intro: hook + hero image
2-4. Content: deep information with stats/quotes
5. Closing: actionable takeaways
6. CTA: save + share

LLM returns JSON:
```json
{
  "slides": [{"number": 1, "type": "intro", "heading": "...", "body": "...", "image_prompt": "..."}],
  "blog_pt": "full blog post in pt-BR markdown",
  "blog_en": "full blog post in English markdown",
  "title_pt": "...", "title_en": "...",
  "subtitle_pt": "...", "subtitle_en": "..."
}
```

**JSON parsing tolerance:** Anthropic frequently wraps JSON in ```` ```json ... ``` ```` fences or adds leading/trailing prose. The server uses `_extract_json` which strips fences and extracts the `{...}` substring before parsing. **If parsing still fails, the pipeline raises** — do not fall back to a stub slide. Log the raw response on failure so the prompt can be improved.

**Writing rules:**
- pt-BR: informal Brazilian Portuguese, engaging
- EN: professional, direct, same depth and structure
- NEVER use em dashes in either language
- Short paragraphs (2-4 sentences max)
- `<strong>` for key terms/numbers, `.code-tag` for technical terms

**Slide-type rendering contract (CRITICAL — the LLM must emit content that fits the visual system):**

| Type | Expected body shape | Wrong shape (causes "weird" slide) |
|------|--------------------|------------------------------------|
| `intro` | Hook subtitle, 2-3 sentences | Bullet list, checklist |
| `content` | Dense paragraph with `<strong>` highlights for key terms | Bullet-only slides (unless user asked) |
| `closing` | **Checklist of 4-6 actionable items**, each with an emoji icon (📝 🏗️ ⚙️ 🧪 🗣️). The frontend/HTML renders this via `.check-grid` / `.check-item`. | Paragraph prose (floats at top of empty slide) |
| `cta` | Short punchy title + 2-3 sentence body + save/share buttons | Long essay |

The content LLM must return `closing` slides as an array of checklist items, not as one paragraph. If the LLM returns prose, the frontend will look sparse.

**image_prompt rules (CRITICAL — system wraps it with style directives, describe SCENE ONLY):**
- 1-2 sentences describing a concrete cyberpunk/sci-fi tech scene.
- ❌ **DO NOT** specify style, colors, lighting, panel layouts, or aspect ratio — those are applied by the system wrapper.
- ❌ **DO NOT** request text, words, labels, speech bubbles, signs, or captions in the image.
- ❌ **DO NOT** use metaphorical/cultural settings (dojos, sensei, crossroads, books being held up).
- ✅ **Favor**: monitors, terminals, code streams, neon cityscapes, robots, circuit boards, holographic UI panels, servers, data pipelines, hooded figures at consoles.

Example good prompt: *"A developer in a high-tech command center gestures at three large holographic panels showing a requirements flowchart, a system architecture diagram with interconnected nodes, and a real-time communication feed between human avatars and AI agents."*

Example bad prompt: *"Uncle Bob depicted as a wise sensei in a dojo, speech bubbles with words 'Transparency', 'Responsibility'. Warm amber lighting, manga panel borders."* — metaphorical setting + text in image + style override.

**Tool vocabulary (2024-2026):** When the content mentions AI-assisted development tools, prefer the current landscape: **Claude Code**, **OpenCode**, **BMAD**, **Superpowers**, **Cursor**. GitHub Copilot is still valid but dated on its own.

### Phase 4: Design System

Generate design tokens based on theme:

| Theme | Primary | Accent | Background |
|-------|---------|--------|------------|
| cybersecurity | #ef4444 | #00d4ff | #0a0e17 |
| ai_competition | #3b82f6 | #f59e0b | #0a0e17 |
| developer_skills | #0ac5a8 | #8b5cf6 | #080c12 |
| source_code | #a855f7 | #f97316 | #0c0a14 |
| social_engineering | #f59e0b | #ef4444 | #0a0c14 |

Design tokens include: colors, typography (heading/body/badge fonts), image URLs, layout (badge_label, swipe_text, progress_segments).

Build HTML carousel with inline CSS using these tokens.

**Typography sizing for 1080x1350** — these are the validated original sizes; do NOT downsize. If content feels cramped, the fix is to structure the body (feature grid / stat cards / insight quote), not shrink text:

| Element | Size | Weight |
|---------|------|--------|
| s1-title (intro) | 52px | 800 |
| s1-subtitle | 28px | 400 |
| slide-heading | 50px | 800 |
| body-p | 30px | 400 |
| body-p strong | 30px | 700 (white #fff) |
| cta-title | 52px | 800 |
| cta-body | 31px | 400 |
| hero-img height | 310px (content) / 380px (intro) | — |
| feature-title | 28px | 700 |
| feature-body | 24px | 400 |
| feature-icon | 34px | — |
| insight-card | 26px | 400 italic |
| badge / slide-num | 16px | 700 mono, 3px letter-spacing |

**Feature grid (content + closing slides) — `.feature-grid` / `.feature-item`:**
```css
.feature-grid { display: flex; flex-direction: column; gap: 16px; }
.feature-item {
  display: flex; gap: 20px; align-items: flex-start;
  padding: 22px 24px; border-radius: 16px;
  background: rgba(255,255,255,0.02);
  border: 1px solid var(--primary) at 15% opacity;
}
.feature-icon { font-size: 34px; flex-shrink: 0; }
.feature-title { font-size: 28px; font-weight: 700; color: #fff; }
.feature-body { font-size: 24px; color: var(--text-60); line-height: 1.45; }
```
The content LLM must return `features: [{icon, title, body}]` on the closing slide (and optionally on content slides) so the renderer can emit a structured list instead of a prose wall.

**Intro footer must pin to the bottom** — `.s1-content` uses `display: flex; flex-direction: column; height: 100%` and `.s1-main { flex: 1 }` so the footer (date / "Deslize →") sits at the bottom of the 1350px canvas, not pressed against the subtitle.

**Heading highlights (accent-color spans)** — every slide heading marks 1-2 key words with Markdown `**word**`. The renderer converts `<strong>` inside `.s1-title`, `.slide-heading`, and `.cta-title` to the palette's **accent** color (not white). The rest of the title stays white, so the highlight draws the eye. Examples from the original skill:
- *Código do Claude Code **vazou**. O que descobrimos?*
- *As **features escondidas** que ninguém deveria ver*
- *O **impacto** e a reação da comunidade*
- *O que isso **significa** pra devs*

Never highlight an entire heading or more than two words — the contrast breaks if half the title is accent-colored.

**Structured cards inside content slides** (slides 2-4 in particular) are what separate our carousels from wall-of-text AI posts. Each content slide's `body` can be followed by one of:

| Field | Shape | Renders as | Good fit for |
|---|---|---|---|
| `stats` | `[{value, label, detail?}]` — exactly 3 items | 3-column grid: big accent-color number, muted label, optional baseline detail | benchmark slides, metrics, before/after numbers |
| `features` | `[{icon, title, body}]` — 2-6 items | 1-column (for 2-3 items or closing slides) or 2-column (for 4+ items) grid of rounded cards: emoji icon, bold-white title, muted body with inline `**bold**`/`` `code` `` | architecture pillars, product tiers, capability lists |
| `insight` | `{quote, attribution}` | Italic pullquote with primary-color left border + small attribution | Twitter/blog quotes, primary-source validations |

**One structured extra per slide.** Benchmarks slide → stats. Architecture slide → features. Reaction slide → insight. Don't stack all three — it gets noisy.

**Body has two inline emphasis flavors:**
- `**bold**` — prose emphasis (phrases, stats, names). Renders as `<strong>` which is white in body text and accent-colored in headings.
- `` `code` `` — **technical tokens** (package names, versions, file patterns, commands, config keys, env vars). Renders as `<span class="code-tag">` — a monospace pill in the **primary** palette color with a tinted background. Use when the reader would copy/paste the token into a terminal or config file.

Examples the renderer handles:
- `` `axios`, `2.1.88`, `*.map`, `.npmignore` `` → primary-color code pills
- `**source map de 59.8 MB**` → white bold
- `**Kimi K2.6: 300 Agentes. **12 Horas**.**` → heading highlight in accent

The content LLM must pick the right flavor per token: prose gets `**`, literal code/config gets backticks. Picking the wrong one loses the hierarchy the reference carousels built.

### Phase 5: Image Generation

Use `ImageGenerationTool` (Gemini `gemini-3.1-flash-image-preview`) to generate images for the **intro + content slides** (slides 1-4). Closing (5) and CTA (6) slides do not get images — closing is a checklist, CTA is save/share buttons.

**The LLM's `image_prompt` is a scene description only.** The server wraps it with mandatory style directives before calling Gemini. Do **not** trust the LLM to remember the style rules — bake them into the wrapper.

Server-side wrapper template (`_build_gemini_prompt`):
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

- 2-3 second delay between API calls to avoid rate limits
- Save to `{output_dir}/images/slide_{n}.jpg`
- The carousel HTML references images via relative paths (`images/slide_N.jpg`), which Phase 6 will resolve during Playwright export

### Phase 6: Assembly & Export

Use `CarouselExportTool` (Playwright screenshots) to render each slide:
- Dimensions: 1080x1350 (Instagram portrait)
- Quality: 95 JPEG
- Embed images as base64 data URIs in self-contained HTML

### Phase 7: Caption Generation

Generate Instagram caption with structure:
1. Hook (1-2 lines with emoji)
2. Value promise
3. Comment question
4. Double CTA (save + share)
5. 12-18 hashtags mixing Portuguese and English

## API Endpoints Created

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/carousels | Create carousel project |
| GET | /api/carousels | List all carousels |
| GET | /api/carousels/{id} | Get project details |
| POST | /api/carousels/{id}/generate | Trigger full pipeline |
| GET | /api/carousels/{id}/status | Check status |
| GET | /api/carousels/{id}/slides | Get generated slides |
| GET | /api/carousels/{id}/blog | Get blog (default pt-BR) |
| GET | /api/carousels/{id}/blog/{lang} | Get blog in specific language (pt/en) |
| GET | /api/carousels/{id}/blog/{lang}?include_design=true | Blog + design tokens |
| GET | /api/carousels/{id}/design | Get visual design tokens |
| GET | /api/carousels/{id}/images/{filename} | Serve carousel image |
| POST | /api/carousels/{id}/caption | Generate Instagram caption |
| GET | /api/carousels/{id}/download | Download files (ZIP) |
| DELETE | /api/carousels/{id} | Delete project and files |

## Status Flow

```
PENDING -> RESEARCHING -> DRAFTING -> DESIGNING -> GENERATING_IMAGES -> EXPORTING -> COMPLETED
                                    └-> FAILED (at any phase)
```

## Output

- Carousel project record with bilingual blog, design tokens, and status
- Generated slide images at `{output_dir}/images/`
- Exported JPG files at `{output_dir}/slide_{n}.jpg`
- Design tokens accessible via API for frontend consumption
