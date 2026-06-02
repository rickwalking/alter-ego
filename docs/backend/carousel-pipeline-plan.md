# Backend Blog/Content Pipeline Plan

> **Status: Superseded** — See [Carousel Pipeline Consolidation Plan](../plans/carousel-pipeline-consolidation.md) and [ADR-007](../decisions/0007-consolidate-carousel-pipelines-under-deepagents.md). Legacy `CarouselAgent` / monolith graph paths are being retired in favor of the editorial workflow orchestrator.

## Overview

The carousel content pipeline is implemented as a **sub-agent** (`CarouselAgent`) that the main `RAGAgent` delegates to when users request carousel/blog generation. The sub-agent executes a 7-phase workflow based on the `carousel-pipeline` skill located at `~/.claude/skills/carousel-pipeline/`.

## Source Skill Reference

The pipeline behavior is defined by the **carousel-pipeline** skill:

| File | Purpose |
|------|---------|
| `SKILL.md` | Skill manifest — declares tools (Agent, Bash, WebFetch, WebSearch, Playwright MCP) and triggers (`"create a carousel"`, `"create a new social media post"`) |
| `workflow.md` | Full 7-phase execution rules — system prompt, research agent dispatch, title optimization criteria, content synthesis rules, design system specs, image generation prompts, Playwright export code, caption structure |
| `bmad-skill-manifest.yaml` | BMAD skill type declaration (`type: skill`) |

### Key Rules from `workflow.md`

**System Prompt Persona:** Professional content strategist, visual designer, and Instagram carousel expert. Deep, fact-checked information in Brazilian Portuguese. Informative, assertive, direct tone. **Never uses em dashes (—).** Takes creative initiative and explains every decision.

**Input Schema (from skill):**
```yaml
title: string           # Working title (MUST improve if weak)
audience: string        # e.g., "AI, software developers, architects"
niche: string           # e.g., "AI/Tech", "Cybersecurity"
slides: string          # e.g., "1 intro, 3 content, 2 closing"
aspect_ratio: string    # Default: "1080x1350 (Instagram portrait)"
sources: list[string]   # URLs to X posts, GitHub issues, blog posts
language: string        # Default: "pt-BR" (Brazilian Portuguese)
generate_images: bool   # Default: true
```

**Research Phase:** Dispatch 3-4 agents IN PARALLEL targeting different source types:
- Agent 1: Twitter/X & primary sources (Playwright MCP: `browser_navigate` + `browser_snapshot`)
- Agent 2: News & blog articles (WebSearch + WebFetch across tech publications)
- Agent 3: Reddit & community (r/programming, r/ClaudeAI, r/LocalLLaMA, Hacker News)
- Agent 4: Technical sources (GitHub issues, CVEs, advisories, vendor analyses)

**Title Optimization Criteria:** Scroll-stop power, emotional pull, max ~60 chars, concrete > generic. Must propose 3 alternatives with rationale if original is weak.

**Writing Rules:**
- Language: Brazilian Portuguese, informal but professional
- NEVER use em dashes (—). Use periods, commas, parentheses, or conjunctions
- Short paragraphs (2-4 sentences max)
- `<strong>` for key terms/numbers, `.code-tag` for technical terms
- Every factual claim must have at least one authoritative source

**Image Generation:** Google Gemini `gemini-3.1-flash-image-preview` via `google-genai` SDK. Comic/manga style, 3:1 ratio, no text, dark background with palette accents. Generate 4 images (one per content-heavy slide). 2-3 second delay between API calls.

**Export:** Playwright screenshots at 1080x1350, quality 95 JPEG. Embed images as base64 data URIs in self-contained HTML.

## Architecture

```
RAGAgent (main DeepAgent)
├── Tools: search_documents, get_conversation_history
└── Delegates to:
    └── CarouselAgent (sub-agent)
        ├── System Prompt: carousel-pipeline skill (workflow.md, 7 phases)
        ├── Tools: ResearchTool, ImageGenerationTool, CarouselExportTool
        └── Output: CarouselProject + slides + images + blog post + caption
```

## Agent Hierarchy

### RAGAgent (existing)
- Orchestrates RAG conversations
- Gets new `generate_carousel` tool
- Delegates carousel generation to sub-agent

