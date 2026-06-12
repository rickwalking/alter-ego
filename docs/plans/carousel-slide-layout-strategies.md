# Carousel Slide Layout Strategies — Architecture Plan

> **Epic:** Slide Layout Strategy Pattern
> **Tickets:** [AE-0007](../.agent/tasks/AE-0007-carousel-visual-design-improvements.md) (Design) · [AE-0005](../.agent/tasks/AE-0005-slide-layout-strategy-api-di-wiring.md) (Backend API + DI) · [AE-0004](../.agent/tasks/AE-0004-frontend-strategy-selector-integration.md) (Frontend) · [AE-0006](../.agent/tasks/AE-0006-slide-layout-strategy-tests.md) (Tests)
> **P1-P4 Implemented:** Yes — Protocol, registry, css/ subfolder, strategies/, builder cleanup
> **Design changes:** See §11 — Design Addendum (P1/P2/P5 + watermark dedup)
> **Order:** AE-0007 → AE-0005 → AE-0004 → AE-0006

## 1. Current State Analysis

### The Problem

The carousel slide rendering pipeline has a hardcoded if/elif dispatch chain in `html_template.py:180-215`:

```python
if slide_type == SLIDE_TYPE_INTRO:
    inner = _render_intro_slide(...)
elif slide_type == SLIDE_TYPE_SUMMARY:
    inner = _render_summary_slide(...)
elif slide_type == SLIDE_TYPE_CLOSING:
    inner = _render_closing_slide(...)
elif slide_type == SLIDE_TYPE_CTA:
    inner = _render_cta_slide(...)
else:
    inner = _render_content_slide(...)
```

Three renderers (`_render_summary_slide`, `_render_content_slide`, `_render_closing_slide`) are **identical** — all produce the same `slide-hero-bg-img` / `slide-hero-content` layout.

The `SlideDict` TypedDict already carries structured data fields (`features`, `stats`, `insight`, `summary_points`, `tldr_strip`) but **no renderer uses them** — they only read `heading` and `body`.

### The Gap

| Layer | What exists | What's missing |
|-------|-------------|----------------|
| Frontend template selector | 6 named templates (Analysis, Comparison, Tutorial, News Flash, Deep Dive, Listicle) as `selectedTemplate: number` | Template never sent to API; UI-only state |
| Backend render dispatch | Hardcoded if/elif on 5 slide types | No strategy registry; no pluggable layouts |
| Renderers | 5 functions, 3 identical | No structured data cards (features, stats, insight) |
| Themes | 5 palettes + brand + category keyword match | No theme-strategy interface |
| `template_version` field | Stored on `CarouselProject` (default `"v2"`) | Never used for dispatch |

### What We Want

- Each frontend template (Analysis, Comparison, etc.) selects a **layout strategy** that determines **slide structure** (which data fields are rendered, in what visual layout)
- Every strategy produces **consistent Neon Shell v2.0** styling through shared CSS tokens
- Themes and voices are orthogonal — any strategy works with any theme/voice
- New strategies can be added without modifying existing code

---

## 2. Strategy Pattern Architecture

### 2.1 Layer Map

