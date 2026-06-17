# Carousel Agent Improvement Plan — Neon Shell v2.0 Alignment

> Status: Superseded — historical record

**Date:** 2026-05-30
**Author:** Plan synthesis from codebase audit and rebranding session analysis
**Status:** Draft / Proposed
**Risk:** High — touches visual output, export pipeline, and prompt alignment

---

## 1. Executive Summary

The rebranding to **Neon Shell v2.0** was applied to a *single carousel output* (`frontend/public/carousel-claude48/`) as a one-off manual effort. The backend carousel template engine, Playwright export service, and frontend preview components were **never updated** to reflect the new visual identity.

This plan recovers the lost elements and upgrades the full carousel agent pipeline to produce Neon Shell v2.0 output consistently, while aligning the skill documentation with the codebase.

### Key Gaps Identified

| Layer | Current State | Desired State |
|-------|--------------|---------------|
| **Backend Template** (`html_template.py`) | Basic HTML — no grid bg, no watermark, no scanline, simple CSS | Neon Shell v2.0 — full dark theme, grid background, creator watermark, scanline overlay, rich glow effects |
| **Playwright Export** (`playwright_export.py`) | Naive 1080x1350 screenshot at .slide, no CSS injection, no clamp overrides | CSS-injected font scale, proper viewport, crop 1px border, optional 2x retina quality |
| **Frontend Preview** (`carousel-preview.tsx`) | Basic hero image + metadata card | Full Instagram-style feed preview with slide navigation |
| **Skill Docs** (`skills/carousel-pipeline/`) | Describe desired Neon Shell v2.0 output | Already aligned (up-to-date) BUT code doesn't match |
| **Prompts** (`prompts/carousel/v1/`) | v1 content/title/caption prompts | Need v2 for refined tone and structured extras |
| **Design Overrides** | Not supported in pipeline — only in `run_design` | Full CSS override injection at export time |

---

## 2. Architecture Context

```
User Request
    │
    ▼
┌─────────────────────────────┐
│  CarouselEditorialOrch.     │
│  (7-phase LangGraph)        │
│  brief → research → outline │
│  → content → design →      │
│  images → final_review      │
└─────────────────────────────┘
    │
    ▼ (design phase)
┌─────────────────────────────┐
│  run_design()               │  ← Generates HTML via html_template.py
│  resolves theme             │     (OLD style — needs Neon Shell upgrade)
│  builds HTML via            │
│  CarouselTemplateBuilder    │
└─────────────────────────────┘
    │
    ▼ (final_review phase)
┌─────────────────────────────┐
│  PlaywrightExportService     │  ← Naive export — needs CSS injection
│  .slide screenshot 1080x1350│
│  quality=95, scale=1        │
└─────────────────────────────┘
    │
    ▼
┌─────────────────────────────┐
│  Frontend Preview            │  ← Basic card — needs full feed view
│  HorizontalCarouselViewer    │
└─────────────────────────────┘
```

### Affected Files (Complete Inventory)

**Backend — Template Engine (must rewrite):**
- `backend/src/rag_backend/application/services/carousel_template/html_template.py`
- `backend/src/rag_backend/application/services/carousel_template/slides.py`
- `backend/src/rag_backend/application/services/carousel_template/design.py`
- `backend/src/rag_backend/application/services/carousel_template/helpers.py`

**Backend — Export (must enhance):**
- `backend/src/rag_backend/infrastructure/external/playwright_export.py`
- `backend/src/rag_backend/application/services/tools/export_tool.py`
- `backend/src/rag_backend/application/services/carousel/nodes/export.py`

**Backend — Prompts (must update):**
- `backend/src/rag_backend/agents/prompts/carousel/v1/content_prompt.yaml`
- `backend/src/rag_backend/agents/prompts/carousel/v1/caption_prompt.yaml`
- `backend/src/rag_backend/agents/prompts/carousel/v1/title_prompt.yaml`

**Frontend — Preview (must upgrade):**
- `frontend/src/app/dashboard/create/workspace/create-carousel-preview.tsx`
- `frontend/src/features/publish/components/horizontal-carousel-viewer.tsx`

**Skills — Documentation (must verify):**
- `skills/carousel-pipeline/_shared/design-system.md` (verify accuracy)
- `skills/carousel-pipeline/_shared/export-and-caption.md` (verify accuracy)
- `skills/carousel-pipeline/_shared/image-generation.md` (verify accuracy)

