# Backend Blog/Content Pipeline Plan

## Overview

The carousel content pipeline is implemented as a **sub-agent** (`CarouselAgent`) that the main `RAGAgent` delegates to when users request carousel/blog generation. The sub-agent executes a 7-phase workflow based on the `carousel-pipeline` skill.

## Architecture

```
RAGAgent (main DeepAgent)
├── Tools: search_documents, get_conversation_history
└── Delegates to:
    └── CarouselAgent (sub-agent)
        ├── System Prompt: carousel-pipeline skill (7 phases)
        ├── Tools: ResearchTool, ImageGenerationTool, CarouselExportTool
        └── Output: CarouselProject + slides + images + blog post
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

## 7-Phase Pipeline

| Phase | Name | Tool/Service | Output |
|-------|------|--------------|--------|
| 1 | Research | `ResearchTool` (Playwright MCP) | `ResearchSource` records |
| 2 | Title Optimization | `LLMService` | Optimized title |
| 3 | Content Synthesis | `LLMService` | `CarouselSlide` records + blog markdown |
| 4 | Design System | Built-in Python templating | HTML + CSS |
| 5 | Image Generation | `ImageGenerationTool` (Gemini) | Image files |
| 6 | Assembly & Export | `CarouselExportTool` (Playwright) | JPG files |
| 7 | Caption Generation | `LLMService` | Instagram caption |

## New API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/carousels` | Create carousel project |
| `GET` | `/api/carousels` | List all carousels |
| `GET` | `/api/carousels/{id}` | Get project details with slides |
| `POST` | `/api/carousels/{id}/generate` | Trigger full pipeline (async) |
| `GET` | `/api/carousels/{id}/status` | Check generation status |
| `GET` | `/api/carousels/{id}/slides` | Get generated slides |
| `GET` | `/api/carousels/{id}/blog` | Get generated blog post |
| `POST` | `/api/carousels/{id}/caption` | Generate Instagram caption |
| `GET` | `/api/carousels/{id}/download` | Download carousel files (ZIP) |
| `DELETE` | `/api/carousels/{id}` | Delete project and files |

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
Phase 2: LLMService.generate(title_prompt) -> optimized_title
    ↓
Phase 3: LLMService.generate(content_prompt) -> CarouselSlide[] + blog_markdown
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

## Implementation Order

1. **Domain models** — CarouselProject, CarouselSlide, ResearchSource dataclasses
2. **SQLAlchemy models** — ORM models with to_entity/from_entity
3. **Protocols** — CarouselRepository, CarouselAgent interfaces
4. **Pydantic schemas** — Request/response models
5. **Repository** — PostgresCarouselRepository implementation
6. **External services** — GeminiImageService, PlaywrightExportService
7. **Tools** — ResearchTool, ImageGenerationTool, CarouselExportTool
8. **CarouselAgent** — 7-phase orchestration
9. **Routes** — CRUD + generate endpoints
10. **Container** — Register all providers
11. **App factory** — Mount carousels router
12. **Tests** — Unit + integration tests