```
┌──────────────────────────────────────────────────────────────────┐
│                       Frontend (React)                           │
│  create-template-section.tsx                                     │
│    └─ selectedTemplate: number  →  POST /api/carousels/{id}/     │
│       strategy?strategy=analysis_deep_dive                       │
│                                                                  │
│  CarouselProjectResponse.slide_layout_strategy (NEW)             │
│    └─ read back the active strategy name                         │
└──────────────────────────┬───────────────────────────────────────┘
                           │  API (FastAPI)
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│  api/routes/carousels/strategies.py  (NEW)                       │
│  POST /{id}/slides/regenerate?strategy=analysis_deep_dive        │
│  GET  /{id}/strategies                                           │
│    └─ CarouselRefinementService.re_render_slides(strategy=...)   │
└──────────────────────────┬───────────────────────────────────────┘
                           │  Application Layer
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│  application/services/carousel/                                  │
│  ├── strategies/                          (NEW directory)        │
│  │   ├── __init__.py                                             │
│  │   ├── interface.py                    ← Strategy Protocol     │
│  │   ├── registry.py                     ← Registry + factory   │
│  │   ├── intro_strategy.py              (wraps _render_intro)    │
│  │   ├── hero_content_strategy.py       (wraps the 3 identical) │
│  │   ├── stat_card_strategy.py          (stats grid)             │
│  │   ├── feature_grid_strategy.py       (feature cards)          │
│  │   ├── insight_quote_strategy.py      (insight quote)          │
│  │   ├── numbered_list_strategy.py      (numbered steps)         │
│  │   └── cta_strategy.py               (wraps _render_cta)      │
│  ├── refinement_service.py              (updated dispatch)       │
│  └── types.py                            (SlideDict unchanged)  │
└──────────────────────────┬───────────────────────────────────────┘
                           │  Domain Layer
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│  domain/                                                         │
│  ├── protocols/carousel.py              ← SlideLayoutStrategy   │
│  │                                        Protocol (NEW)         │
│  └── models/carousel.py                 ← CarouselProject       │
│       slide_layout_strategy: str | None  (NEW field)             │
└──────────────────────────────────────────────────────────────────┘
```

### 2.2 Interface Contract

The `SlideLayoutStrategy` Protocol lives in `domain/protocols/carousel.py` alongside existing protocols:

```python
@runtime_checkable
class SlideLayoutStrategy(Protocol):
    """Renders a single slide's inner HTML for a given layout format.

    Each strategy produces the content *inside* the ig-slide wrapper
    (heading, body, structured cards, watermark). The outer shell
    (action bar, counter, caption) is applied by the builder.
    """

    strategy_name: str
    """Unique key used in the API and registry, e.g. 'stat_card_grid'."""

    display_name: str
    """Human-readable label, e.g. 'Stat Card Grid'."""

    supported_slide_types: frozenset[str]
    """Slide types this strategy can render, e.g. {'content', 'summary'}."""

    def render(
        self,
        slide: SlideDict,
        project: CarouselProject,
        theme: Mapping[str, str],
        total_slides: int,
        language: str,
    ) -> str:
        """Return inner HTML for a single slide.

        Args:
            slide: Structured slide data (heading, body, features, stats, insight...)
            project: Full project metadata (watermark, language, niche, creator...)
            theme: Design palette dict (primary, accent, background...)
            total_slides: Total slide count for progress display.
            language: Language code (pt, en) for localized CTA text.

        Returns:
            Inner HTML string (inserted inside .ig-slide-inner).
        """
        ...
```

### 2.3 Strategy Registry

```python
# application/services/carousel/strategies/registry.py

class SlideLayoutRegistry:
    """Maps strategy_name → SlideLayoutStrategy implementation.

    Registered at container bootstrap. Strategies are lazy-loaded
    singletons — only constructed when first requested.
    """

    _strategies: dict[str, SlideLayoutStrategy]

    def __init__(self) -> None:
        self._strategies = {}

    def register(self, strategy: SlideLayoutStrategy) -> None:
        name = strategy.strategy_name
        if name in self._strategies:
            raise ValueError(f"Strategy '{name}' already registered")
        self._strategies[name] = strategy

    def get(self, name: str) -> SlideLayoutStrategy:
        strategy = self._strategies.get(name)
        if strategy is None:
            raise StrategyNotFoundError(name)
        return strategy

    def list(self) -> list[dict[str, str]]:
        return [
            {"name": s.strategy_name, "display_name": s.display_name}
            for s in self._strategies.values()
        ]

    def find_for_slide(
        self, slide_type: str, fallback: str = "hero_content"
    ) -> SlideLayoutStrategy:
        for strategy in self._strategies.values():
            if slide_type in strategy.supported_slide_types:
                return strategy
        return self._strategies[fallback]
```

