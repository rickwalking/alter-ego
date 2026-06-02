# Design system

Theme resolution, design tokens, typography, and layout CSS for 1080×1350 Instagram portrait slides.

## Theme resolution (creative palette selection)

Each carousel gets a **unique, topic-aware color palette**. The system analyzes project topic, title, subtitle, and niche — not a generic default.

### Resolution order

1. **Brand detection** — If the topic clearly belongs to a known tech brand, use that brand's identity colors:
   - **Anthropic / Claude** → Orange `#ea580c` + Cyan `#22d3ee`
   - **Google / Gemma / Gemini** → Blue `#3b82f6` + Amber `#f59e0b`
   - **OpenAI / GPT / ChatGPT** → Green `#10a37f` + Amber `#f59e0b`
   - **Meta / Llama** → Purple `#8b5cf6` + Teal `#0ac5a8`
   - **Microsoft / Azure / Copilot** → Azure `#0078d4` + Amber `#f59e0b`

2. **Category keyword detection** — If no brand is detected, scan for category keywords:
   - Security/attacks/hacking/vulnerability → **cybersecurity** (Red + Cyan)
   - AI models/competitions/benchmarks → **ai_competition** (Blue + Amber)
   - Dev skills/tutorials/architecture → **developer_skills** (Teal + Purple)
   - Code/leaks/open source/repository → **source_code** (Purple + Orange)
   - Social engineering/phishing/scam → **social_engineering** (Amber + Red)

3. **Fallback** — If nothing matches, default to `ai_competition`.

The content synthesis prompt receives the resolved palette so image prompts can match color mood (warm orange for Anthropic, cool blue for Google, aggressive red for security).

## Theme palettes

| Theme | Primary | Accent | Background |
|-------|---------|--------|------------|
| cybersecurity | `#ef4444` | `#00d4ff` | `#0a0e17` |
| ai_competition | `#3b82f6` | `#f59e0b` | `#0a0e17` |
| developer_skills | `#0ac5a8` | `#8b5cf6` | `#080c12` |
| source_code | `#a855f7` | `#f97316` | `#0c0a14` |
| social_engineering | `#f59e0b` | `#ef4444` | `#0a0c14` |

## Design tokens structure

```json
{
  "colors": {
    "primary": "#3b82f6",
    "accent": "#f59e0b",
    "bg": "#0a0e17",
    "text": "#ffffff",
    "text_muted": "rgba(255,255,255,0.63)",
    "text_dim": "rgba(255,255,255,0.48)",
    "border": "#3b82f633",
    "glow": "#3b82f60D"
  },
  "typography": {
    "font_family_heading": "'Inter', system-ui, -apple-system, sans-serif",
    "font_family_body": "'Inter', system-ui, -apple-system, sans-serif",
    "font_family_badge": "'JetBrains Mono', monospace"
  },
  "images": {
    "hero": "/api/carousels/{id}/images/hero",
    "slides": ["/api/carousels/{id}/images/slide_1"]
  },
  "layout": {
    "badge_label": "AI Education",
    "swipe_text": "Deslize →",
    "progress_segments": 6
  }
}
```

Design tokens include: colors, typography (heading/body/badge fonts), image URLs, layout (badge_label, swipe_text, progress_segments).

The frontend is a **theme consumer** — never hardcode palette values in UI components.

## HTML template requirements

Build self-contained HTML with:

- Inline CSS using design tokens as CSS custom properties
- Embedded images as base64 data URIs (for export)
- Dark background with glow effects
- Fixed **1080×1350** slide dimensions — all six slides at exactly this size
- Progress bars on content slides
- Badge showing niche category on intro slide

**Anti-pattern:** Do not set `height: 100%` on `.cta-slide` or other slide-level classes — it collapses CTA height and exports wrong dimensions. See [`anti-patterns.md`](anti-patterns.md).

## Typography sizing for 1080×1350

Validated original sizes — **do NOT downsize**. If content feels cramped, structure the body (feature grid / stat cards / insight quote), do not shrink text.

| Element | Size | Weight | Notes |
|---------|------|--------|-------|
| s1-title (intro) | 52px | 800 | letter-spacing: -0.02em |
| s1-subtitle | 28px | 400 | |
| slide-heading | 50px | 800 | accent `<strong>` highlights |
| body-p | 30px | 400 | `<strong>` renders white `#fff` |
| cta-title | 52px | 800 | |
| cta-body | 31px | 400 | |
| hero-img height | 310px (content) / 380px (intro) | — | gradient overlay |
| feature-title | 28px | 700 | |
| feature-body | 24px | 400 | |
| feature-icon | 34px | — | |
| insight-card | 26px | 400 italic | |
| badge / slide-num | 16px | 700 mono | 3px letter-spacing |
| stat-number | 42px | 900 | accent color |
| stat-label | 20px | 400 | |
| creator-watermark name | 11px | 700 | |
| creator-watermark handle | 9px | 400 | JetBrains Mono |

## Feature grid CSS

Used for content and closing slides when `features` array is present:

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

## Intro footer layout

Intro footer must pin to the bottom of the 1350px canvas:

```css
.s1-content { display: flex; flex-direction: column; height: 100%; }
.s1-main { flex: 1; }
```

Footer (date / "Deslize →") sits at the bottom, not pressed against the subtitle.

## Heading highlights

See [`text-formatting.md`](text-formatting.md) — accent-color spans on 1-2 words in `.s1-title`, `.slide-heading`, `.cta-title`.