### CarouselAgent (new)
- Specialized in carousel + blog content generation
- Executes 7-phase workflow autonomously
- Uses tools for research, image generation, and export
- Follows `carousel-pipeline/workflow.md` rules for every phase

## 7-Phase Pipeline

| Phase | Name | Tool/Service | Output | Skill Rule |
|-------|------|--------------|--------|------------|
| 1 | Research | `ResearchTool` (Playwright MCP) | `ResearchSource[]` | 3-4 parallel agents, different source types |
| 2 | Title Optimization | `LLMService` | Optimized title | Scroll-stop criteria, 3 alternatives if weak |
| 3 | Content Synthesis | `LLMService` | `CarouselSlide[]` + blog markdown | pt-BR, no em dashes, fact-checked |
| 4 | Design System | Built-in Python templating | HTML + CSS | Unique palette, typography hierarchy |
| 5 | Image Generation | `ImageGenerationTool` (Gemini) | Image files | Comic/manga, 3:1, no text |
| 6 | Assembly & Export | `CarouselExportTool` (Playwright) | JPG files | 1080x1350, quality 95, base64 embed |
| 7 | Caption Generation | `LLMService` | Instagram caption | Hook + value + question + CTA + hashtags |

## New API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/carousels` | Create carousel project |
| `GET` | `/api/carousels` | List all carousels |
| `GET` | `/api/carousels/{id}` | Get project details with slides |
| `POST` | `/api/carousels/{id}/generate` | Trigger full pipeline (async) |
| `GET` | `/api/carousels/{id}/status` | Check generation status |
| `GET` | `/api/carousels/{id}/slides` | Get generated slides |
| `GET` | `/api/carousels/{id}/blog` | Get generated blog post (default pt-BR) |
| `GET` | `/api/carousels/{id}/blog/{lang}` | Get blog in specific language |
| `GET` | `/api/carousels/{id}/blog/{lang}?include_design=true` | Get blog + full design tokens |
| `GET` | `/api/carousels/{id}/design` | Get visual design tokens only |
| `GET` | `/api/carousels/{id}/images/{filename}` | Serve carousel image file |
| `POST` | `/api/carousels/{id}/caption` | Generate Instagram caption |
| `GET` | `/api/carousels/{id}/download` | Download carousel files (ZIP) |
| `DELETE` | `/api/carousels/{id}` | Delete project and files |

## i18n Blog Content System

### Design

Blog content is generated and stored per-language. Each carousel project stores blog markdown in both `pt-BR` (default) and `en`. The LLM generates both versions during Phase 3 (Content Synthesis).

### Backend i18n Interface

**New endpoint:** `GET /api/carousels/{id}/blog/{lang}` where `lang` is `pt` or `en`.

**New schema:**
```python
class CarouselBlogI18nResponse(BaseModel):
    markdown: str
    title: str
    subtitle: str | None
    language: str  # "pt" or "en"
    available_languages: list[str]  # ["pt", "en"]
```

**Route behavior:**
- `GET /api/carousels/{id}/blog` — returns default (pt-BR) for backward compatibility
- `GET /api/carousels/{id}/blog/pt` — returns Portuguese version
- `GET /api/carousels/{id}/blog/en` — returns English version
- If requested language doesn't exist, returns 404 with `available_languages`

### Content Generation (Phase 3 Update)

The LLM prompt in Phase 3 is updated to request bilingual output:
```
Return ONLY a JSON object with keys:
- slides: array of {number, type, heading, body, image_prompt} in pt-BR
- blog_pt: full blog post in pt-BR markdown
- blog_en: full blog post in English markdown
- title_pt, title_en, subtitle_pt, subtitle_en
```

Both versions follow the same `workflow.md` writing rules — the English version uses professional, direct tone matching the Portuguese original's depth and structure.

## Blog Visual Design System (Backend-Driven)

### Design

The frontend blog pages must NOT hardcode themes, colors, typography, or images. Everything is generated by the backend pipeline and retrieved via API. Each carousel/blog post gets a **unique, self-contained visual identity** defined during Phase 4 (Design System) of the pipeline.

