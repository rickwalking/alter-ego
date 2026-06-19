# Content contracts

Return shapes and per-slide structure rules. Enforced in Python validators and HTML renderers — prompts must align with these contracts.

## Input schema (workflow request)

```yaml
title: string           # Working title (MUST improve if weak)
audience: string        # e.g., "AI, software developers, architects"
niche: string           # e.g., "AI/Tech", "Cybersecurity"
slides: string          # e.g., "1 intro, 3 content, 1 closing, 1 cta"
aspect_ratio: string    # Default: "1080x1350 (Instagram portrait)"
sources: list[string]   # URLs to X posts, GitHub issues, blog posts
language: string        # Default: "pt-BR" (Brazilian Portuguese)
generate_images: bool   # Default: true
```

## Content synthesis JSON return shape

The LLM MUST return JSON with both languages:

```json
{
  "slides": [
    {"number": 1, "type": "intro", "heading": "...", "body": "...", "image_prompt": "..."}
  ],
  "blog_pt": "# Title\n\nFull blog post in Brazilian Portuguese markdown...",
  "blog_en": "# Title\n\nFull blog post in English markdown...",
  "title_pt": "Portuguese Title",
  "title_en": "English Title",
  "subtitle_pt": "Portuguese Subtitle",
  "subtitle_en": "English Subtitle"
}
```

Alternate title shape (single-locale projects): `{title, subtitle}` or `{title_pt, title_en, subtitle_pt, subtitle_en}`.

**Parsing:** See [`critical-rules.md`](critical-rules.md) — fail loudly on parse failure; never stub.

## Slide structure (7 slides)

| # | Type | Content | Image |
|---|------|---------|-------|
| 1 | `intro` | Hook + thesis statement | Hero image |
| 2 | `summary` | One heading plus three compact narrative points | Supporting visual |
| 3 | `content` | Key insight #1 with one structured extra | Supporting visual |
| 4 | `content` | Key insight #2 with one structured extra | Supporting visual |
| 5 | `content` | Key insight #3 with one structured extra | Supporting visual |
| 6 | `closing` | Three or four concise actions | Supporting visual |
| 7 | `cta` | Save + share prompt + creator identity | Creator avatar |

Canonical values live in `contracts/hero_lower_third_v1.yaml`.

## Slide-type rendering contract

| Type | Expected body shape | Wrong shape (causes broken slide) |
|------|--------------------|-----------------------------------|
| `intro` | Hook subtitle, 2-3 sentences | Bullet list, checklist |
| `content` | Dense paragraph with `<strong>` highlights for key terms | Bullet-only slides (unless user asked) |
| `closing` | **Checklist of 3-4 actionable items**, each with a Lucide `icon_name` (`chart-column`, `book-open`, `wrench`, `flask-conical`, etc.). Renders via `.check-grid` / `.check-item` or `.feature-grid`. | Paragraph prose (floats at top of empty slide) |
| `cta` | Short punchy title + 2-3 sentence body + save/share buttons | Long essay |

The content LLM must return `closing` slides as structured items (`features: [{icon_name, title, body}]`), not as one paragraph.

## Structured extras (one per slide)

Each content slide's `body` can be followed by **one** structured extra — do not stack all three on the same slide.

| Field | Shape | Renders as | Good fit for |
|-------|-------|------------|--------------|
| `stats` | `[{value, label, detail?}]` — exactly 3 items | 3-column grid: big accent-color number, muted label, optional baseline detail | benchmark slides, metrics, before/after numbers |
| `features` | `[{icon_name, title, body}]` — 2-4 items | 1-column (2-3 items or closing) or 2-column (4 items) grid of rounded cards | architecture pillars, product tiers, capability lists |
| `insight` | `{quote, attribution}` | Italic pullquote with primary-color left border + small attribution | Twitter/blog quotes, primary-source validations |

**Lucide allowlist:** `chart-column`, `book-open`, `newspaper`, `brain`, `target`, `eye`, `message-circle`, `shield-check`, `wrench`, `flask-conical`. Use `icon_name`, not emoji or raw SVG.

**Mapping:** Benchmarks slide → `stats`. Architecture slide → `features`. Reaction slide → `insight`.

The content LLM must return `features: [{icon_name, title, body}]` on the closing slide (and optionally on content slides) so the renderer emits a structured list instead of a prose wall.

## ResearchSource entity

Store each source as a `ResearchSource` linked to the project:

| Field | Description |
|-------|-------------|
| `source_url` | The URL |
| `source_type` | `twitter` / `blog` / `reddit` / `github` / `news` / `documentation` |
| `title` | Page title |
| `extracted_content` | Key content (max 10000 chars) |
| `relevance_score` | 0.0–2.0 (user sources: 2.0) |

## image_prompt contract (scene description only)

See [`image-generation.md`](image-generation.md) for full rules. Summary:

- 1-2 sentences describing a concrete cyberpunk/sci-fi tech scene
- ❌ DO NOT specify style, colors, lighting, panel layouts, or aspect ratio
- ❌ DO NOT request text, words, labels, speech bubbles, signs, or captions
- ❌ DO NOT use metaphorical/cultural settings (dojos, sensei, crossroads, books being held up)
- ✅ Favor: monitors, terminals, code streams, neon cityscapes, robots, circuit boards, holographic UI panels, servers, data pipelines, hooded figures at consoles

**Good:** *"A developer in a high-tech command center gestures at three large holographic panels showing a requirements flowchart, a system architecture diagram with interconnected nodes, and a real-time communication feed between human avatars and AI agents."*

**Bad:** *"Uncle Bob depicted as a wise sensei in a dojo, speech bubbles with words 'Transparency', 'Responsibility'. Warm amber lighting, manga panel borders."*

## Tool vocabulary (2024-2026)

When content mentions AI-assisted development tools, prefer the current landscape: **Claude Code**, **OpenCode**, **BMAD**, **Superpowers**, **Cursor**. GitHub Copilot is still valid but dated on its own.