---

## 3. Gherkin Scenarios

### EPIC-1: Neon Shell v2.0 HTML Template

```gherkin
Feature: Neon Shell v2.0 Carousel HTML Template
  As a content creator
  I want carousel HTML output to use the Neon Shell v2.0 visual identity
  So that all carousels have consistent dark theme with grid background,
  creator watermark, and rich visual effects

  Scenario: Intro slide renders with full Neon Shell style
    Given a carousel project with niche "AI/Tech" and title "Claude Opus 4.8"
    When the design phase generates HTML
    Then the intro slide container has a <div class="grid-bg"> with animated grid lines
    And the intro slide has a creator watermark with avatar image, name, and handle
    And the intro slide badge includes a pulsing dot indicator
    And the intro slide title uses font-size at 52px with 0.02em negative letter-spacing
    And the slide footer shows niche text and "Deslize →" swipe prompt
    And the page background is #060a12 or theme background
    And the page includes Inter and JetBrains Mono font imports from Google Fonts

  Scenario: Content slide renders with Neon Shell layout
    Given a content slide with heading, body, and optional extras
    When the design phase generates HTML
    Then the slide has bg-glow with primary and accent radial gradients
    And the slide heading uses 50px font-weight 800 with accent-colored <strong> highlights
    And the slide body uses 30px font-weight 400 at var(--text-60) opacity
    And the slide has a slide number badge (e.g. "01 / 06") in mono font
    And progress dots show at the bottom of the slide

  Scenario: Feature grid renders in 1-column or 2-column layout
    Given a slide with 2-6 features in structured extras
    When rendered as HTML
    Then each feature has an icon, title, and body
    And if 4+ features, the grid uses .feature-grid.cols-2
    And each feature-item has border-radius: 8px with primary-colored border at 15% opacity
    And feature-title uses 28px font-weight 700
    And feature-body uses 24px font-weight 400 at var(--text-60)

  Scenario: Stat row renders as 3-column number grid
    Given a slide with 3 stat items
    When rendered as HTML
    Then stats display in a 3-column grid with .stat-number at 42px font-weight 900 in accent color
    And each stat has .stat-label and optional .stat-detail
    And stat cards have border-radius 8px with primary border

  Scenario: CTA slide renders centered content
    Given a CTA slide with heading and body
    When rendered as HTML
    Then the slide content is centered both horizontally and vertically
    And there is a rocket emoji icon at 64px
    And there are two CTA buttons: "Salve este post" and "Compartilhe"

  Scenario: Summary/closing slide renders checklist layout
    Given a closing slide with summary_points array
    When rendered as HTML
    Then each point renders as a .summary-item with icon, title, and body
    And the items are in a 2-column grid with the 3rd item spanning both columns
    And the background is a blurred version of slide 1's hero image

  Scenario: Progress dots render per slide
    Given any slide is rendered
    When the HTML is generated
    Then a .progress container shows 6 bars with .active class for completed slides
    And active bars use the primary color
```

### EPIC-2: Enhanced Playwright Export with CSS Injection

```gherkin
Feature: High-Quality Carousel Export via Playwright
  As a content creator
  I want carousel slides exported at 1080x1350 with proper font scaling
  So that images are Instagram-ready without quality loss

  Scenario: Export injects font clamp overrides for 1080px canvas
    Given a carousel HTML document
    When the export service renders slides
    Then it injects CSS overriding font clamp max values for 1080px canvas
    And .s1-title gets clamp(26px, 5.5vw, 56px)
    And .slide-heading gets clamp(20px, 4.5vw, 50px)
    And .body-p gets clamp(12px, 2.5vw, 30px)
    And the feed width is set to 1150px (1080 + padding)
    And .ig-slide-inner is forced to exactly 1080x1350

  Scenario: Export screenshots each slide individually
    Given the HTML is fully rendered
    When screenshots are taken
    Then each .ig-slide-inner element is captured separately
    And screenshots are saved as JPEG quality 100
    And the 1px border artifact is cropped from center

  Scenario: Optional 2x Retina export is available
    Given the export service is configured for HD
    When rendering with deviceScaleFactor: 2
    Then each slide is exported at 2160x2700
    And filenames use format export_hd_{n}.jpg
    And font clamp values are proportionally scaled

  Scenario: Export preserves accent color highlights
    Given a slide heading with **accent-highlighted** words
    When the export service renders the HTML
    Then <strong> elements inside headings render in the theme accent color
    And the inline renderer converts **bold** to correct <strong> tags

  Scenario: Export creates bilingual directories
    Given a project with EN translations available
    When the export runs
    Then PT slides go to /pt/ subdirectory
    And EN slides (when translations exist) go to /en/ subdirectory
    And hero image paths are rewritten from images/ to ../images/
```