### 2.4 Concrete Strategies

| Strategy Name | Supported Slide Types | Data Used | Visual Layout |
|---|---|---|---|
| `intro_hero` | `intro` | heading, body, tldr_strip | Existing full-bleed image + gradient + badge |
| `hero_content` | `content`, `summary`, `closing` | heading, body | Existing hero-bg-img + gradient + number |
| `stat_card_grid` | `content`, `summary` | stats[], heading, body | 3-column stat cards under heading |
| `feature_grid` | `content`, `closing` | features[], heading, body | 2×2 feature card grid |
| `insight_quote` | `content`, `closing` | insight{}, heading, body | Accent-bordered quote card |
| `numbered_list` | `content` | features[], heading | Numbered step list (1-based) |
| `cta_centered` | `cta` | heading, body, creator metadata | Existing centered avatar + CTA |

Each strategy wraps its own CSS in a `get_strategy_css() -> str` method, called by `get_neon_shell_css()` during assembly.

### 2.5 Dependency Injection Wiring

```python
# infrastructure/container.py

from rag_backend.application.services.carousel.strategies.registry import (
    SlideLayoutRegistry,
)
from rag_backend.application.services.carousel.strategies.stat_card_grid import (
    StatCardGridStrategy,
)
from rag_backend.application.services.carousel.strategies.feature_grid import (
    FeatureGridStrategy,
)
# ... other strategies

def bootstrap_strategies() -> SlideLayoutRegistry:
    registry = SlideLayoutRegistry()
    registry.register(IntroHeroStrategy())
    registry.register(HeroContentStrategy())
    registry.register(StatCardGridStrategy())
    registry.register(FeatureGridStrategy())
    registry.register(InsightQuoteStrategy())
    registry.register(NumberedListStrategy())
    registry.register(CtaCenteredStrategy())
    return registry

class Container(containers.DeclarativeContainer):
    strategy_registry = providers.Singleton(bootstrap_strategies)

    carousel_refinement = providers.Factory(
        CarouselRefinementService,
        repository=carousel_repository,
        llm_service=llm_service,
        image_registry=image_provider_registry,
        export_service=export_service,
        pdf_slide_builder=pdf_slide_builder,
        strategy_registry=strategy_registry,  # NEW
    )
```

---

## 3. Architecture Flow (ASCII Diagram)

```
┌──────────────┐    POST /{id}/slides/regenerate?strategy=feature_grid
│  Frontend    │ ───────────────────────────────────────────────────┐
│  Template    │                                                    │
│  Selector    │                                                    │
│  (6 cards)   │                                                    │
└──────┬───────┘                                                    ▼
       │ selectedTemplate: number  ┌──────────────────────────────────────┐
       │ → mapped to strategy key  │  api/routes/carousels/strategies.py  │
       │                           │                                      │
       │                           │  1. Parse strategy query param        │
       │                           │  2. Validate in registry              │
       │                           │  3. Call refinement_service           │
       │                           │     .re_render_slides(                │
       │                           │       project_id, strategy=name)      │
       │                           └──────────┬───────────────────────────┘
       │                                      │
       │                           ┌──────────▼───────────────────────────┐
       │                           │  CarouselRefinementService           │
       │                           │                                      │
       │                           │  1. Load project + slides from DB    │
       │                           │  2. Unpack_extras() → SlideData[]    │
       │                           │  3. For each slide:                  │
       │                           │     strategy = registry.find_for_    │
       │                           │       slide(slide_type, strategy)    │
       │                           │     html = strategy.render(...)      │
       │                           │  4. Swap strategy in build_carousel_ │
       │                           │     html()                           │
       │                           └──────────┬───────────────────────────┘
       │                                      │
       │                           ┌──────────▼───────────────────────────┐
       │                           │  strategies/                         │
       │                           │                                      │
       │                           │  intro_hero.py    → intro slides     │
       │                           │  hero_content.py  → content/summary  │
       │                           │  stat_card_grid.py→ stats[] layout   │
       │                           │  feature_grid.py  → features[] grid  │
       │                           │  insight_quote.py → insight{} card   │
       │                           │  numbered_list.py → step list        │
       │                           │  cta_centered.py  → CTA slides       │
       │                           └──────────┬───────────────────────────┘
       │                                      │
       │                           ┌──────────▼───────────────────────────┐
       │                           │  HTML Assembly + Export              │
       │                           │                                      │
       │                           │  1. Wrap each slide in ig-post       │
       │                           │  2. Embed CSS (base + strategy)      │
       │                           │  3. Export to JPG via Playwright     │
       │                           │  4. Update project.slide_layout_     │
       │                           │     strategy                         │
       │                           └──────────────────────────────────────┘
       │
       │   GET /{id} → CarouselProjectResponse.slide_layout_strategy
       └──────────────────────────────────────────────────────────────────
```

