# Carousel Creator — Implementation Plan

## Overview

A new `/create` section on the site that lets users create a carousel project and then chat with the AI to generate and refine blog posts and Instagram carousels. The flow leverages the existing WebSocket chat infrastructure and RAGAgent's `generate_carousel` tool.

---

## UX Flow

```
1. /create → User fills in Topic, Audience, Niche, Theme
            → POST /api/carousels → creates project (status: "pending")
            → Redirected to /create/{id} (chat workspace)

2. /create/{id} → Chat interface connected to WS /ws/chat/{conversation_id}
            → User sends message: "Generate a carousel about this topic"
            → RAGAgent detects carousel intent → calls _generate_carousel_tool
            → CarouselAgent runs 7-phase pipeline
            → Status updates stream back via WebSocket (phase names, progress)
            → On completion: blog post + carousel rendered inline
            → User can chat further: "Make it more technical", "Change the theme"
            → AI refines and re-generates
```

---

## Backend Changes

| Area | What | Detail |
|------|-------|--------|
| **Existing** | `POST /api/carousels` | Already creates a project record — no change needed |
| **Existing** | `POST /api/carousels/{id}/generate` | Already triggers pipeline — no change needed |
| **Existing** | `WS /ws/chat/{conversation_id}` | Already streams AI responses — no change needed |
| **Existing** | `RAGAgent._generate_carousel_tool` | Already creates project + runs pipeline — no change needed |
| **New** | `GET /api/carousels/{id}/status` SSE stream | Streams phase-by-phase progress during generation (researching → drafting → designing → generating images → exporting → complete) |
| **New** | Frontend consumes carousel tool calls | When the AI invokes the carousel tool, the WS message includes the tool call result with `project_id` so the frontend can navigate to `/blog/{id}` |

---

## Frontend Changes

| Area | What |
|------|-------|
| **New page** | `/create` — topic/audience/niche form, calls `POST /api/carousels`, redirects to `/create/{id}` |
| **New page** | `/create/{id}` — chat workspace for the carousel project. Uses existing `ChatInterface` component but scoped to the carousel context. Shows pipeline progress inline. On completion, renders preview card linking to `/blog/{id}` |
| **New hook** | `useCarouselStatus(id)` — TanStack Query hook for polling project status during generation |
| **New component** | `CarouselProgress` — shows 7-phase pipeline progress with phase names and status indicators |
| **New component** | `CarouselPreview` — shows title, hero image, niche badge, link to blog post once complete |
| **Navigation** | Add "Create" link to header nav (between Blog and Knowledge) |

---

## WebSocket Message Flow

```
User → WS: { content: "Generate a carousel about Rust vs Go" }
AI   → WS: { type: "assistant", content: "I'll create a carousel about..." }
AI   → WS: { type: "tool_call", tool: "generate_carousel", args: { project_id, topic, ... } }
AI   → WS: { type: "tool_result", tool: "generate_carousel", result: { project_id, status: "completed" } }
AI   → WS: { type: "assistant", content: "Your carousel is ready! [View Blog Post](/blog/{id})" }
```

The frontend intercepts `tool_result` messages for `generate_carousel` and:
1. Shows the `CarouselProgress` component during generation
2. Shows the `CarouselPreview` component once status is `completed`
3. Offers a "View Blog Post" button linking to `/blog/{id}`

---

## Key Design Decisions

- **Two distinct steps**: Create project (form) → Chat with AI (workspace). The chat is *about* the project.
- **WebSocket-first**: Leverages existing `/ws/chat` infrastructure, not REST polling. The AI streams back status as it works.
- **Refinement loop**: User can continue chatting after generation — "make it shorter", "change the theme to cybersecurity" — and the AI can re-run phases.
- **No `GEMINI_API_KEY`**: Pipeline already supports `generate_images=false`. Images come from the AI's image prompts, not Gemini. We respect the current behavior.

---

## File Structure (Planned)

```
frontend/src/
├── app/
│   └── (create)/
│       └── create/
│           ├── page.tsx                          # Topic form + project creation
│           └── [id]/
│               └── page.tsx                      # Chat workspace for carousel project
├── features/
│   └── create/
│       ├── components/
│       │   ├── topic-form.tsx                   # Topic/audience/niche/theme form
│       │   ├── carousel-progress.tsx             # 7-phase pipeline progress indicator
│       │   └── carousel-preview.tsx              # Preview card with hero + blog link
│       └── hooks/
│           └── use-carousel-status.ts             # Poll project status during generation
├── constants/
│   └── create.ts                                # Carousel creation constants
└── schemas/
    └── carousel.ts                               # Existing — may need CarouselCreateRequest
```

---

## Pipeline Phases (for progress display)

| # | Phase | Status String | Description |
|---|-------|---------------|-------------|
| 1 | Research | `researching` | Web search + scrape URLs for topic context |
| 2 | Title Optimization | `drafting` | LLM generates optimized title/subtitle (bilingual) |
| 3 | Content Synthesis | `drafting` | LLM generates slide-by-slide content + blog markdown |
| 4 | Design System | `designing` | Applies theme colors, generates design tokens |
| 5 | Image Generation | `generating_images` | Generates comic/manga-style images per slide (skipped if no Gemini key) |
| 6 | Assembly & Export | `exporting` | Playwright renders HTML to individual slide JPGs |
| 7 | Caption | `exporting` | LLM generates Instagram caption with hashtags |

---

## Out of Scope (for now)

- Editing individual slides in the UI
- Custom image uploads
- Exporting carousel HTML/PDF
- Choosing language at creation time (default: both pt + en)