The frontend receives a complete design token set and applies it dynamically. This means:
- Every blog post has its own color palette (primary, accent, background, text variants)
- Every blog post has its own typography configuration (font families, sizes, weights)
- Every blog post has its own hero images and slide images (generated by Gemini in Phase 5)
- The frontend is a **theme consumer** — it reads tokens from the API and applies them via CSS custom properties

### Design Token Schema

Each carousel project stores a `design_tokens` JSON blob generated during Phase 4:

```python
class DesignTokens(TypedDict):
    """Complete visual design for a blog post / carousel."""
    colors: dict[str, str]       # primary, accent, bg, text, text_muted, text_dim, border, glow
    typography: dict[str, str]   # font_family_heading, font_family_body, font_family_badge
    images: dict[str, str]       # hero: "/api/carousels/{id}/images/hero", slides: [...]
    layout: dict[str, str | int] # badge_label, swipe_text, progress_segments
```

### Database Schema Addition

Add `design_tokens` JSON column to `carousel_projects`:
```python
design_tokens: Mapped[dict[str, Any]] = mapped_column(
    JSON, nullable=True, default=None,
    comment="Complete visual design: colors, typography, images, layout"
)
```

### API Endpoint — Visual Design

**New endpoint:** `GET /api/carousels/{id}/design`

**New schema:**
```python
class CarouselDesignResponse(BaseModel):
    """Complete visual design tokens for a blog post."""
    colors: dict[str, str]
    typography: dict[str, str]
    images: dict[str, str | list[str]]
    layout: dict[str, str | int]
    theme_name: str  # e.g., "ai_competition", "cybersecurity"
```

### Combined Blog + Design Endpoint

For efficiency, the blog endpoint can include design tokens inline:
```python
class CarouselBlogWithDesignResponse(BaseModel):
    markdown: str
    title: str
    subtitle: str | None
    language: str
    available_languages: list[str]
    design: CarouselDesignResponse  # Colors, typography, images
```

**Route:** `GET /api/carousels/{id}/blog/{lang}?include_design=true`

When `include_design=true`, the response includes the full visual design system. The frontend uses these tokens to:
1. Set CSS custom properties on a wrapper element (`--blog-primary`, `--blog-accent`, etc.)
2. Apply font families from `typography` to heading/body elements
3. Load hero images from `images.hero` URLs
4. Render the badge label, swipe text, and progress bar count from `layout`

### Phase 4 Update — Design Token Generation

The `CarouselTemplateBuilder._resolve_theme()` method is extended to output a structured token object instead of just inline CSS:

```python
# application/services/carousel_template.py
def generate_design_tokens(project: CarouselProject) -> DesignTokens:
    """Generate complete design tokens for a blog post."""
    theme = THEME_PALETTES.get(project.theme.value, THEME_PALETTES["ai_competition"])
    return DesignTokens(
        colors={
            "primary": theme["primary"],
            "accent": theme["accent"],
            "bg": theme["background"],
            "text": "#ffffff",
            "text_muted": "rgba(255,255,255,0.63)",
            "text_dim": "rgba(255,255,255,0.48)",
            "border": f"{theme['primary']}33",
            "glow": f"{theme['primary']}0D",
        },
        typography={
            "font_family_heading": "'Segoe UI', 'Helvetica Neue', Arial, sans-serif",
            "font_family_body": "'Segoe UI', 'Helvetica Neue', Arial, sans-serif",
            "font_family_badge": "'Courier New', monospace",
        },
        images={
            "hero": f"/api/carousels/{project.id}/images/hero",
            "slides": [
                f"/api/carousels/{project.id}/images/slide_{i}"
                for i in range(1, 5)
            ],
        },
        layout={
            "badge_label": project.niche,
            "swipe_text": "Deslize →" if project.language == "pt-BR" else "Swipe →",
            "progress_segments": 6,
        },
    )
```

### Image Serving

Carousel images are served as static files from the output directory:

**New endpoint:** `GET /api/carousels/{id}/images/{filename}`

Returns the image file (JPEG) with proper `Content-Type` and caching headers. Files are read from `project.output_dir`.

### Frontend Integration Pattern

The frontend blog page (`/blog/[slug]`) fetches design tokens and applies them:

```
1. Fetch blog content with ?include_design=true
2. Extract design.colors, design.typography, design.images
3. Apply colors as CSS custom properties on wrapper div:
   style={{
     "--blog-primary": design.colors.primary,
     "--blog-accent": design.colors.accent,
     "--blog-bg": design.colors.bg,
     ...
   }}
4. Apply typography from design.typography to heading/body elements
5. Load hero image from design.images.hero
6. Remove all hardcoded theme references — everything comes from API
```

This eliminates the current `BLOG_THEME_COLORS` constant map in `frontend/src/constants/blog.ts`. The frontend becomes a **generic theme renderer** that works with any design token set the backend provides.

## New Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `GEMINI_API_KEY` | Google Gemini API key for image generation | Yes |
| `CAROUSEL_OUTPUT_DIR` | Directory for carousel output files | No (default: `./output/carousels`) |
| `PLAYWRIGHT_BROWSER_PATH` | Custom browser path for Playwright | No |

## File Structure

```
backend/src/rag_backend/
├── domain/
│   ├── models.py                  # + CarouselProject, CarouselSlide, ResearchSource
│   ├── protocols.py               # + CarouselRepository, CarouselAgent
│   └── constants.py               # + Carousel constants
├── application/
│   └── services/
│       ├── carousel_agent.py      # Sub-agent with 7-phase workflow
│       └── tools/
│           ├── research_tool.py   # Web scraping via Playwright MCP
│           ├── image_tool.py      # Gemini image generation
│           └── export_tool.py     # Playwright HTML -> JPG
├── infrastructure/
│   ├── database/
│   │   ├── models.py              # + CarouselProjectModel, CarouselSlideModel, ResearchSourceModel
│   │   └── carousel_repository.py # PostgresCarouselRepository
│   ├── external/
│   │   ├── gemini_image.py        # google-genai wrapper
│   │   └── playwright_export.py   # Playwright screenshot service
│   └── container.py               # + new providers
└── api/
    ├── schemas.py                 # + Carousel schemas
    ├── routes/
    │   └── carousels.py           # New router
    └── app.py                     # + mount carousels router
```

## Data Flow

```
User Request (POST /api/carousels/{id}/generate)
    ↓
CarouselAgent.execute(project_id)
    ↓
Phase 1: ResearchTool.scrape(sources) -> ResearchSource[]
    ↓
Phase 2: LLMService.generate(title_prompt) -> optimized_title (pt + en)
    ↓
Phase 3: LLMService.generate(content_prompt) -> CarouselSlide[] + blog_pt + blog_en
    ↓
Phase 4: CarouselDesignService.generate(theme, slides) -> HTML string
    ↓
Phase 5: ImageGenerationTool.generate(prompts) -> image files
    ↓
Phase 6: CarouselExportTool.export(html, images) -> JPG files
    ↓
Phase 7: LLMService.generate(caption_prompt) -> caption
    ↓
Update CarouselProject status -> COMPLETED
    ↓
Return CarouselProjectResponse
```

## Status Enum

```
PENDING -> RESEARCHING -> DRAFTING -> DESIGNING -> GENERATING_IMAGES -> EXPORTING -> COMPLETED
                                    └-> FAILED (at any phase)
```

## Theme System

Each carousel gets a unique color palette. Available themes:

| Theme | Primary | Accent | Background | Use Case |
|-------|---------|--------|------------|----------|
| `cybersecurity` | `#ef4444` | `#00d4ff` | `#0a0e17` | Security/attacks |
| `ai_competition` | `#3b82f6` | `#f59e0b` | `#0a0e17` | AI models/competitions |
| `developer_skills` | `#0ac5a8` | `#8b5cf6` | `#080c12` | Dev skills/tutorials |
| `source_code` | `#a855f7` | `#f97316` | `#0c0a14` | Code leaks/open source |
| `social_engineering` | `#f59e0b` | `#ef4444` | `#0a0c14` | Social engineering |
| `auto` | (generated) | (generated) | (generated) | Auto-generated from topic |

## Implementation Snippets

### 0. Domain Model — `design_tokens` field