---

## 4. API Contracts

### 4.1 Regenerate Slides with Strategy

```
POST /api/carousels/{project_id}/slides/regenerate?strategy=feature_grid
```

**Request:** None (strategy as query param)

**Response 200:**
```json
{
  "id": "uuid",
  "slide_layout_strategy": "feature_grid",
  "status": "completed",
  "design_tokens": { ... }
}
```

**Errors:**
| Status | Condition |
|--------|-----------|
| 404 | Project not found |
| 422 | Strategy name not in registry |
| 409 | Project not yet completed (no slides to re-render) |

### 4.2 List Available Strategies

```
GET /api/carousels/strategies
```

**Response 200:**
```json
{
  "strategies": [
    {"name": "hero_content", "display_name": "Hero Content (Default)"},
    {"name": "stat_card_grid", "display_name": "Stat Card Grid"},
    {"name": "feature_grid", "display_name": "Feature Card Grid"},
    {"name": "insight_quote", "display_name": "Insight Quote"},
    {"name": "numbered_list", "display_name": "Numbered List"}
  ]
}
```

### 4.3 Updated GET /{id} Response

Add field to `CarouselProjectResponse`:
```json
{
  "slide_layout_strategy": "feature_grid",
  ...
}
```

### 4.4 Frontend Hook (NEW)

```typescript
// features/create/hooks/use-slide-layout-strategies.ts

export function useAvailableStrategies() {
  return useQuery({
    queryKey: ["carousel-strategies"],
    queryFn: () => apiCall("/api/carousels/strategies", strategiesSchema),
  });
}

export function useRegenerateSlides(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (strategy: string) => {
      return apiCall(
        `/api/carousels/${projectId}/slides/regenerate?strategy=${strategy}`,
        carouselProjectResponseSchema,
        { method: HTTP_METHODS.POST },
      );
    },
    onSuccess: (project) => {
      queryClient.invalidateQueries({ queryKey: carouselKeys.detail(projectId) });
    },
  });
}
```

---

## 5. Frontend Template → Strategy Mapping

Replace the current `selectedTemplate: number` with a strategy name that gets sent to the API:

```typescript
// app/dashboard/create/constants.ts
export const CREATE_TEMPLATES = [
  { icon: "📊", name: "Analysis",      desc: "Deep dive with data",     strategy: "stat_card_grid" },
  { icon: "⚖️", name: "Comparison",    desc: "Side by side",           strategy: "feature_grid" },
  { icon: "📚", name: "Tutorial",      desc: "Step by step",           strategy: "numbered_list" },
  { icon: "📰", name: "News Flash",    desc: "Quick update",           strategy: "hero_content" },
  { icon: "🧠", name: "Deep Dive",     desc: "Comprehensive",          strategy: "insight_quote" },
  { icon: "🎯", name: "Listicle",      desc: "Top N format",           strategy: "feature_grid" },
] as const;
```

