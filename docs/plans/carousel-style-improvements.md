# Carousel Style Improvement Plan (Research-Backed)

**Date:** 2026-06-04
**Sources:** design-system.md, PRODUCT.md, Instagram carousel research report, web research (Socialinsider 35M-post study 2026, Hootsuite, Sprout Social, Later, Buffer, Metricool 2026, Search Engine Journal, Foundation Inc)

---

## What's working well ✅

- Portrait 1080×1350 — research confirms highest engagement format
- Swipe prompt on slide 1 — only 5% of carousels use this; lifts engagement ~9%
- Decorative bg images with empty alt — correct accessibility pattern
- AI-generated cyberpunk imagery — on-brand per PRODUCT.md
- Font sizes now consistent across all slides

---

## Improvement Proposals (Priority Order)

### P1: Give slide 7 a hero-bg background image

**Research verdict:** ✅ STRONG YES

Top carousels consistently keep color palette and visual style across all slides, including the closing CTA. A plain dark closing slide breaks the visual narrative established by slides 1-6.

**Implementation:** Use the same full-bleed AI-generated bg image + gradient overlay pattern for slide 7. The avatar/name/handle/CTA text sits over the background, maintaining visual continuity. This also matches how top brand accounts (Canva, Mel Robbins) structure their closers.

**Relevant files:** `neon_slide_styles.py` (`.closing-*` CSS → hero-bg wrapper), `slides.py` (CTA renderer)

---

### P2: Remove watermark from slides 3-6, keep only on slide 2

**Research verdict:** ✅ CONFIRMED EXCESSIVE

5 watermark appearances across slides 2-6 is too many. Watermarks compete with content and feel promotional. Best practice: brand element on first content slide (slide 2), consistent palette/fonts on others, avatar again on closing slide (slide 7).

**Implementation:** Remove `watermark_html` from `_render_content_slide` and `_render_closing_slide`. Keep it only on `_render_summary_slide` (slide 2). Slide 7 already has its own avatar treatment.

**Relevant files:** `slides.py` (render functions), `html_template.py` (watermark generation)

---

### P3: Convert long paragraph body text into structured layouts

**Research verdict:** ✅ STRONG YES — highest engagement opportunity

Structured layouts (stat cards, numbered lists, feature grids, insight quote cards) significantly outperform plain text paragraphs. Carousels with mixed formats create visual rhythm and keep users swiping.

**Per design-system.md:** "If content feels cramped, structure the body (feature grid / stat cards / insight quote), do not shrink text."

**Affected slides:**
- **Slide 4** (longest text, 4 points) → 4 feature grid items or 4 stat cards
- **Slide 5** (numbered list "1-5" in paragraph form) → proper numbered feature grid
- **Slide 6** (action list) → bulleted structure

**Implementation:** Add structured layout variants in `slides.py`: feature grid renderer, stat card renderer, numbered list renderer. Each with dedicated CSS in `neon_slide_styles.py`.

---

### P4: Expand to 10 slides (conditional on content)

**Research verdict:** ⚠️ CONDITIONAL — worth it only if content needs the depth

No current (2025-2026) large-scale study directly compares 7 vs 10 slides. The 10-slide finding is from 2023 (Foundation Inc). Current consensus: "content quality > slide count." However:
- Carousels are the #1 format for saves — more slides = more save-worthy surface area
- Educational/list-style content benefits most from more slides
- Instagram is adding per-slide analytics, enabling future optimization

**If expanded:** Split slide 4 (4 distinct points → 4 slides) or slide 5 (5 numbered steps → 5 slides). This naturally reaches 10 slides, keeps each slide focused on one idea.

---

### P5: Add directional CTAs on slides 1-2 and primary action CTA on slide 7

**Research verdict:** ✅ SUPPORTED

"Swipe left" messaging boosts engagement from 1.83% → 2.00% (+9%). Only 5% of carousels use this. Optimal pattern:
- **Slides 1-2:** Directional CTAs ("→ Continue", "Deslize →")
- **Mid slides:** Content continuation prompts
- **Slide 7:** Primary action CTA ("Salve", "Compartilhe", "Siga")

**Implementation:** The swipe text already exists on slide 1 footer. Add directional arrows on content slides. Strengthen the closing CTA with a save/share prompt.

---

### P6: Mixed media — add a short video slide (future)

**Research verdict:** ⚠️ BIG OPPORTUNITY but HIGH EFFORT

Mixed media (images + video) achieves 2.33% engagement vs 1.80% for images-only — a **29% uplift**. Yet only 7% of carousels use it.

**Implementation complexity:** Requires video generation pipeline (not currently in the system). Needs video upload/storage. Best done as a future enhancement after all CSS/layout improvements are shipped.

---

## Rejected proposals

**Per-slide CTAs on EVERY slide:** ❌ Not supported by research. Optimal pattern is directional on early slides, primary action on last. CTAs on every slide would feel aggressive and clutter the design.

---

## Implementation Order

| Order | Proposal | Effort | Impact | Dependencies |
|-------|----------|--------|--------|--------------|
| 1 | **P1** — Slide 7 hero-bg | Low | High | None |
| 2 | **P2** — Remove watermark | Low | Medium | P1 (watermark on slide 2 only) |
| 3 | **P3** — Structured layouts | Medium | High | None (new CSS + renderers) |
| 4 | **P5** — CTAs on slides 1-2, 7 | Low | Medium | P1 (CTA on slide 7) |
| 5 | **P4** — Expand to 10 slides | Medium | Medium | P3 (reuse structured layouts) |
| 6 | **P6** — Mixed media | High | High | Video pipeline |

---

## Research Sources

| Source | Key Finding |
|--------|-------------|
| Socialinsider (35M posts, Jan 2026) | Carousels 0.55% engagement — highest format. Mixed media carousels 2.33% vs 1.80%. |
| Sprout Social (May 2026) | "Use as many slides as the story demands, then cut." |
| Metricool (Jan 2026) | Carousels "hottest format." Instagram testing per-slide engagement. |
| Search Engine Journal | 10 slides peak engagement (2023 — not replicated in 2025-2026). |
| Hootsuite Carousel Guide | Consistent palette across slides; "Swipe" messaging lifts engagement. |
| Buffer Carousel Ideas | Educational/list-style carousels drive most saves. |