```python
# domain/models.py — CarouselProject dataclass
from typing import TypedDict

class DesignTokenColors(TypedDict):
    primary: str
    accent: str
    bg: str
    text: str
    text_muted: str
    text_dim: str
    border: str
    glow: str

class DesignTokenTypography(TypedDict):
    font_family_heading: str
    font_family_body: str
    font_family_badge: str

class DesignTokenImages(TypedDict):
    hero: str
    slides: list[str]

class DesignTokenLayout(TypedDict):
    badge_label: str
    swipe_text: str
    progress_segments: int

class DesignTokens(TypedDict):
    colors: DesignTokenColors
    typography: DesignTokenTypography
    images: DesignTokenImages
    layout: DesignTokenLayout

@dataclass
class CarouselProject:
    # ... existing fields ...
    design_tokens: DesignTokens | None = None

    def get_design(self) -> DesignTokens | None:
        """Return complete design tokens for frontend consumption."""
        return self.design_tokens

    def get_image_url(self, filename: str) -> str | None:
        """Get the API URL for a carousel image."""
        if not self.output_dir:
            return None
        return f"/api/carousels/{self.id}/images/{filename}"
```

### 1. Domain Model — `blog_translations` field

```python
# domain/models.py — CarouselProject dataclass
@dataclass
class CarouselProject:
    # ... existing fields ...
    blog_markdown: str | None = None           # Default language (pt-BR)
    blog_translations: dict[str, str] | None = None  # {"pt": "...", "en": "..."}
    caption: str | None = None

    def get_blog(self, language: str = "pt") -> str | None:
        """Get blog markdown for a specific language."""
        if self.blog_translations and language in self.blog_translations:
            return self.blog_translations[language]
        return self.blog_markdown

    def get_available_languages(self) -> list[str]:
        """Return list of available blog languages."""
        langs = []
        if self.blog_translations:
            langs = list(self.blog_translations.keys())
        elif self.blog_markdown:
            langs = ["pt"]
        return langs
```

### 2. SQLAlchemy ORM — JSON column

```python
# infrastructure/database/models.py
class CarouselProjectModel(Base):
    # ... existing columns ...
    blog_markdown = Column(Text, nullable=True)
    blog_translations = Column(JSON, nullable=True)
    caption = Column(Text, nullable=True)

    def to_entity(self) -> CarouselProject:
        return CarouselProject(
            # ... existing fields ...
            blog_markdown=self.blog_markdown,
            blog_translations=self.blog_translations,
            caption=self.caption,
        )

    def update_from_entity(self, entity: CarouselProject) -> None:
        # ... existing updates ...
        self.blog_markdown = entity.blog_markdown
        self.blog_translations = entity.blog_translations
        self.caption = entity.caption
```

### 3. Pydantic Schema — i18n blog response

```python
# api/schemas.py
class CarouselBlogI18nResponse(BaseModel):
    """Schema for localized blog post response."""
    markdown: str
    title: str
    subtitle: str | None
    language: str  # "pt" or "en"
    available_languages: list[str]

    model_config = {"from_attributes": False}  # Not mapped from ORM directly
```

### 4. Route — i18n blog endpoint

```python
# api/routes/carousels.py
@router.get("/{project_id}/blog/{lang}", response_model=CarouselBlogI18nResponse)
async def get_carousel_blog_i18n(
    project_id: UUID,
    lang: Annotated[str, Path(pattern="^(pt|en)$")],
    repo: Annotated[CarouselRepository, Depends(get_carousel_repo)],
) -> CarouselBlogI18nResponse:
    """Get the generated blog post in a specific language."""
    project = await repo.get_project_by_id(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Carousel project not found")

    blog_content = project.get_blog(lang)
    if blog_content is None:
        raise HTTPException(
            status_code=404,
            detail=f"Blog post not available in '{lang}'",
            headers={"X-Available-Languages": ",".join(project.get_available_languages())},
        )

    return CarouselBlogI18nResponse(
        markdown=blog_content,
        title=project.title or project.topic,
        subtitle=project.subtitle,
        language=lang,
        available_languages=project.get_available_languages(),
    )
```

### 5. CarouselTemplate — bilingual content prompt