Worksflow:
1. User selects a template at creation → `selectedTemplate` maps to `strategy`
2. On publish → `CarouselCreateRequest` includes `strategy` field
3. Pipeline stores strategy on `CarouselProject`
4. After generation, user can change strategy → `POST /slides/regenerate?strategy=new_name`
5. Frontend reads back `project.slide_layout_strategy` to highlight active template

---

## 6. Gherkin Feature File

`tests/features/carousel_slide_layout_strategies.feature`:

```gherkin
Feature: Carousel Slide Layout Strategies
  As a content creator
  I want to select different slide layout strategies for my carousel
  So that I can choose the visual format that best communicates my content

  Background:
    Given a completed carousel project with 7 slides
    And the project has persisted SlideData with features, stats, and insight

  Scenario: Select stat_card_grid strategy
    Given a carousel with 3 content slides
    When I select the "stat_card_grid" strategy
    Then content slides render stats as 3-column cards
    And the HTML contains ".stat-card-grid" selector
    And each stat card shows a value, label, and detail

  Scenario: Select feature_grid strategy
    Given a carousel with 3 content slides
    When I select the "feature_grid" strategy
    Then content slides render features as a 2-column grid
    And the HTML contains ".feature-grid" selector
    And each feature card shows an icon, title, and body

  Scenario: Select insight_quote strategy
    Given a carousel with a closing slide containing insight data
    When I select the "insight_quote" strategy
    Then the closing slide renders an accent-bordered quote card
    And the HTML contains the quote text and attribution

  Scenario: Fallback for missing data
    Given a carousel with no stats data
    When I select the "stat_card_grid" strategy
    Then the strategy falls back to "hero_content" layout
    And renders heading and body only

  Scenario: Intro and CTA slides ignore strategy
    Given any selected strategy
    When rendering an intro or CTA slide
    Then the intro uses "intro_hero" layout regardless
    And the CTA uses "cta_centered" layout regardless

  Scenario: Strategy not found returns 422
    Given an invalid strategy name "nonexistent"
    When I POST to /slides/regenerate?strategy=nonexistent
    Then the API returns 422 Unprocessable Entity

  Scenario: List available strategies
    When I GET /strategies
    Then the response contains a strategies array
    And each strategy has name and display_name

  Scenario: Active strategy persisted and readable
    Given I have applied the "feature_grid" strategy
    When I GET the carousel project
    Then the response includes slide_layout_strategy: "feature_grid"

  Scenario: Theme and strategy are orthogonal
    Given any selected strategy
    When I apply a "cybersecurity" theme
    Then the strategy renders with cybersecurity colors
    And the strategy produces the same layout structure

  Scenario: Bilingual rendering with strategy
    Given a bilingual carousel (pt + en)
    When I select any strategy
    Then EN slides use the same strategy layout with translated text
    And stat values and feature text are translated
```

---

## 7. Test Plan

### 7.1 Unit Tests — Strategy Interface

```python
# tests/unit/application/strategies/test_strategy_interface.py

class TestSlideLayoutStrategyInterface:
    """Every strategy must satisfy the Protocol contract."""

    def test_strategy_has_required_attributes(self, all_strategies):
        """Each strategy has strategy_name, display_name, supported_slide_types."""
        for strategy in all_strategies:
            assert isinstance(strategy.strategy_name, str)
            assert len(strategy.strategy_name) > 0
            assert isinstance(strategy.display_name, str)
            assert isinstance(strategy.supported_slide_types, frozenset)

    def test_render_returns_string(self, all_strategies, sample_slide, sample_project, sample_theme):
        """render() produces non-empty HTML."""
        for strategy in all_strategies:
            if sample_slide["type"] in strategy.supported_slide_types:
                html = strategy.render(sample_slide, sample_project, sample_theme, 7, "pt")
                assert isinstance(html, str)
                assert len(html) > 0

    def test_render_escapes_html(self, all_strategies_with_support, sample_project, sample_theme):
        """HTML entities in heading/body are escaped."""
        ...

    def test_render_no_data_fields_graceful(self, all_strategies):
        """When features/stats/insight are None, strategy degrades to heading+body."""
        ...
```