### EPIC-3: Creator Watermark Support

```gherkin
Feature: Configurable Creator Watermark
  As a content creator
  I want a watermark with my avatar, name, and handle on every slide
  So that my brand is consistently visible

  Scenario: Watermark appears on all slides
    Given a carousel project with creator metadata
    When the design phase generates HTML
    Then every slide container includes a .creator-watermark div
    And the watermark contains avatar image, display name, and @handle
    And the watermark is positioned at bottom-left with backdrop blur
    And the avatar is 24px (or 36px on export) with primary-color border and glow

  Scenario: Watermark is configurable per project
    Given a carousel project
    When the project includes creator metadata (name, handle, avatar_url)
    Then the HTML template renders that creator's info
    And if no creator metadata exists, the watermark is omitted

  Scenario: Watermark scales for export
    Given the export service is rendering at 1080x1350
    When CSS injection overrides are applied
    Then the watermark padding increases to 10px 18px 10px 10px
    And the avatar scales to 36px with 2px border
    And the name and handle font sizes increase proportionally
```

### EPIC-4: Frontend Preview Upgrade

```gherkin
Feature: Instagram-Style Carousel Preview
  As a user reviewing a carousel in the dashboard
  I want to see a full Instagram-style feed preview
  So that I can accurately judge the visual output before publishing

  Scenario: Create workspace shows live carousel preview
    Given a carousel project with generated slides
    When viewing the create workspace
    Then the preview shows slides in a vertical feed layout (max-width 600px)
    And each slide renders at the correct aspect ratio (4:5)
    And navigation dots and slide counter are visible
    And the preview uses the Neon Shell dark theme

  Scenario: Preview updates when design changes
    Given the design phase has completed
    When the user approves or revises the design
    Then the preview reflects the latest design tokens and slide content
```

### EPIC-5: Skill Documentation Alignment

```gherkin
Feature: Skill Documentation Matches Backend Implementation
  As a developer maintaining the carousel pipeline
  I want the skill documentation to accurately reflect the backend implementation
  So that agents follow correct instructions

  Scenario: Design system docs match backend template output
    Given the backend html_template.py produces Neon Shell v2.0 output
    When comparing with skills/carousel-pipeline/_shared/design-system.md
    Then all CSS custom properties match
    And all font sizes match
    And all layout rules match (feature grid, stat row, etc.)
    And the watermark implementation matches

  Scenario: Export docs match Playwright export implementation
    Given the enhanced PlaywrightExportService
    When comparing with skills/carousel-pipeline/_shared/export-and-caption.md
    Then the CSS injection procedure is documented
    And the font clamp override values are documented
    And the bilingual export process is documented
```

### EPIC-6: Prompt Version Update

```gherkin
Feature: Updated Prompts for Neon Shell Content
  As an LLM generating carousel content
  I want prompts that produce structured extras and Neon Shell-appropriate output
  So that the content fits the visual design

  Scenario: Content prompt produces structured extras
    Given a content prompt
    When generating slide content for a content slide
    Then the output includes exactly one structured extra (stats/features/insight)
    And stats arrays contain exactly 3 items
    And feature items include icon, title, and body
    And insight includes quote and attribution

  Scenario: Caption prompt follows Neon Shell style
    Given a caption prompt
    When generating an Instagram caption
    Then the output includes a hook, value promise, comment question, and double CTA
    And 12-18 relevant hashtags
    And no em dashes in the output
```

---

## 4. Risks, Trade-offs, and Mitigations