```python
# application/services/carousel_template.py
@staticmethod
def build_content_prompt(project: CarouselProject, research_context: str) -> str:
    """Build prompt for bilingual content synthesis."""
    return (
        f"Create a 6-slide Instagram carousel and a blog post in TWO languages.\n\n"
        f"Topic: {project.topic}\n"
        f"Title: {project.title}\n"
        f"Subtitle: {project.subtitle}\n"
        f"Audience: {project.audience}\n\n"
        f"Research context:\n{research_context}\n\n"
        f"Slide structure:\n"
        f"1. Intro: hook + hero image\n"
        f"2-4. Content: deep information with stats/quotes\n"
        f"5. Closing: actionable takeaways\n"
        f"6. CTA: save + share\n\n"
        f"Return ONLY a JSON object with keys:\n"
        f"- slides: array of {{number, type, heading, body, image_prompt}} in pt-BR\n"
        f"- blog_pt: full blog post in pt-BR markdown\n"
        f"- blog_en: full blog post in English markdown\n"
        f"- title_pt, title_en, subtitle_pt, subtitle_en\n\n"
        f"Rules:\n"
        f"- pt-BR version: informal Brazilian Portuguese, engaging\n"
        f"- EN version: professional, direct, same depth and structure\n"
        f"- NEVER use em dashes (—) in either language\n"
        f"- Each slide must have complete explanatory content\n"
        f"- image_prompt: describe the scene for comic/manga style generation\n"
    )
```

### 6. CarouselAgent — parse bilingual response

```python
# application/services/carousel_agent.py — inside _phase2_3_content
try:
    content_data = json.loads(content_response)
    # ... slides parsing (existing) ...

    blog_pt = content_data.get("blog_pt", "")
    blog_en = content_data.get("blog_en", "")

    project.blog_markdown = blog_pt  # Default language
    project.blog_translations = {"pt": blog_pt, "en": blog_en}

    # Also update title/subtitle for both languages
    project.set_title(
        title=title_data.get("title_pt", project.topic),
        subtitle=title_data.get("subtitle_pt"),
    )

except (json.JSONDecodeError, KeyError):
    # Fallback (existing behavior)
    slides_data = [...]
    blog_markdown = ""
```

### 7. Repository — carousel_repository fixture for tests

```python
# tests/conftest.py
@pytest.fixture
def carousel_repository(db_session: AsyncSession) -> PostgresCarouselRepository:
    """Create a carousel repository instance."""
    return PostgresCarouselRepository(db_session)

@pytest.fixture
def sample_carousel_project() -> CarouselProject:
    """Create a sample carousel project with bilingual blog."""
    project = CarouselProject(
        topic="Machine Learning Basics",
        audience="Beginners",
        niche="AI Education",
        theme=CarouselTheme.AI_COMPETITION,
    )
    project.blog_markdown = "# ML Básico\n\nConteúdo em português."
    project.blog_translations = {
        "pt": "# ML Básico\n\nConteúdo em português.",
        "en": "# ML Basics\n\nContent in English.",
    }
    return project
```

### 8. Integration test — i18n blog endpoint

```python
# tests/integration/test_carousel_api.py
@pytest.mark.asyncio
async def test_get_carousel_blog_i18n_portuguese(self, client):
    """Given carousel with bilingual blog, when GET /blog/pt, then returns pt version."""
    # Create carousel
    payload = {"topic": "Test", "audience": "Everyone", "niche": "Tech"}
    create_resp = await client.post("/api/carousels", json=payload)
    carousel_id = create_resp.json()["id"]

    # Manually set blog_translations via direct DB access or mock
    # ... then test ...
    response = await client.get(f"/api/carousels/{carousel_id}/blog/pt")
    assert response.status_code == 200
    data = response.json()
    assert data["language"] == "pt"
    assert "português" in data["markdown"]

@pytest.mark.asyncio
async def test_get_carousel_blog_i18n_english(self, client):
    """Given carousel with bilingual blog, when GET /blog/en, then returns en version."""
    # ... setup ...
    response = await client.get(f"/api/carousels/{carousel_id}/blog/en")
    assert response.status_code == 200
    data = response.json()
    assert data["language"] == "en"
    assert "English" in data["markdown"]

@pytest.mark.asyncio
async def test_get_carousel_blog_i18n_unavailable(self, client):
    """Given carousel without en blog, when GET /blog/en, then returns 404 with available langs."""
    # ... setup with pt-only blog ...
    response = await client.get(f"/api/carousels/{carousel_id}/blog/en")
    assert response.status_code == 404
    assert "pt" in response.headers.get("x-available-languages", "")
```