### 7.2 Unit Tests — Per Strategy

```python
class TestStatCardGridStrategy:
    def test_renders_three_column_grid(self, sample_slide_with_stats, ...): ...
    def test_renders_up_to_four_cards(self, sample_slide_with_four_stats, ...): ...
    def test_falls_back_to_hero_when_no_stats(self, sample_slide_without_stats, ...): ...

class TestFeatureGridStrategy:
    def test_renders_two_column_grid(self, sample_slide_with_features, ...): ...
    def test_renders_up_to_four_features(self, ...): ...
    def test_falls_back_to_hero_when_no_features(self, ...): ...

class TestInsightQuoteStrategy:
    def test_renders_quote_with_border(self, sample_slide_with_insight, ...): ...
    def test_renders_attribution(self, ...): ...
    def test_falls_back_to_hero_when_no_insight(self, ...): ...

class TestNumberedListStrategy:
    def test_renders_numbered_steps(self, sample_slide_with_features, ...): ...
    def test_numbers_are_one_based(self, ...): ...
    def test_falls_back_to_hero_when_no_features(self, ...): ...
```

### 7.3 Unit Tests — Registry

```python
class TestSlideLayoutRegistry:
    def test_register_and_retrieve(self, registry, strategy): ...
    def test_raises_on_duplicate(self, registry, strategy): ...
    def test_raises_on_not_found(self, registry): ...
    def test_lists_all_strategies(self, registry): ...
    def test_find_for_slide_returns_matching(self, registry): ...
    def test_find_for_slide_returns_fallback(self, registry): ...
```

### 7.4 Integration Tests — API Endpoints

```python
class TestStrategyEndpoints:
    async def test_regenerate_with_valid_strategy(self, client, completed_project): ...
    async def test_regenerate_with_invalid_strategy_returns_422(self, client): ...
    async def test_list_strategies(self, client): ...
    async def test_project_returns_strategy_field(self, client, completed_project): ...
```

### 7.5 Property Tests

```python
class TestStrategyProperties:
    """Property-based tests using Hypothesis."""

    @given(st.text(), st.text())
    def test_all_strategies_produce_valid_html_fragment(self, heading, body):
        """Any string input produces well-formed HTML (no unclosed tags)."""
        ...

    @given(st.sampled_from(ALL_THEMES), st.sampled_from(ALL_STRATEGY_NAMES))
    def test_all_theme_strategy_combinations_produce_html(self, theme, strategy_name):
        """Every (theme × strategy) pair produces non-empty output."""
        ...
```

### 7.6 Test Fixtures

New fixtures needed:

| Fixture | Purpose |
|---------|---------|
| `sample_slide_with_stats` | SlideDict with 2-3 stat items |
| `sample_slide_with_features` | SlideDict with 2-4 feature items |
| `sample_slide_with_insight` | SlideDict with insight quote |
| `sample_slide_with_all_data` | SlideDict with stats + features + insight |
| `all_strategies` | All registered strategy instances |
| `registry` | Populated SlideLayoutRegistry |
| `sample_project_with_watermark` | CarouselProject with creator metadata |

---

## 8. Implementation Order

