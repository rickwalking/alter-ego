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
- **Fact-checking**: Every factual claim must have at least one authoritative source from the research phase.
- **Title criteria**: Scroll-stop power, emotional pull, max ~60 chars, concrete over generic. Propose 3 alternatives with rationale if the original title is weak.
- **Image style**: Comic/manga style, 3:1 aspect ratio, no text on images, dark background with palette accent colors.
- **Design tokens**: Every blog/carousel gets a unique, self-contained visual identity stored as structured tokens. The frontend is a theme consumer, never hardcoded.
- **Bilingual**: Always generate content in pt-BR (primary) and en (secondary). Store both in `blog_translations`.

## Workflow

### Phase 1: Research

Dispatch 3-4 research agents IN PARALLEL targeting different source types:

| Agent | Source Type | Method |
|-------|------------|--------|
| Agent 1 | Twitter/X, primary sources | Playwright MCP `browser_navigate` + `browser_snapshot` |
| Agent 2 | News, blog articles | WebSearch + WebFetch across tech publications |
| Agent 3 | Reddit, community | r/programming, r/ClaudeAI, r/LocalLLaMA, Hacker News |
| Agent 4 | Technical sources | GitHub issues, CVEs, advisories, vendor analyses |

Each agent collects URLs, titles, and extracted content. Store as `ResearchSource` entities linked to the project.

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

**Writing rules:**
- pt-BR: informal Brazilian Portuguese, engaging
- EN: professional, direct, same depth and structure
- NEVER use em dashes in either language
- Short paragraphs (2-4 sentences max)
- `<strong>` for key terms/numbers, `.code-tag` for technical terms

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

### Phase 5: Image Generation

Use `ImageGenerationTool` (Gemini `gemini-3.1-flash-image-preview`) to generate images for content-heavy slides (typically slides 2-4).

- Style: comic/manga, 3:1 ratio, no text, dark background with palette accents
- 2-3 second delay between API calls to avoid rate limits
- Save to `{output_dir}/images/slide_{n}.jpg`

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