| Risk | Severity | Probability | Mitigation |
|------|----------|-------------|------------|
| **Visual regression**: changed template breaks existing carousels | High | Medium | Version the HTML template; old carousels keep v1, new carousels use v2; snapshot test for each slide type |
| **Export quality regression**: CSS injection changes slide dimensions | High | Medium | Unit test export with pixel-perfect comparison; validate 1080x1350 output dimensions |
| **Watermark breaks layout**: 24px watermark on intro slide overlaps hero gradient | Medium | Low | Position watermark in bottom-left area that gradient avoids; test all 6 slide types |
| **Font mismatch**: Google Fonts Inter / JetBrains Mono not available offline | Low | High | Add fallback fonts (`system-ui, -apple-system, sans-serif`); include WOFF2 as base64 for self-contained HTML |
| **Prompts drift from skills**: v2 prompts don't match _shared/ contracts | Medium | Medium | Create `v2` prompt directory alongside `v1`; run prompt validation tests on output JSON |
| **Frontend preview slows**: full Instagram feed render is heavy | Low | Medium | Lazy-load slides with IntersectionObserver; virtualize for 10+ slides |
| **Bilingual export doubles time**: running Playwright twice | Medium | Medium | Cache browser context between PT and EN renders; parallelize PT and EN export |
| **Existing carousels in DB have old design_tokens**: migration needed | Low | Low | Design tokens are regenerated by `run_design()` — no DB migration needed |
| **Mutation testing required for new code**: 70%+ target for template + export | Medium | Medium | Write tests alongside implementation; mutmut config in `backend/pyproject.toml` |

### Trade-offs

| Decision | Option A (Recommended) | Option B | Rationale |
|----------|----------------------|----------|-----------|
| **Template versioning** | Add `template_version` to project model | Rewrite in-place | Avoids breaking in-progress carousels; enables A/B testing |
| **CSS injection strategy** | Inject via `page.evaluate()` at export time | Hardcode in HTML template | Clamp values need to differ for preview (600px) vs export (1080px); injection is cleaner |
| **Watermark storage** | Creator metadata on `CarouselProject` model | Hardcoded in env config | Supports multi-user; required for personal brand |
| **Image generation model** | Keep current: Gemini 3.1 Flash Image Preview | Switch to DALL-E 3 | Current provider works; Gemini is cheaper and faster |
| **Export quality default** | JPEG quality 100 (475-846KB per slide) | quality 95 (current) | Instagram-ready vs smaller files; disk is cheap |

---

## 5. Implementation Plan — Tasks with Acceptance Criteria

### Milestone 1: Backend Template Upgrade (Neon Shell v2.0)

#### Task 1.1: Create Neon Shell template CSS module
**Acceptance Criteria:**
- [ ] New file: `carousel_template/neon_styles.py` with all CSS custom properties
- [ ] Grid background with animated scanlines (`@keyframes grid-drift`)
- [ ] Fixed position overlay with repeating-linear-gradient scanline
- [ ] Radially gradient glow effects (primary top-right, accent bottom-left)
- [ ] Google Fonts link for Inter (300-900 weights) and JetBrains Mono (400-700)
- [ ] CSS custom properties for all theme colors
- [ ] Reduced motion media query for accessibility
- [ ] Responsive breakpoints at 640px and 400px for mobile

#### Task 1.2: Rewrite html_template.py with Neon Shell layout
**Acceptance Criteria:**
- [ ] Template generates `<!DOCTYPE html><html class="dark">` with Neon Shell head
- [ ] Grid background div with `grid-bg-inner` animated element
- [ ] Page header with title and slide count subtitle
- [ ] Feed container at `max-width: 600px` with padding
- [ ] Each slide is `.ig-post` with `.ig-slide` > `.ig-slide-inner`
- [ ] Creator watermark on all slides (bottom-left, backdrop-blur, avatar + name + handle)
- [ ] Instagram-style action bar (like, comment, share, save)
- [ ] Instagram-style caption below each slide
- [ ] Slide counter with dots navigation (`past`/`active` dot classes)
- [ ] SVG icon sprite defs at top of body