| Phase | Task | Files |
|-------|------|-------|
| **P1** | Define `SlideLayoutStrategy` Protocol | `domain/protocols/carousel.py` |
| **P1** | Add `slide_layout_strategy` field to `CarouselProject` | `domain/models/carousel.py` |
| **P1** | Add field to `CarouselProjectResponse` + `CarouselProjectCreate` | `api/schemas/carousel.py` |
| **P2** | Create `SlideLayoutRegistry` | `application/services/carousel/strategies/registry.py` |
| **P2** | Extract existing renderers as strategies (intro_hero, hero_content, cta_centered) | `strategies/intro_strategy.py`, `hero_content.py`, `cta.py` |
| **P3** | Implement structured strategies (stat_card_grid, feature_grid, insight_quote, numbered_list) | `strategies/stat_card_grid.py`, `feature_grid.py`, `insight_quote.py`, `numbered_list.py` |
| **P3** | Write CSS for new layout types | `neon_slide_styles.py` (extend) |
| **P4** | Update `build_carousel_html()` to use registry dispatch | `html_template.py` |
| **P4** | Wire registry in DI container | `infrastructure/container.py` |
| **P5** | Add API endpoints | `api/routes/carousels/strategies.py` |
| **P5** | Update frontend template selector to send strategy | `constants.ts`, `types.ts`, schema |
| **P6** | Add Gherkin feature file | `tests/features/carousel_slide_layout_strategies.feature` |
| **P6** | Write all unit tests | `tests/unit/application/strategies/` |
| **P6** | Write integration tests | `tests/integration/test_strategy_endpoints.py` |
| **P7** | Add property tests | `tests/property/test_strategy_properties.py` |

---

## 9. Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Strategy renders without structured data | Medium | Low — falls back to heading+body | Registry `find_for_slide()` uses fallback; each strategy checks data presence |
| Theme colors don't apply to new CSS | Low | Medium — visual inconsistency | Strategy CSS uses CSS variables (`var(--primary)`, `var(--accent)`, `var(--bg)`) from existing theme system |
| New strategy CSS conflicts with existing | Low | Medium — layout breakage | Each strategy's CSS is scoped under a unique class (e.g. `.stat-card-grid`) |
| Registry not thread-safe | Low | Low — concurrent strategy lookup | Registry built at container bootstrap; reads are concurrent-safe, writes happen once |
| Strategy name collisions between features | Low | Medium — silent override accepted | Registry raises `ValueError` on duplicate registration |
| Frontend sends outdated strategy to old backend version | Medium | Low — API returns 422 | Graceful 422 with message listing available strategies |
| Slide data missing `features`/`stats`/`insight` after pipeline change | Medium | Medium — strategy renders fallback | `unpack_extras()` ensures all fields are present or None; strategies handle None gracefully |

---

## 10. Design Decisions

### Why Protocol over ABC?
The existing codebase uses `Protocol` for all interfaces (`ImageStyleStrategy`, `CarouselExportService`, etc.). ADR-002 and `AGENTS.md` mandate Protocol-based DI. ABC would be inconsistent.

### Why not template_version for dispatch?
`template_version` (`"v1"`/`"v2"`) was designed for A/B testing the entire template shell, not per-slide layout selection. The new `slide_layout_strategy` field is orthogonal and more granular.

### Why not LangGraph nodes for strategies?
Strategies are pure rendering functions with no LLM calls, no state, and no tool use. LangGraph would add unnecessary complexity. The strategy registry is a simple dict lookup.

### Why keep intro_hero and cta_centered as separate strategies?
Even though they look different from intro/CTA, they have unique HTML structure (badge dot, avatar, swipe text) that doesn't fit the hero_content template. Keeping them separate avoids conditional logic inside the renderer.

### How are strategies versioned?
Each strategy's CSS and HTML is versioned via its import path. When a strategy needs breaking changes, create a new file (e.g. `stat_card_grid_v2.py`), register with a different name (`stat_card_grid_v2`), and keep the old one for backward compatibility. The `template_version` field on `CarouselProject` controls which strategy version to default to.

---

## 11. Design Addendum — Visual Changes & Template Identity

This section covers design work beyond the strategy pattern: visual identity per template, improvement plan items P1/P2/P5, and shared utility extraction.

### 11.1 Do Templates Need Distinct Visual DNA?