### 9. Design Tokens — generation in CarouselTemplateBuilder

```python
# application/services/carousel_template.py
from rag_backend.domain.models import CarouselProject, DesignTokens

THEME_PALETTES: dict[str, dict[str, str]] = {
    "cybersecurity": {"primary": "#ef4444", "accent": "#00d4ff", "background": "#0a0e17"},
    "ai_competition": {"primary": "#3b82f6", "accent": "#f59e0b", "background": "#0a0e17"},
    "developer_skills": {"primary": "#0ac5a8", "accent": "#8b5cf6", "background": "#080c12"},
    "source_code": {"primary": "#a855f7", "accent": "#f97316", "background": "#0c0a14"},
    "social_engineering": {"primary": "#f59e0b", "accent": "#ef4444", "background": "#0a0c14"},
}

@staticmethod
def generate_design_tokens(project: CarouselProject) -> DesignTokens:
    """Generate complete design tokens for a blog post."""
    theme = THEME_PALETTES.get(project.theme.value, THEME_PALETTES["ai_competition"])
    primary = theme["primary"]
    accent = theme["accent"]
    bg = theme["background"]
    swipe_text = "Deslize →" if project.language == "pt-BR" else "Swipe →"

    return DesignTokens(
        colors=DesignTokenColors(
            primary=primary,
            accent=accent,
            bg=bg,
            text="#ffffff",
            text_muted="rgba(255,255,255,0.63)",
            text_dim="rgba(255,255,255,0.48)",
            border=f"{primary}33",
            glow=f"{primary}0D",
        ),
        typography=DesignTokenTypography(
            font_family_heading="'Segoe UI', 'Helvetica Neue', Arial, sans-serif",
            font_family_body="'Segoe UI', 'Helvetica Neue', Arial, sans-serif",
            font_family_badge="'Courier New', monospace",
        ),
        images=DesignTokenImages(
            hero=f"/api/carousels/{project.id}/images/hero",
            slides=[f"/api/carousels/{project.id}/images/slide_{i}" for i in range(1, 5)],
        ),
        layout=DesignTokenLayout(
            badge_label=project.niche,
            swipe_text=swipe_text,
            progress_segments=6,
        ),
    )
```

### 10. Route — design tokens endpoint

```python
# api/routes/carousels.py
from rag_backend.api.schemas import CarouselDesignResponse

@router.get("/{project_id}/design", response_model=CarouselDesignResponse)
async def get_carousel_design(
    project_id: UUID,
    repo: Annotated[CarouselRepository, Depends(get_carousel_repo)],
) -> CarouselDesignResponse:
    """Get the visual design tokens for a carousel."""
    project = await repo.get_project_by_id(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Carousel project not found")
    if project.design_tokens is None:
        raise HTTPException(status_code=404, detail="Design tokens not yet generated")
    return CarouselDesignResponse.model_validate(project.design_tokens)
```

### 11. Route — image file serving

```python
# api/routes/carousels.py
from fastapi.responses import FileResponse

@router.get("/{project_id}/images/{filename}")
async def get_carousel_image(
    project_id: UUID,
    filename: str,
    repo: Annotated[CarouselRepository, Depends(get_carousel_repo)],
) -> FileResponse:
    """Serve a carousel image file."""
    project = await repo.get_project_by_id(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Carousel project not found")
    if project.output_dir is None:
        raise HTTPException(status_code=404, detail="Carousel not yet generated")
    image_path = Path(project.output_dir) / filename
    if not image_path.exists() or not image_path.is_file():
        raise HTTPException(status_code=404, detail="Image file not found")
    return FileResponse(
        path=str(image_path),
        media_type="image/jpeg",
        headers={"Cache-Control": "public, max-age=31536000"},
    )
```

### 12. CarouselAgent — store design tokens after Phase 4

```python
# application/services/carousel_agent.py — inside execute_pipeline
# After Phase 4 (Design System):
design_tokens = CarouselTemplateBuilder.generate_design_tokens(project)
project.design_tokens = design_tokens
await self._repository.update_project(project)
```