#### Task 1.3: Rewrite slides.py with Neon Shell slide renderers
**Acceptance Criteria:**
- [ ] `_render_intro_slide`: hero background image with gradient overlay, badge with pulse dot, title with accent highlight, subtitle, TL;DR strip, footer with niche + swipe prompt
- [ ] `_render_content_slide`: slide number, heading with accent highlight, hero image (border + gradient overlay), body paragraphs, structured extras (feature grid, stat row, insight card)
- [ ] `_render_summary_slide`: blurred hero background, heading, subtitle, summary_grid with items (third spans full width), progress dots
- [ ] `_render_cta_slide`: centered layout, rocket icon, heading, body, dual CTA buttons
- [ ] All structured extras render at the font sizes specified in design-system.md (52px titles, 30px body, 50px headings, etc.)
- [ ] Feature grid supports 1-column (2-3 items) and 2-column (4+ items) layouts
- [ ] Stat row renders exactly 3 items in 3-column grid
- [ ] Heading `<strong>` highlights render in accent color
- [ ] Body `<strong>` renders in white (#fff)
- [ ] `_render_inline` correctly handles em-dash stripping, `**bold**` -> `<strong>`, `` `code` `` -> `.code-tag`
- [ ] Slide containers do NOT set `height: 100%` on cta-slide (anti-pattern AP-10)

#### Task 1.4: Update design.py for new template
**Acceptance Criteria:**
- [ ] `run_design` passes creator metadata (name, handle, avatar URL) to template
- [ ] Design tokens JSON includes watermark info
- [ ] Theme resolution unchanged but verified to produce correct CSS vars

#### Task 1.5: Update helpers.py inline renderer
**Acceptance Criteria:**
- [ ] `_render_inline` escapes HTML entities
- [ ] Strips em dashes (`—`, `–`, `--`)
- [ ] Converts `**text**` -> `<strong>text</strong>`
- [ ] Converts `` `code` `` -> `<span class="code-tag">code</span>`
- [ ] Heading-level highlights detected and wrapped in accent-colored `<strong>`

#### Tests for Milestone 1
**Acceptance Criteria:**
- [ ] Unit tests for each slide renderer with all valid input combinations
- [ ] Snapshot test: render each slide type and compare to expected HTML string
- [ ] Verify all 5 themes (cybersecurity, ai_competition, developer_skills, source_code, social_engineering) produce correct CSS vars
- [ ] Verify feature grid wraps to 2-column at 4+ items
- [ ] Verify stat row renders exactly 3 items
- [ ] Verify em-dash stripping works on body text
- [ ] Verify watermark rendering with and without creator metadata
- [ ] Verify all 21 anti-patterns from `_shared/anti-patterns.md` are covered by tests
- [ ] Branch coverage >= 90% on template module

---

### Milestone 2: Enhanced Playwright Export with CSS Injection

#### Task 2.1: Rewrite PlaywrightExportService with CSS injection
**Acceptance Criteria:**
- [ ] Export accepts optional `css_overrides` parameter
- [ ] On export, injects font clamp overrides via `page.evaluate()` (not by modifying HTML)
- [ ] Override CSS matches the values documented in `carousel-export-techniques.md`
- [ ] Feed width set to 1150px for 1080px canvas padding
- [ ] `.ig-slide-inner` elements forced to exactly 1080x1350
- [ ] Screenshot targets `.ig-slide-inner` (not `.ig-slide`) to avoid 1px border artifact
- [ ] Output images cropped from center to exactly 1080x1350 (border artifact removal)
- [ ] JPEG quality defaults to 95, optionally 100
- [ ] Watermark font sizes and avatar scale up with CSS injection

#### Task 2.2: Add 2x Retina export support
**Acceptance Criteria:**
- [ ] New method: `export_slides_hd()` with `deviceScaleFactor: 2`
- [ ] Output at 2160x2700 resolution
- [ ] Filename pattern: `export_hd_{n}.jpg`
- [ ] Font clamp overrides scaled for 2x canvas

#### Task 2.3: Update export.py for bilingual Neon Shell export
**Acceptance Criteria:**
- [ ] `render_language` rewrites image paths (`images/` -> `../images/`)
- [ ] Creates language subdirectories (`pt/`, `en/`)
- [ ] PT slides exported first, then EN when translations exist
- [ ] Optional PDF build for each language
- [ ] Progress reported via `publish_workflow_progress()`

#### Tests for Milestone 2
**Acceptance Criteria:**
- [ ] Unit test CSS injection: verify clamp values injected correctly
- [ ] Unit test border cropping: verify 1px artifact removed from all 4 edges
- [ ] Integration test with Playwright: export single slide, verify dimensions 1080x1350
- [ ] Test bilingual export produces PT and EN directories
- [ ] Test HD export produces 2160x2700 files
- [ ] Branch coverage >= 90%

---

### Milestone 3: Creator Watermark Support

#### Task 3.1: Add creator metadata to CarouselProject model
**Acceptance Criteria:**
- [ ] `creator_name`, `creator_handle`, `creator_avatar_url` fields on `CarouselProject`
- [ ] Default values based on env config (`CREATOR_NAME`, `CREATOR_HANDLE`, `CREATOR_AVATAR_URL`)
- [ ] Watermark only renders when at least `creator_name` is set
- [ ] API endpoints expose creator metadata in project response

#### Task 3.2: Render watermark in template
**Acceptance Criteria:**
- [ ] Watermark div positioned absolute at bottom-left (16px offset)
- [ ] Backdrop blur with semi-transparent background
- [ ] Avatar image (24px x 24px) with primary-color border and glow
- [ ] Name (11px, bold) and handle (9px, mono, muted) stacked vertically
- [ ] Max-width constraints with ellipsis overflow
- [ ] Responsive: shrinks on mobile (20px avatar, 10px/8px text)

#### Tests for Milestone 3
- [ ] Test watermark renders when creator metadata exists
- [ ] Test watermark omitted when no creator metadata
- [ ] Test text truncation with long name/handle
- [ ] Test mobile responsive sizing

---

### Milestone 4: Frontend Preview Upgrade

#### Task 4.1: Upgrade create-carousel-preview.tsx
**Acceptance Criteria:**
- [ ] Renders full vertical feed at `max-width: 600px` using inline CSS (not an iframe)
- [ ] Shows all 6 slides with Neon Shell styling
- [ ] Slide counter dots with navigation
- [ ] Creator watermark rendered (if enabled)
- [ ] Instagram-style action bar (like, comment, share, save — visual only)
- [ ] Caption text below each slide
- [ ] Lazy-loading with IntersectionObserver
- [ ] Accessible: keyboard navigation for slide switching

#### Task 4.2: Upgrade HorizontalCarouselViewer for published carousels
**Acceptance Criteria:**
- [ ] Renders published slides in horizontal snap-scroll view
- [ ] Shows slide counter
- [ ] Download-all button exports ZIP
- [ ] Responsive: full width on mobile, constrained on desktop

#### Tests for Milestone 4
- [ ] Test preview renders all 6 slides
- [ ] Test IntersectionObserver triggers lazy-load
- [ ] Test download-all creates valid ZIP
- [ ] Test keyboard navigation

---

### Milestone 5: Prompt Version Update

#### Task 5.1: Create prompts/carousel/v2/ directory
**Acceptance Criteria:**
- [ ] New directory: `backend/src/rag_backend/agents/prompts/carousel/v2/`
- [ ] Updated `content_prompt.yaml` with structured extras requirements
- [ ] Updated `caption_prompt.yaml` with Neon Shell caption template
- [ ] Updated `title_prompt.yaml` with title optimization rules
- [ ] Old v1 prompts preserved for rollback
- [ ] Prompt registry updated: `render_prompt("carousel", "content_prompt", version="v2")`

#### Task 5.2: Update prompt registry default version
**Acceptance Criteria:**
- [ ] `DEFAULT_CAROUSEL_PROMPT_VERSION = "v2"`
- [ ] Phase subagents use v2 prompts by default
- [ ] Can still use v1 for A/B testing via config
- [ ] Langfuse metadata includes prompt version

#### Tests for Milestone 5
- [ ] Test registry returns v2 prompts correctly
- [ ] Test v1 prompts still loadable (backward compatibility)
- [ ] Test Jinja2 rendering with v2 variables

---

### Milestone 6: Skill Documentation Alignment

#### Task 6.1: Align skills/carousel-pipeline/_shared/ with implementation
**Acceptance Criteria:**
- [ ] `design-system.md` font sizes match the Neon Shell template output
- [ ] `export-and-caption.md` CSS injection values match `carousel-export-techniques.md`
- [ ] `image-generation.md` correctly describes the Gemini provider strategy
- [ ] `content-contracts.md` structured extras match the new prompts
- [ ] All anti-patterns in `anti-patterns.md` are test-covered
- [ ] `three-layer alignment` in `_shared/README.md` is accurate

#### Task 6.2: Update bmad-skill-manifest.yaml if phases changed
**Acceptance Criteria:**
- [ ] Phase skill references point to correct files
- [ ] Shared standards lists are accurate per phase
- [ ] Input/output schemas match the implementation

#### Tests for Milestone 6
- [ ] No test needed (documentation only)
- [ ] Review: manual verification that docs match code

---

### Milestone 7: Integration and E2E

#### Task 7.1: Full workflow integration test
**Acceptance Criteria:**
- [ ] Create carousel via API -> verify Neon Shell HTML is generated
- [ ] Approve design phase -> verify HTML is persisted
- [ ] Run final review -> verify Playwright export produces 1080x1350 slides
- [ ] Publish carousel -> verify frontend preview renders correctly
- [ ] Verify bilingual export works correctly

#### Task 7.2: Regression test pack
**Acceptance Criteria:**
- [ ] Run full backend test suite: `cd backend && uv run pytest`
- [ ] Run full frontend test suite: `cd frontend && npm run test`
- [ ] Run type checks: `cd backend && uv run mypy && cd frontend && npm run typecheck`
- [ ] Run lint: `cd backend && uv run ruff check && cd frontend && npm run lint`
- [ ] Verify no regressions in existing carousel functionality

#### Task 7.3: Mutation testing baseline
**Acceptance Criteria:**
- [ ] Run `mutmut` on template and export modules
- [ ] Mutation score >= 70% on business logic (template rendering, export sizing)
- [ ] Disable Regex and ObjectLiteral mutators
- [ ] Document current mutation score for tracking

---

## 6. Implementation Order

```
Week 1: Milestone 1 (Backend Template) + Milestone 3 (Watermark)
  - Core HTML templates
  - CSS module
  - Slide renderers
  - Creator metadata model

Week 2: Milestone 2 (Export) + Milestone 4 (Frontend Preview)
  - Playwright CSS injection
  - 1080x1350 export
  - Bilingual export
  - Preview components

Week 3: Milestone 5 (Prompts) + Milestone 6 (Docs) + Milestone 7 (Integration)
  - v2 prompts
  - Skill docs alignment
  - Integration tests
  - Mutation testing
```

---

## 7. Key Files Reference

| Current File | Action | New/Enhanced File |
|-------------|--------|-------------------|
| `html_template.py` | REWRITE | `html_template.py` (Neon Shell v2.0) |
| `slides.py` | REWRITE | `slides.py` (Neon Shell renderers) |
| `helpers.py` | UPDATE | `helpers.py` (inline renderer) |
| `design.py` | UPDATE | `design.py` (watermark passthrough) |
| `playwright_export.py` | REWRITE | `playwright_export.py` (CSS injection + HD) |
| `export_tool.py` | UPDATE | `export_tool.py` (HD param) |
| `export.py` (nodes) | UPDATE | `export.py` (bilingual Neon Shell) |
| `content_prompt.yaml` | NEW v2 | `prompts/carousel/v2/content_prompt.yaml` |
| `caption_prompt.yaml` | NEW v2 | `prompts/carousel/v2/caption_prompt.yaml` |
| `title_prompt.yaml` | NEW v2 | `prompts/carousel/v2/title_prompt.yaml` |
| `create-carousel-preview.tsx` | REWRITE | `create-carousel-preview.tsx` (full feed) |
| `horizontal-carousel-viewer.tsx` | UPDATE | `horizontal-carousel-viewer.tsx` (Neon Shell) |
| `design-system.md` | VERIFY | `design-system.md` |
| `export-and-caption.md` | VERIFY | `export-and-caption.md` |
| `anti-patterns.md` | VERIFY | `anti-patterns.md` |

---

## 8. Rollback Plan

If the Neon Shell v2.0 template causes issues:

1. **Template rollback**: Keep old `html_template.py` as `html_template_v1.py`. If template_version == "v1", use old template.
2. **Export rollback**: Old `PlaywrightExportService` does simple `.slide` screenshot. Keep as `SimpleExportService`.
3. **Prompt rollback**: v1 prompts remain in `prompts/carousel/v1/`. Switch default version back via config.
4. **Frontend rollback**: Old preview component kept in git history.

Add `TEMPLATE_VERSION` constant to `domain/constants/carousel.py`:
```python
TEMPLATE_VERSION_V1 = "v1"
TEMPLATE_VERSION_V2 = "v2"
DEFAULT_TEMPLATE_VERSION = TEMPLATE_VERSION_V2
```