The 6 frontend templates currently differ only by **layout strategy** (which data fields render, in what grid). But should they also have distinct **visual personality** — different border treatments, spacing, or accent colors?

| Template | Strategy | Visual DNA Recommendation |
|----------|----------|--------------------------|
| **Analysis** | `stat_card_grid` | No changes needed — stat cards already distinguish it |
| **Comparison** | `feature_grid` | No changes needed — 2-col grid is distinctive |
| **Tutorial** | `numbered_list` | No changes needed — numbered steps are distinctive |
| **News Flash** | `hero_content` | Could benefit from a top banner/strip accent |
| **Deep Dive** | `insight_quote` | No changes needed — quote card is distinctive |
| **Listicle** | `feature_grid` | Same as Comparison — could add a list-style marker |

**Verdict:** The existing layout strategy is sufficient visual differentiation for 5/6 templates. Only **News Flash** (`hero_content`) looks like the default — it has no distinctive visual element. A candidate fix: add a top accent strip to News Flash slides. This is low-effort CSS and can be a separate ticket.

### 11.2 P1 — Slide 7 Hero-Bg Layout

The closing CTA slide (slide 7) uses a plain dark background with centered avatar. It should use the **hero-bg** layout (full-bleed image + gradient) for visual continuity with slides 1-6.

**Changes:**
- `cta_centered` strategy: wrap content in `.slide-hero-bg-img` + `.slide-hero-bg-gradient` + `.slide-hero-content` structure
- CSS: add `.slide-hero-content .closing-avatar` positioning override (centered, not bottom-aligned)
- The watermark is unnecessary on slide 7 (avatar already shows creator identity)

**Effort:** Low. ~10 lines CSS + strategy HTML template change.

### 11.3 P2 — Watermark Reduction

Current: watermark on slides 2, 3, 4, 5, 6 (5 appearances).
Target: watermark only on slide 2 (the first content/summary slide).

**Changes:**
- `hero_content` strategy: add `include_watermark` flag, default `True`, set to `False` for slides 3+
- `html_template.py`: pass slide position to strategy so it knows whether to render watermark
- The watermark module in `html_template._build_watermark_html()` remains the canonical source

**Effort:** Low. ~5 lines in dispatch logic + remove `watermark_html` param from non-summary strategy calls.

### 11.4 P5 — Per-Slide CTAs

Directional CTAs ("Continue →") on early slides (1-2) and primary action CTA ("Salve", "Siga") on slide 7.

**Changes:**
- Already partially done: `.s1-swipe` on slide 1 shows "Deslize →"
- Add slide 2: same swipe text in the hero-content footer
- Slide 7: currently shows "Siga para mais conteúdo como esse" — this is sufficient per research
- **No change needed** for mid-slide CTAs (rejected by research — see improvement plan)

**Effort:** Trivial. Add swipe text to `hero_content` strategy for slide 2 only.

### 11.5 Watermark Utility Dedup

`hero_content` strategy has its own `_build_watermark()` method — a copy of `html_template._build_watermark_html()`. This should be a shared utility.

**Refactor:**
- Keep `html_template._build_watermark_html()` as the canonical source
- `hero_content` strategy calls it instead of its own copy
- Import from `html_template` or extract to `helpers.py`

**Effort:** Trivial. Remove 25 lines duplicated code.

### 11.6 Recommended Design Ticket

These changes are small, well-scoped, and independent of the strategy API. They can be a single T1 or T2 ticket:

> **AE-0007** — Carousel Visual Design Improvements (T1/T2)
> - P1: Slide 7 hero-bg layout
> - P2: Watermark reduction to slide 2 only
> - P5: Per-slide CTAs (slide 2 swipe text)
> - Watermark utility dedup
> - News Flash template accent strip (optional)

**Dependencies:** None — independent of AE-0005/AE-0004/AE-0006.
**Order:** Do before or in parallel with AE-0005, since AE-0005's API changes touch some of the same dispatch code.