### 13. Integration test — design tokens endpoint

```python
# tests/integration/test_carousel_api.py
@pytest.mark.asyncio
async def test_get_carousel_design(self, client):
    """Given generated carousel, when GET /design, then returns design tokens."""
    # ... create and generate carousel ...
    response = await client.get(f"/api/carousels/{carousel_id}/design")
    assert response.status_code == 200
    data = response.json()
    assert "colors" in data
    assert "typography" in data
    assert "images" in data
    assert data["colors"]["primary"] in ["#ef4444", "#3b82f6", "#0ac5a8", "#a855f7", "#f59e0b"]

@pytest.mark.asyncio
async def test_get_carousel_image(self, client):
    """Given carousel with output, when GET /images/slide_1.jpg, then returns JPEG."""
    # ... create and generate carousel ...
    response = await client.get(f"/api/carousels/{carousel_id}/images/slide_1.jpg")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpeg"
    assert "max-age=31536000" in response.headers["cache-control"]
```

### 14. Pydantic Schema — design response

```python
# api/schemas.py
class CarouselDesignColors(BaseModel):
    primary: str
    accent: str
    bg: str
    text: str
    text_muted: str
    text_dim: str
    border: str
    glow: str

class CarouselDesignTypography(BaseModel):
    font_family_heading: str
    font_family_body: str
    font_family_badge: str

class CarouselDesignImages(BaseModel):
    hero: str
    slides: list[str]

class CarouselDesignLayout(BaseModel):
    badge_label: str
    swipe_text: str
    progress_segments: int

class CarouselDesignResponse(BaseModel):
    """Complete visual design tokens for a blog post."""
    colors: CarouselDesignColors
    typography: CarouselDesignTypography
    images: CarouselDesignImages
    layout: CarouselDesignLayout
    theme_name: str

    model_config = {"from_attributes": False}
```

### 15. Frontend — generic theme renderer (conceptual)

```typescript
// frontend/src/app/(blog)/blog/[slug]/page.tsx — future pattern
// Instead of hardcoded BLOG_THEME_COLORS map:
const response = await fetch(`/api/carousels/${id}/blog/${lang}?include_design=true`);
const { markdown, title, design } = await response.json();

// Apply design tokens as CSS custom properties:
<div
  className="dark min-h-screen"
  style={{
    "--blog-primary": design.colors.primary,
    "--blog-accent": design.colors.accent,
    "--blog-bg": design.colors.bg,
    "--blog-text": design.colors.text,
    "--blog-text-muted": design.colors.text_muted,
    "--blog-font-heading": design.typography.font_family_heading,
    "--blog-font-body": design.typography.font_family_body,
    "--blog-font-badge": design.typography.font_family_badge,
  } as React.CSSProperties}
>
  {/* All components read from CSS variables — no hardcoded themes */}
</div>
```

## Implementation Order

1. **Domain models** — Add `blog_translations`, `design_tokens`, `get_blog()`, `get_available_languages()`, `get_design()`
2. **SQLAlchemy models** — Add `blog_translations` JSON column, `design_tokens` JSON column, update `to_entity`/`update_from_entity`
3. **Protocols** — CarouselRepository, CarouselAgent interfaces (existing)
4. **Pydantic schemas** — Add `CarouselBlogI18nResponse`, `CarouselDesignResponse` + nested models
5. **Repository** — PostgresCarouselRepository (existing, no changes needed for JSON columns)
6. **External services** — GeminiImageService, PlaywrightExportService (existing)
7. **Tools** — ResearchTool, ImageGenerationTool, CarouselExportTool (existing)
8. **CarouselTemplate** — Add `generate_design_tokens()`, update `build_content_prompt()` for bilingual + design
9. **CarouselAgent** — Update Phase 3 to parse bilingual response, Phase 4 to store design tokens
10. **Routes** — Add `GET /{id}/blog/{lang}`, `GET /{id}/design`, `GET /{id}/images/{filename}`
11. **Container** — Register all providers (existing)
12. **App factory** — Mount carousels router (existing)
13. **Tests** — Unit tests for helpers, integration tests for i18n + design + image endpoints
14. **Frontend** — Replace `BLOG_THEME_COLORS` constant with API-driven design token consumer
