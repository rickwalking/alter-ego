# Alter-Ego Professional Content Platform — Comprehensive Pivot Plan

**Date:** 2026-05-23
**Status:** Phase 5 Complete → Launched
**Goal:** Transform Alter-Ego from an autonomous AI content factory into a professional, human-in-the-loop content platform that captures Pedro's authentic voice and expertise.

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Current State Analysis](#2-current-state-analysis)
3. [Desired State Vision](#3-desired-state-vision)
4. [Architecture Solution](#4-architecture-solution)
5. [Domain Model Extensions](#5-domain-model-extensions)
6. [API Contract Changes](#6-api-contract-changes)
7. [Workflow Engine Design](#7-workflow-engine-design)
8. [AI Orchestration Architecture](#8-ai-orchestration-architecture)
9. [Risks & Mitigations](#9-risks--mitigations)
10. [Code Snippets](#10-code-snippets)
11. [Gherkin Scenarios](#11-gherkin-scenarios)
12. [Implementation Task List](#12-implementation-task-list)
13. [Appendix: Research Citations](#13-appendix-research-citations)

---

## 1. Executive Summary

### The Problem

Alter-Ego currently operates as a **fully autonomous AI content factory** with these critical limitations:

| Dimension | Current State | Professional Standard |
|-----------|--------------|----------------------|
| **Briefing Depth** | 5 fields (topic, audience, niche, theme, style) | Multi-page creative briefs with personas, rubrics, sources, instructions |
| **Human Control** | Zero — set inputs, wait for output | Continuous editorial control at every stage |
| **Source Quality** | Web search only | Curated primary sources, expert interviews, proprietary data |
| **Voice Authenticity** | Generic AI tone | "How Pedro would write this" — personal anecdotes, opinions, expertise |
| **Content Review** | None — auto-publish | Draft → Review → Approved workflow with stakeholder sign-off |
| **Originality** | Repurposed search results | Original analysis, first-hand experience, unique perspectives |
| **Asset Management** | Auto-generated images only | Human-curated images, AI-assisted generation, editing, replacement |
| **Blog Posts** | Auto-generated from carousel | Independent editorial pieces with AI assistance, not duplication |

### The Vision

Transform Alter-Ego into a **professional content creation platform** where:

- **Pedro is the driver**, not a passenger. The AI amplifies his expertise, it doesn't replace it.
- Every carousel and blog post flows through an **editorial workflow** with human checkpoints.
- The platform captures and enforces Pedro's **writing persona** through style guides, examples, and feedback loops.
- **Sources are curated** — not just search results, but Pedro's own materials, expert contacts, and verified references.
- **Quality is measurable** through explicit rubrics (E-E-A-T, originality, voice consistency).
- **Blog posts are independent editorial content**, not derivative of carousels.

### Research Foundation

This plan synthesizes findings from four parallel research streams:

1. **Instagram Carousel Best Practices** (Hootsuite, Buffer, Later, Sprout Social, SocialInsider)
2. **Blog Editorial Workflows** (WordPress, Ghost, Medium, Substack, Grammarly Business, Jasper)
3. **AI-Human Collaboration** (Google E-E-A-T, OpenAI RLHF, Anthropic Constitutional AI, SEMrush)
4. **Technical Architecture** (Martin Fowler distributed patterns, Confluent Kafka, Redis, Supabase)

---

## 2. Current State Analysis

### 2.1 Carousel Creation Flow (Current)

```
User Input (5 fields)
    ↓
[Auto] Research Agent (web search)
    ↓
[Auto] Content Agent (drafts slides)
    ↓
[Auto] Design Agent (applies visual theme)
    ↓
[Auto] Image Agent (generates images)
    ↓
[Auto] Export Agent (PDF + images)
    ↓
Carousel Ready
```

**Problems:**
- No human review between stages
- No way to provide detailed creative direction
- No source curation — relies entirely on search quality
- No voice enforcement — generic AI output
- No quality gates — outputs vary widely
- No iteration loop — can't refine mid-process

### 2.2 Blog Post Flow (Current)

```
Carousel Generated
    ↓
[Auto] Blog Agent (repurposes carousel content)
    ↓
Blog Post Published
```

**Problems:**
- Blog posts are derivative, not original
- No draft status — immediately published
- No editing capability
- No image management
- No source references
- Same generic AI voice

### 2.3 Technical Debt

| Issue | Impact | Tracking |
|-------|--------|----------|
| Monolithic generation pipeline | Can't pause/resume at stages | Phase 3 (WF-*) |
| No workflow state persistence | Lost progress on errors | TD-006 |
| No versioning | Can't compare iterations | Phase 1 UI-008 |
| No collaboration primitives | Single-user only | Phase 3 (UI-021) |
| Fixed prompt templates | Can't adapt to content type | Partially addressed Phase 2 |
| No feedback loops | System doesn't learn from corrections | TD-005 (in-memory stub exists) |
| Phase 2 QA remainder | Test depth, auth consistency, mutation score | [TECHNICAL_DEBT.md](TECHNICAL_DEBT.md) |

---

## 3. Desired State Vision

### 3.1 Carousel Creation — Enhanced Workflow

```
Phase 1: BRIEF
├─ Project metadata (topic, audience, niche, theme, style)
├─ Creative brief (detailed instructions, goals, tone notes)
├─ Source materials (uploaded docs, URLs, notes, interviews)
├─ Persona selection (Pedro's voice profile)
├─ Quality rubric (E-E-A-T criteria, originality targets)
├─ Reference carousels (examples of "good" work)
└─ [Human] Review & Confirm Brief

Phase 2: RESEARCH
├─ AI research (web search, as before)
├─ Source synthesis (extract key points from uploaded materials)
├─ Gap analysis (what's missing? what needs human input?)
└─ [Human] Review Research, Add Notes, Request More Sources

Phase 3: OUTLINE
├─ AI generates slide-by-slide outline
├─ Each slide: title, key points, visual direction, sources
├─ [Human] Edit outline, reorder slides, add/remove content
└─ [Human] Approve Outline

Phase 4: CONTENT
├─ AI drafts slide copy (with persona enforcement)
├─ Each slide shows: draft text, sources used, confidence score
├─ [Human] Edit each slide, rewrite sections, add personal anecdotes
├─ AI suggestions: "Make this more Pedro" / "Add data here" / "Source needed"
└─ [Human] Approve Content

Phase 5: DESIGN
├─ AI applies visual theme
├─ [Human] Review design, request changes
├─ AI regenerates specific slides on request
└─ [Human] Approve Design

Phase 6: IMAGES
├─ AI generates images
├─ [Human] Review, replace, upload custom images
├─ AI generates alt text
└─ [Human] Approve Images

Phase 7: FINAL REVIEW
├─ Full carousel preview
├─ Quality check against rubric
├─ Accessibility check
└─ [Human] Publish or Save as Draft
```

### 3.2 Blog Post — Independent Editorial Workflow

```
State: DRAFT
├─ Create from template or scratch
├─ AI-assisted writing with persona enforcement
├─ Rich text editor with markdown support
├─ Image upload, AI image generation, image editing
├─ Source management (add references, citations)
├─ Inline AI suggestions: "Improve this paragraph" / "Make it shorter" / "Add Pedro's opinion"
├─ Version history with diff view
├─ [Human] Edit, iterate, improve

State: UNDER REVIEW
├─ Submit for review
├─ Quality rubric evaluation (AI + human)
├─ Reviewer comments and suggestions
├─ [Human] Address feedback, revise

State: APPROVED
├─ Final approval
├─ SEO optimization check
├─ Social sharing preview
├─ Schedule or publish immediately

State: PUBLISHED
├─ Live on blog
├─ Analytics tracking
├─ Engagement monitoring
├─ [Human] Can unpublish, edit, or create new version
```

### 3.3 Key Differentiators

| Feature | Why It Matters |
|---------|---------------|
| **Persona Engine** | Captures Pedro's unique voice, opinions, expertise, and writing style |
| **Source Curation** | Humans provide high-quality inputs; AI synthesizes rather than searches blindly |
| **Quality Rubrics** | Explicit, measurable criteria for every piece of content |
| **Stage Gates** | Human approval at each phase prevents low-quality output from propagating |
| **Feedback Loops** | Corrections and preferences train the system over time |
| **Originality Scoring** | Ensures content isn't just rehashed search results |
| **Blog Independence** | Blog posts are original editorial content, not derivative marketing |

---

## 4. Architecture Solution

### 4.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        CLIENT LAYER                          │
│  Next.js 16 + React 19 + TanStack Query + Tailwind CSS v4  │
│  ├─ Rich Text Editor (TipTap / Plate)                       │
│  ├─ Image Editor (Fabric.js / react-image-crop)            │
│  ├─ Carousel Preview (interactive slide viewer)              │
│  ├─ Workflow UI (Kanban-style stage boards)                 │
│  └─ Real-time Collaboration (Yjs / Liveblocks)              │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                      API GATEWAY LAYER                       │
│  FastAPI + Zod Validation + JWT Auth                         │
│  ├─ REST API (CRUD operations)                              │
│  ├─ SSE Streaming (real-time updates)                       │
│  └─ WebSocket (collaborative editing)                        │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                   WORKFLOW ENGINE LAYER                      │
│  LangGraph + State Machines                                  │
│  ├─ CarouselWorkflow (7 phases, human gates)                │
│  ├─ BlogPostWorkflow (4 states, approval gates)               │
│  ├─ EditorialTaskWorkflow (review assignments)             │
│  └─ AssetWorkflow (image generation, upload, editing)       │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                     AI ORCHESTRATION                        │
│  LangGraph Deep Agents + LangChain                          │
│  ├─ PersonaAgent (voice enforcement, style matching)         │
│  ├─ ResearchAgent (synthesis, not just search)              │
│  ├─ ContentAgent (drafting with constraints)                │
│  ├─ QualityAgent (rubric evaluation, scoring)                │
│  ├─ ImageAgent (generation, editing, alt text)              │
│  └─ FeedbackAgent (learning from corrections)                │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                      DATA LAYER                               │
│  PostgreSQL (primary) + Redis (cache/queues) + Pinecone (RAG)│
│  ├─ Content Store (JSONB documents with versioning)         │
│  ├─ Workflow State (event-sourced audit log)                  │
│  ├─ Asset Store (S3-compatible + CDN)                         │
│  ├─ Persona Store (voice profiles, examples, feedback)       │
│  └─ Source Store (curated materials, references, citations)  │
└─────────────────────────────────────────────────────────────┘
```

### 4.2 Event-Driven Workflow Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     EVENT BACKBONE                          │
│              (Apache Kafka / Redis Streams)                 │
├─────────────────────────────────────────────────────────────┤
│  Topics:                                                     │
│  ├─ content.project.created                                │
│  ├─ content.project.brief.submitted                        │
│  ├─ content.project.research.completed                      │
│  ├─ content.project.outline.approved                       │
│  ├─ content.project.content.draft_generated                │
│  ├─ content.project.content.human_edited                   │
│  ├─ content.project.content.approved                       │
│  ├─ content.project.design.applied                          │
│  ├─ content.project.images.generated                       │
│  ├─ content.project.images.human_replaced                  │
│  ├─ content.project.quality.scored                         │
│  ├─ content.project.published                               │
│  ├─ content.blogpost.created                               │
│  ├─ content.blogpost.draft.saved                           │
│  ├─ content.blogpost.submitted_for_review                │
│  ├─ content.blogpost.review.completed                     │
│  ├─ content.blogpost.approved                              │
│  ├─ content.blogpost.published                             │
│  ├─ content.asset.uploaded                                  │
│  ├─ content.asset.generated                                 │
│  ├─ content.asset.edited                                    │
│  ├─ content.persona.updated                                │
│  ├─ content.source.added                                    │
│  └─ content.quality.rubric_evaluated                        │
└─────────────────────────────────────────────────────────────┘
```

### 4.3 State Machine for Carousel Workflow

```
[CREATED]
    ↓ brief_submitted
[RESEARCHING]
    ↓ research_completed OR research_human_review_requested
[RESEARCH_REVIEW] ←→ [RESEARCHING]
    ↓ outline_generated
[OUTLINING]
    ↓ outline_approved
[CONTENT_DRAFTING]
    ↓ content_draft_generated
[CONTENT_REVIEW] ←→ [CONTENT_DRAFTING]
    ↓ content_approved
[DESIGNING]
    ↓ design_applied
[DESIGN_REVIEW] ←→ [DESIGNING]
    ↓ design_approved
[IMAGE_GENERATING]
    ↓ images_generated
[IMAGE_REVIEW] ←→ [IMAGE_GENERATING]
    ↓ images_approved
[FINAL_REVIEW]
    ↓ published OR saved_as_draft
[PUBLISHED] ←→ [FINAL_REVIEW]
[DRAFT] → [FINAL_REVIEW]
```

### 4.4 State Machine for Blog Post Workflow

```
[CREATED]
    ↓ auto_save
[DRAFT]
    ↓ submit_for_review
[UNDER_REVIEW]
    ↓ review_completed (approved OR needs_revision)
[NEEDS_REVISION] ←→ [DRAFT]
    ↓ revision_submitted
[UNDER_REVIEW]
    ↓ approved
[APPROVED]
    ↓ publish OR schedule
[PUBLISHED]
    ↓ unpublish
[DRAFT]
    ↓ archive
[ARCHIVED]
```

---

## 5. Domain Model Extensions

### 5.1 New Entities

```python
# Persona Profile
class PersonaProfile:
    id: str
    name: str  # "Pedro's Professional Voice"
    description: str
    tone_attributes: dict[str, float]  # {"formal": 0.3, "conversational": 0.8, "humorous": 0.4}
    writing_samples: list[str]  # URLs or text excerpts
    forbidden_phrases: list[str]  # "In today's world", "Let's dive in"
    preferred_phrases: list[str]  # "Here's the thing", "What most people miss"
    sentence_structure_preferences: str  # "Short punchy sentences. Occasional longer ones for rhythm."
    paragraph_style: str  # "1-3 sentences per paragraph. White space is key."
    opinion_expression: str  # "Strong opinions, loosely held. Never neutral."
    expertise_areas: list[str]  # ["cybersecurity", "entrepreneurship", "AI"]
    created_at: datetime
    updated_at: datetime
    version: int

# Quality Rubric
class QualityRubric:
    id: str
    name: str  # "Instagram Carousel Quality"
    description: str
    criteria: list[RubricCriterion]
    applicable_content_types: list[str]  # ["carousel", "blog_post"]
    is_default: bool

class RubricCriterion:
    id: str
    name: str  # "E-E-A-T Score"
    description: str
    weight: float  # 0.0 to 1.0
    evaluation_method: str  # "ai_auto" | "human_required" | "hybrid"
    min_threshold: float  # minimum score to pass
    scoring_scale: str  # "1-10" | "pass_fail" | "grade_a_f"
    prompt_template: str  # LLM prompt for evaluation

# Content Source
class ContentSource:
    id: str
    project_id: str
    source_type: str  # "url" | "document" | "note" | "interview" | "data"
    title: str
    content: str  # text content or URL
    metadata: dict  # author, date, credibility_score
    tags: list[str]
    extracted_key_points: list[str]  # AI-extracted highlights
    is_primary: bool  # primary source vs. reference
    created_by: str  # user_id
    created_at: datetime

# Editorial Comment
class EditorialComment:
    id: str
    content_id: str  # project or blog post id
    content_type: str  # "carousel_slide" | "blog_post_section"
    author_id: str
    text: str
    position: dict  # {"slide_index": 3} or {"paragraph_index": 5, "offset": 120}
    status: str  # "open" | "resolved" | "dismissed"
    ai_suggestion: str | None  # optional AI-generated fix
    created_at: datetime
    resolved_at: datetime | None

# Content Version
class ContentVersion:
    id: str
    content_id: str
    content_type: str  # "carousel" | "blog_post"
    version_number: int
    snapshot: dict  # full JSON snapshot of content state
    change_summary: str  # "Edited slide 3: added statistic"
    author_id: str
    created_at: datetime
```

### 5.2 Extended Project Model

```python
class Project:
    id: str
    title: str
    description: str
    target_audience: str
    niche: str
    visual_theme: str
    image_style: str

    # NEW FIELDS
    creative_brief: str  # Detailed instructions and goals
    persona_id: str  # Reference to PersonaProfile
    rubric_id: str  # Reference to QualityRubric
    sources: list[str]  # Reference to ContentSource IDs
    reference_carousels: list[str]  # URLs or IDs of "good" examples
    instructions: str  # "Make this controversial" / "Focus on data" / "Tell a story"
    quality_target: dict  # {"originality": 0.8, "engagement": 0.9}

    # WORKFLOW STATE
    current_phase: str  # Phase name
    phase_status: str  # "in_progress" | "awaiting_human" | "approved" | "rejected"
    phase_started_at: datetime
    phase_deadline: datetime | None

    # METADATA
    created_by: str
    created_at: datetime
    updated_at: datetime
    published_at: datetime | None
```

### 5.3 New Blog Post Model

```python
class BlogPost:
    id: str
    project_id: str | None  # Optional link to carousel
    title: str
    slug: str
    status: str  # "draft" | "under_review" | "approved" | "published" | "archived"

    # CONTENT
    content: dict  # Rich text JSON (TipTap/ProseMirror format)
    excerpt: str
    featured_image: str | None

    # EDITORIAL
    author_id: str
    reviewer_id: str | None
    editor_comments: list[str]  # EditorialComment IDs
    version_history: list[str]  # ContentVersion IDs

    # SOURCES
    sources: list[str]  # ContentSource IDs
    citations: list[dict]  # [{"text": "According to...", "source_id": "..."}]

    # AI ASSISTANCE
    ai_suggestions: list[dict]  # [{"type": "improve", "text": "...", "applied": false}]
    ai_generation_metadata: dict  # prompt used, model, temperature

    # SEO
    meta_title: str
    meta_description: str
    keywords: list[str]
    canonical_url: str | None

    # ENGAGEMENT
    view_count: int
    like_count: int
    comment_count: int
    share_count: int

    # TIMESTAMPS
    created_at: datetime
    updated_at: datetime
    submitted_for_review_at: datetime | None
    approved_at: datetime | None
    published_at: datetime | None
    scheduled_publish_at: datetime | None
```

---

## 6. API Contract Changes

### 6.1 New Endpoints

```yaml
# Persona Management
POST   /api/personas                    # Create persona
GET    /api/personas                    # List personas
GET    /api/personas/{id}              # Get persona
PUT    /api/personas/{id}              # Update persona
DELETE /api/personas/{id}              # Delete persona
POST   /api/personas/{id}/feedback      # Add writing feedback to train persona

# Quality Rubrics
POST   /api/rubrics                     # Create rubric
GET    /api/rubrics                     # List rubrics
GET    /api/rubrics/{id}               # Get rubric
PUT    /api/rubrics/{id}               # Update rubric
POST   /api/rubrics/{id}/evaluate      # Evaluate content against rubric

# Content Sources
POST   /api/projects/{id}/sources       # Add source
GET    /api/projects/{id}/sources       # List sources
PUT    /api/projects/{id}/sources/{sid} # Update source
DELETE /api/projects/{id}/sources/{sid} # Delete source
POST   /api/sources/{id}/extract        # AI-extract key points

# Project Workflow Actions
POST   /api/projects/{id}/submit-brief          # Submit brief, start research
POST   /api/projects/{id}/approve-phase        # Approve current phase
POST   /api/projects/{id}/reject-phase         # Reject, request changes
POST   /api/projects/{id}/request-revision    # Request specific revision
POST   /api/projects/{id}/skip-to-phase        # Skip to specific phase (admin)
POST   /api/projects/{id}/publish              # Publish carousel
POST   /api/projects/{id}/save-draft          # Save as draft

# Blog Posts
POST   /api/blog-posts                   # Create blog post
GET    /api/blog-posts                   # List blog posts (with filters)
GET    /api/blog-posts/{id}              # Get blog post
PUT    /api/blog-posts/{id}              # Update blog post
DELETE /api/blog-posts/{id}              # Delete blog post
POST   /api/blog-posts/{id}/submit-review    # Submit for review
POST   /api/blog-posts/{id}/approve          # Approve
POST   /api/blog-posts/{id}/reject           # Reject with feedback
POST   /api/blog-posts/{id}/publish          # Publish
POST   /api/blog-posts/{id}/unpublish        # Unpublish
POST   /api/blog-posts/{id}/archive          # Archive
POST   /api/blog-posts/{id}/ai-suggest       # Get AI suggestions
POST   /api/blog-posts/{id}/ai-improve       # AI improvement on selection
POST   /api/blog-posts/{id}/generate-image   # Generate image for post
POST   /api/blog-posts/{id}/add-source      # Add reference source
GET    /api/blog-posts/{id}/versions         # Get version history
POST   /api/blog-posts/{id}/restore-version # Restore to version

# Editorial Comments
POST   /api/comments                     # Add comment
GET    /api/comments/{content_id}       # Get comments for content
PUT    /api/comments/{id}              # Update comment
DELETE /api/comments/{id}              # Delete comment
POST   /api/comments/{id}/resolve       # Resolve comment
POST   /api/comments/{id}/ai-fix        # Apply AI-suggested fix

# Assets
POST   /api/assets/upload               # Upload image
POST   /api/assets/generate             # Generate image with AI
POST   /api/assets/{id}/edit            # Edit image (crop, resize, filter)
POST   /api/assets/{id}/alt-text        # Generate alt text
GET    /api/assets/{id}                 # Get asset
DELETE /api/assets/{id}                 # Delete asset
```

### 6.2 SSE Events

```yaml
# Workflow Phase Updates
project.phase.changed:
  project_id: string
  old_phase: string
  new_phase: string
  status: "in_progress" | "awaiting_human" | "approved" | "rejected"
  message: string
  timestamp: datetime

# Human Review Requested
project.review.requested:
  project_id: string
  phase: string
  reviewer_id: string
  deadline: datetime | null
  review_url: string

# Content Draft Ready
project.content.draft:
  project_id: string
  slide_index: int
  draft_text: string
  sources_used: list[string]
  confidence_score: float

# AI Suggestion
content.ai.suggestion:
  content_id: string
  content_type: "carousel" | "blog_post"
  suggestion_type: "improve" | "shorten" | "expand" | "add_source" | "add_opinion"
  original_text: string
  suggested_text: string
  explanation: string

# Blog Post Status Changes
blogpost.status.changed:
  post_id: string
  old_status: string
  new_status: string
  changed_by: string
  timestamp: datetime

# Editorial Comment
content.comment.added:
  comment_id: string
  content_id: string
  author_id: string
  text: string
  position: dict
```

---

## 7. Workflow Engine Design

### 7.1 LangGraph Workflow State

```python
from typing import TypedDict, Annotated
from langgraph.graph import StateGraph
import operator

class CarouselWorkflowState(TypedDict):
    project_id: str
    current_phase: str
    phase_history: list[dict]

    # Brief Phase
    brief: dict  # creative_brief, persona_id, rubric_id, sources, instructions
    brief_approved: bool

    # Research Phase
    research_findings: list[dict]
    synthesized_sources: list[dict]
    research_notes: str
    research_approved: bool

    # Outline Phase
    outline: list[dict]  # [{slide_index, title, key_points, visual_direction}]
    outline_approved: bool

    # Content Phase
    slide_drafts: Annotated[list[dict], operator.add]
    content_approved: bool

    # Design Phase
    design_applied: bool
    design_feedback: str
    design_approved: bool

    # Images Phase
    images_generated: bool
    image_assets: list[str]
    image_feedback: str
    images_approved: bool

    # Quality
    rubric_scores: dict
    quality_passed: bool

    # Final
    status: str  # "draft" | "published" | "archived"

class BlogPostWorkflowState(TypedDict):
    post_id: str
    status: str

    # Content
    title: str
    content: dict  # rich text JSON
    excerpt: str
    featured_image: str | None

    # Editorial
    editor_comments: list[dict]
    reviewer_id: str | None
    review_feedback: str

    # AI
    ai_suggestions: list[dict]
    ai_metadata: dict

    # Sources
    sources: list[str]
    citations: list[dict]

    # Versions
    current_version: int
    version_history: list[dict]

    # Quality
    rubric_scores: dict
    quality_passed: bool
```

### 7.2 Human-in-the-Loop Interrupts

```python
from langgraph.types import interrupt

async def research_phase(state: CarouselWorkflowState):
    """Conduct research, then INTERRUPT for human review."""
    # AI does the work
    findings = await research_agent.conduct_research(
        brief=state["brief"],
        sources=state["brief"]["sources"],
    )

    # INTERRUPT — wait for human
    human_review = interrupt({
        "type": "research_review",
        "findings": findings,
        "message": "Please review research findings and add notes.",
    })

    # Human provides feedback
    if human_review["action"] == "approve":
        return {"research_approved": True, "research_notes": human_review["notes"]}
    elif human_review["action"] == "reject":
        return {"research_approved": False, "research_notes": human_review["feedback"]}
    elif human_review["action"] == "add_sources":
        # Loop back with more sources
        return {"research_approved": False, "additional_sources": human_review["sources"]}
```

### 7.3 Workflow Persistence

```python
from langgraph.checkpoint.postgres import PostgresSaver

# Save workflow state after every step
workflow = StateGraph(CarouselWorkflowState)
# ... add nodes and edges ...

# Compile with persistence
app = workflow.compile(checkpointer=PostgresSaver(conn=db_pool))

# Resume from any checkpoint
config = {"configurable": {"thread_id": project_id}}
state = app.get_state(config)

# Human can resume from interrupt
result = app.invoke(None, config)  # Continues from interrupt
```

---

## 8. AI Orchestration Architecture

### 8.1 Persona Engine

```python
class PersonaAgent:
    """Enforces Pedro's writing voice on all AI-generated content."""

    def __init__(self, persona: PersonaProfile):
        self.persona = persona
        self.style_guide = self._build_style_guide()

    def _build_style_guide(self) -> str:
        return f"""
        You are writing as {self.persona.name}.

        TONE: {self.persona.tone_attributes}
        SENTENCE STRUCTURE: {self.persona.sentence_structure_preferences}
        PARAGRAPH STYLE: {self.persona.paragraph_style}
        OPINION EXPRESSION: {self.persona.opinion_expression}

        FORBIDDEN PHRASES: {', '.join(self.persona.forbidden_phrases)}
        PREFERRED PHRASES: {', '.join(self.persona.preferred_phrases)}

        EXPERTISE AREAS: {', '.join(self.persona.expertise_areas)}

        WRITING SAMPLES:
        {chr(10).join(f'- {sample}' for sample in self.persona.writing_samples[:3])}

        INSTRUCTION: Rewrite the following content to match this voice perfectly.
        It should sound authentically human, with strong opinions, personal anecdotes where relevant,
        and zero generic AI-speak. Never use dashes as bullet points unless explicitly asked.
        """

    async def enforce(self, content: str, context: str = "") -> str:
        """Rewrite content to match persona."""
        prompt = f"{self.style_guide}\n\nCONTEXT: {context}\n\nCONTENT TO REWRITE:\n{content}"
        return await llm.complete(prompt)

    async def evaluate_match(self, content: str) -> dict:
        """Score how well content matches persona (0-100)."""
        prompt = f"""
        Score this content on how well it matches the following persona.

        PERSONA: {self.persona.description}

        CONTENT: {content}

        Provide scores (0-100) for:
        - tone_match
        - sentence_structure_match
        - opinion_strength
        - originality
        - human_authenticity
        - overall

        Also provide specific improvement suggestions.
        """
        return await llm.structured_complete(prompt, schema=PersonaScoreSchema)
```

### 8.2 Quality Evaluation Agent

```python
class QualityAgent:
    """Evaluates content against rubrics and provides actionable feedback."""

    def __init__(self, rubric: QualityRubric):
        self.rubric = rubric

    async def evaluate(self, content: str, sources: list[str]) -> dict:
        scores = {}
        feedback = []

        for criterion in self.rubric.criteria:
            if criterion.evaluation_method == "ai_auto":
                score = await self._ai_evaluate(criterion, content, sources)
            elif criterion.evaluation_method == "human_required":
                score = await self._request_human_evaluation(criterion, content)
            else:  # hybrid
                ai_score = await self._ai_evaluate(criterion, content, sources)
                human_score = await self._request_human_evaluation(criterion, content)
                score = (ai_score * 0.4) + (human_score * 0.6)

            scores[criterion.id] = {
                "score": score,
                "weight": criterion.weight,
                "passed": score >= criterion.min_threshold,
            }

            if score < criterion.min_threshold:
                feedback.append({
                    "criterion": criterion.name,
                    "score": score,
                    "threshold": criterion.min_threshold,
                    "suggestion": await self._generate_improvement(criterion, content),
                })

        overall_score = sum(
            s["score"] * s["weight"] for s in scores.values()
        ) / sum(s["weight"] for s in scores.values())

        return {
            "overall_score": overall_score,
            "criteria_scores": scores,
            "feedback": feedback,
            "passed": all(s["passed"] for s in scores.values()),
        }

    async def _ai_evaluate(self, criterion: RubricCriterion, content: str, sources: list[str]) -> float:
        prompt = criterion.prompt_template.format(
            content=content,
            sources=sources,
        )
        result = await llm.structured_complete(prompt, schema=ScoreSchema)
        return result.score
```

### 8.3 Feedback Learning Loop

```python
class FeedbackLearningLoop:
    """Learns from human corrections to improve AI outputs over time."""

    async def record_correction(self, original: str, corrected: str, context: str, persona_id: str):
        """Store a human correction for future learning."""
        await db.corrections.insert({
            "original": original,
            "corrected": corrected,
            "context": context,
            "persona_id": persona_id,
            "correction_type": self._classify_correction(original, corrected),
            "created_at": datetime.now(),
        })

        # Update persona with new examples
        await self._update_persona_examples(persona_id, corrected)

    async def _update_persona_examples(self, persona_id: str, example: str):
        """Add corrected example to persona's writing samples."""
        persona = await db.personas.get(persona_id)
        persona.writing_samples.append(example)

        # Keep only the best N examples (most recent + highest quality)
        if len(persona.writing_samples) > 50:
            # Score each and keep top 50
            scored = []
            for sample in persona.writing_samples:
                quality = await quality_agent.evaluate_match(sample)
                scored.append((sample, quality["overall"]))
            scored.sort(key=lambda x: x[1], reverse=True)
            persona.writing_samples = [s[0] for s in scored[:50]]

        await db.personas.update(persona_id, persona)

    async def get_relevant_examples(self, prompt: str, persona_id: str, k: int = 3) -> list[str]:
        """Retrieve similar past corrections to improve new outputs."""
        corrections = await db.corrections.find({"persona_id": persona_id})

        # Embed all corrections and find similar ones
        prompt_embedding = await embeddings.embed(prompt)
        correction_embeddings = [
            (c, await embeddings.embed(c["original"])) for c in corrections
        ]

        # Find k-nearest neighbors
        similarities = [
            (c, cosine_similarity(prompt_embedding, emb))
            for c, emb in correction_embeddings
        ]
        similarities.sort(key=lambda x: x[1], reverse=True)

        return [
            f"Original: {c['original']}\nCorrected: {c['corrected']}"
            for c, _ in similarities[:k]
        ]
```

---

## 8.5 Observability & Tracing Architecture

### 8.5.1 Core Principle: Full Visibility

Every AI operation must be visible. No agent, subagent, or LLM call is a blind spot. The entire creation tree — from initial brief to published content — must be traceable in Langfuse.

### 8.5.2 Trace Tree Structure

#### Carousel Creation Trace Tree

```
Trace: carousel_workflow_abc123
├── Metadata: {project_id, user_id, content_type, persona_id}
├── Tags: ["carousel", "workflow"]
│
├── Span: phase_brief (2s)
│   └── Event: brief_submitted
│
├── Span: phase_research (45s)
│   ├── Span: subagent_researcher_topic_1 (12s, 3.2k tokens)
│   │   ├── Generation: web_search_call
│   │   ├── Generation: synthesis_call
│   │   └── Metadata: {sources_found: 5, topic: "breaches"}
│   ├── Span: subagent_researcher_topic_2 (11s, 2.8k tokens)
│   │   └── ...
│   └── Span: subagent_researcher_topic_3 (13s, 3.1k tokens)
│       └── ...
│
├── Span: phase_outline (8s)
│   └── Generation: outline_generation (8s, 1.5k tokens)
│
├── Span: phase_content (120s)
│   ├── Span: subagent_content_slide_1 (15s, 2.1k tokens)
│   ├── Span: subagent_content_slide_2 (14s, 2.0k tokens)
│   ├── Span: subagent_content_slide_3 (16s, 2.3k tokens)
│   ├── Span: subagent_content_slide_4 (15s, 2.2k tokens)
│   ├── Span: subagent_content_slide_5 (14s, 2.1k tokens)
│   ├── Span: subagent_content_slide_6 (15s, 2.2k tokens)
│   └── Span: subagent_content_slide_7 (14s, 2.0k tokens)
│
├── Span: phase_design (5s)
│   └── No LLM calls (deterministic CSS/template application)
│
├── Span: phase_images (180s)
│   ├── Span: image_generation_slide_1 (DALL-E, 18s)
│   ├── Span: image_generation_slide_2 (DALL-E, 19s)
│   ├── Span: image_generation_slide_3 (DALL-E, 17s)
│   ├── Span: image_generation_slide_4 (DALL-E, 18s)
│   ├── Span: image_generation_slide_5 (DALL-E, 19s)
│   ├── Span: image_generation_slide_6 (DALL-E, 18s)
│   └── Span: image_generation_slide_7 (DALL-E, 18s)
│
├── Span: quality_check (12s)
│   ├── Generation: rubric_evaluation (8s, 3.0k tokens)
│   ├── Score: eeat_score = 85
│   ├── Score: originality_score = 78
│   ├── Score: voice_match_score = 92
│   └── Score: overall_quality = 84
│
├── Span: human_review_brief (2h 15m) ──interrupt()──
│   ├── Event: review_requested
│   ├── Event: review_completed {action: "approve", reviewer: "pedro"}
│   └── Metadata: {time_to_respond: "2h15m", feedback: ""}
│
├── Span: human_review_content (45m) ──interrupt()──
│   ├── Event: review_requested
│   ├── Event: review_completed {action: "edit", reviewer: "pedro"}
│   └── Metadata: {edits_made: 3, slides_edited: [1, 3, 5]}
│
├── Span: human_review_final (12m) ──interrupt()──
│   ├── Event: review_requested
│   ├── Event: review_completed {action: "publish", reviewer: "pedro"}
│   └── Metadata: {time_to_respond: "12m"}
│
└── Event: workflow_completed {status: "published", total_duration: "4h 32m"}
```

#### Blog Post Creation Trace Tree (Independent)

```
Trace: blogpost_workflow_def456
├── Metadata: {post_id, user_id, content_type: "blog_post", persona_id}
├── Tags: ["blog_post", "workflow"]
│
├── Span: creation (3s)
│   └── Event: post_created {title: "The Real Cost of AI Security Breaches"}
│
├── Span: ai_suggestion_1 (8s)
│   ├── Generation: suggestion_generation (8s, 1.2k tokens)
│   ├── Metadata: {suggestion_type: "improve", paragraph: 2}
│   └── Event: suggestion_shown_to_user
│
├── Span: ai_suggestion_2 (7s)
│   ├── Generation: suggestion_generation (7s, 1.1k tokens)
│   ├── Metadata: {suggestion_type: "add_opinion", paragraph: 3}
│   └── Event: suggestion_applied_by_user
│
├── Span: image_generation (15s)
│   ├── Generation: DALL-E call (15s)
│   └── Metadata: {prompt: "Abstract visualization of AI security...", size: "1024x1024"}
│
├── Span: draft_save (1s)
│   └── Event: draft_saved {version: 1, word_count: 1200}
│
├── Span: draft_save (1s)
│   └── Event: draft_saved {version: 2, word_count: 1350}
│
├── Span: draft_save (1s)
│   └── Event: draft_saved {version: 3, word_count: 1280}
│
├── Span: ai_improve_selection (10s)
│   ├── Generation: improvement_call (10s, 1.8k tokens)
│   ├── Metadata: {selected_text: "AI is transforming industries", action: "strengthen_opinion"}
│   └── Event: text_replaced {old_length: 28, new_length: 45}
│
├── Span: submit_for_review (2s)
│   └── Event: submitted_for_review {reviewer_id: "pedro"}
│
├── Span: human_review (2h) ──interrupt()──
│   ├── Event: review_requested
│   ├── Span: editorial_comment_1 (human action)
│   │   └── Metadata: {position: "paragraph_3", text: "Add more detail about Marriott case"}
│   ├── Span: editorial_comment_2 (human action)
│   │   └── Metadata: {position: "paragraph_5", text: "Good point about costs"}
│   ├── Event: review_completed {action: "request_changes", reviewer: "pedro"}
│   └── Metadata: {comments_count: 2, time_to_respond: "2h"}
│
├── Span: revision_1 (20m)
│   ├── Event: draft_saved {version: 4}
│   ├── Event: comment_resolved {comment_id: 1}
│   └── Span: ai_suggestion_3 (6s)
│       ├── Generation: suggestion_generation (6s, 0.9k tokens)
│       └── Event: suggestion_dismissed_by_user
│
├── Span: submit_for_review_2 (2s)
│   └── Event: submitted_for_review {reviewer_id: "pedro"}
│
├── Span: human_review_2 (30m) ──interrupt()──
│   ├── Event: review_requested
│   ├── Event: review_completed {action: "approve", reviewer: "pedro"}
│   └── Metadata: {time_to_respond: "30m"}
│
├── Span: publish (3s)
│   ├── Event: published
│   └── Metadata: {url: "/blog/the-real-cost...", scheduled: false}
│
└── Event: workflow_completed {status: "published", total_versions: 4, total_duration: "5h 20m"}
```

#### Blog Post Creation Trace Tree (From Carousel)

When a blog post is generated from a carousel, the trace tree must show the **parent-child relationship**:

```
Trace: blogpost_workflow_ghi789 (CHILD)
├── Metadata: {post_id, parent_project_id: "abc123", content_type: "blog_post"}
├── Tags: ["blog_post", "from_carousel", "workflow"]
│
├── Span: carousel_content_import (5s)
│   ├── Event: content_imported {source_project: "abc123", slides_imported: 7}
│   └── Metadata: {carousel_trace_id: "carousel_workflow_abc123"}
│
├── Span: content_expansion (45s)
│   ├── Generation: blog_expansion_call (45s, 5.2k tokens)
│   ├── Metadata: {model: "claude-sonnet-4", temperature: 0.7}
│   └── Event: content_expanded {word_count: 2500, sections: 5}
│
├── Span: image_mapping (2s)
│   └── Event: images_mapped {carousel_slide_refs: [1, 2, 3, 4, 5, 6, 7]}
│
└── ... (continues with editing, review, publish same as independent blog post)
```

**Link to parent trace:**
- Child trace metadata contains `parent_project_id` and `carousel_trace_id`
- Langfuse UI can navigate from blog post trace to originating carousel trace
- This enables full visibility: carousel → blog post → edits → published version

### 8.5.3 Trace Visibility Requirements

#### Every Operation Must Be Visible

| Operation | Visibility | Trace Location |
|-----------|-----------|----------------|
| **LLM Call** | ✅ Required | Generation node with tokens, latency, model |
| **Tool Call** | ✅ Required | Span showing tool name, inputs, outputs |
| **Human Interrupt** | ✅ Required | Span with events (requested, completed, timeout) |
| **Database Write** | ⚠️ Recommended | Span for audit trail (idempotent checks) |
| **File System Op** | ⚠️ Recommended | Span (image save, PDF export) |
| **External API** | ✅ Required | Span (DALL-E, web search, URL fetch) |
| **Queue/Event** | ✅ Required | Event emission to Redis Streams |
| **Error/Retry** | ✅ Required | Error spans with retry count, failure reason |
| **State Checkpoint** | ⚠️ Recommended | LangGraph checkpoint save |
| **Quality Score** | ✅ Required | Langfuse Score attached to trace |

#### Cross-Trace Linking

```python
# When creating a blog post from a carousel, link traces
async def create_blog_from_carousel(project_id: str, carousel_trace_id: str):
    # Create child trace with parent reference
    child_trace = langfuse.trace(
        name="blogpost_workflow",
        metadata={
            "post_id": post_id,
            "parent_project_id": project_id,
            "carousel_trace_id": carousel_trace_id,  # Link to parent
            "content_type": "blog_post",
            "generation_source": "carousel_derivative",
        },
        tags=["blog_post", "from_carousel"],
    )

    # Add relationship event
    child_trace.event(
        name="parent_trace_linked",
        metadata={
            "parent_trace_id": carousel_trace_id,
            "relationship": "derived_from",
        },
    )
```

### 8.5.4 What Must NOT Be a Blind Spot

The following are **critical visibility requirements** — missing any of these is a bug:

1. **Subagent spawning** — Every spawned subagent must appear as a child span
2. **Parallel execution** — All parallel tasks must be individually visible
3. **Human review time** — Time from `interrupt()` to response must be tracked
4. **Rejected content** — Rejections and feedback must be traced (not just successes)
5. **Retries** — Failed attempts before success must be visible
6. **Fallback paths** — When primary path fails and fallback is used
7. **Cache hits/misses** — When cached results are used vs. fresh generation
8. **Persona enforcement** — Voice match scores for each content piece
9. **Quality gates** — Scores and pass/fail decisions
10. **Cost per operation** — Token usage and API costs for every LLM/image call

### 8.5.5 Dashboard Views for Tree Visibility

#### Tree View

```
┌─ Carousel Workflow: AI Security Threats (abc123)
│  ├─ Brief: 2s ✓
│  ├─ Research: 45s ✓
│  │  ├─ Researcher (breaches): 12s, 3.2k tokens
│  │  ├─ Researcher (costs): 11s, 2.8k tokens
│  │  └─ Researcher (prevention): 13s, 3.1k tokens
│  ├─ Outline: 8s ✓
│  ├─ Content: 120s ✓
│  │  ├─ Slide 1: 15s, 2.1k tokens
│  │  ├─ Slide 2: 14s, 2.0k tokens
│  │  ├─ Slide 3: 16s, 2.3k tokens
│  │  ├─ Slide 4: 15s, 2.2k tokens
│  │  ├─ Slide 5: 14s, 2.1k tokens
│  │  ├─ Slide 6: 15s, 2.2k tokens
│  │  └─ Slide 7: 14s, 2.0k tokens
│  ├─ Design: 5s ✓
│  ├─ Images: 180s ✓
│  │  ├─ Image 1: 18s ($0.04)
│  │  ├─ Image 2: 19s ($0.04)
│  │  ├─ Image 3: 17s ($0.04)
│  │  ├─ Image 4: 18s ($0.04)
│  │  ├─ Image 5: 19s ($0.04)
│  │  ├─ Image 6: 18s ($0.04)
│  │  └─ Image 7: 18s ($0.04)
│  ├─ Quality: 12s ✓ (Score: 84/100)
│  ├─ Human Review (Brief): 2h15m ✓
│  ├─ Human Review (Content): 45m ✓ (3 edits)
│  ├─ Human Review (Final): 12m ✓
│  └─ Publish: 3s ✓
│
│  Total: 4h 32m | $4.07 | 188k tokens
│
│  Linked Blog Post: The Real Cost of AI Security Breaches (def456)
│  └─ Click to view blog post trace tree →
```

#### Blog Post Tree View

```
┌─ Blog Post Workflow: The Real Cost... (def456)
│  ├─ Created: 3s ✓
│  ├─ AI Suggestions: 2 shown, 1 applied
│  │  ├─ Suggestion 1 (improve): 8s ✓ (dismissed)
│  │  └─ Suggestion 2 (add_opinion): 7s ✓ (applied)
│  ├─ Image Generation: 15s ✓ ($0.04)
│  ├─ Draft Versions: 4 saved
│  ├─ AI Improve Selection: 10s ✓
│  ├─ Submit for Review: 2s ✓
│  ├─ Human Review (Round 1): 2h ✓ (2 comments)
│  ├─ Revision: 20m ✓ (1 comment resolved)
│  ├─ Submit for Review 2: 2s ✓
│  ├─ Human Review (Round 2): 30m ✓ (approved)
│  └─ Publish: 3s ✓
│
│  Total: 5h 20m | $0.85 | 12k tokens
│
│  Parent Carousel: AI Security Threats (abc123)
│  └─ Click to view carousel trace tree →
```

---

## 9. Risks & Mitigations

| Risk | Severity | Likelihood | Impact | Mitigation |
|------|----------|-----------|--------|-----------|
| **AI hallucinations in final content** | Critical | High | Brand damage, misinformation | Multi-stage review gates; fact-check agent; source citation enforcement; human approval on all published content |
| **Loss of Pedro's authentic voice** | Critical | High | Content feels generic, audience disengages | Persona engine with feedback loops; forbidden phrases list; writing sample training; voice match scoring |
| **Workflow friction — too many approval steps** | High | Medium | Users abandon platform; slower content production | Configurable workflow (skip phases for trusted users); batch approvals; smart defaults; one-click "approve all" with diff review |
| **Content quality inconsistency** | High | Medium | Variable output quality damages brand | Quality rubrics with thresholds; auto-reject below minimum scores; feedback loops; A/B testing framework |
| **System complexity explosion** | High | Medium | Harder to maintain; slower development | Modular architecture; feature flags; clear service boundaries; comprehensive test coverage |
| **Data model migration complexity** | High | High | Data loss, downtime | Event sourcing for audit trail; backward-compatible schema changes; blue-green deployment; comprehensive migration tests |
| **AI generation costs spiraling** | Medium | High | Unsustainable operating costs | Caching layer for similar prompts; request coalescing; usage quotas; model fallback (GPT-4 → GPT-3.5 for drafts); async processing |
| **Collaboration conflicts** | Medium | Medium | Lost edits, overwritten content | Optimistic locking with version vectors; real-time sync with CRDTs; conflict resolution UI |
| **Asset storage costs** | Medium | Medium | Image/video storage grows rapidly | Compression; CDN edge caching; lifecycle policies (archive old versions); deduplication |
| **Regulatory compliance (EU AI Act)** | Medium | Low | Fines, legal liability | AI disclosure labels; human-in-the-loop documentation; audit logs; data retention policies |
| **SEO impact of draft/approval delays** | Low | Medium | Slower publishing cadence hurts rankings | Batch scheduling; content calendar; evergreen content pipeline; repurpose published content |
| **Reviewer bottleneck** | Low | Medium | Content queue backs up | Multiple reviewers; review assignment algorithm; review reminders; escalation rules |

---

## 10. Code Snippets

### 10.1 Frontend: Rich Text Editor with AI Suggestions

```typescript
// components/rich-text-editor.tsx
import { useEditor, EditorContent } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import { useAiSuggestions } from '@/features/blog/hooks/use-ai-suggestions';

interface RichTextEditorProps {
  content: string;
  onChange: (content: string) => void;
  postId: string;
}

export function RichTextEditor({ content, onChange, postId }: RichTextEditorProps) {
  const { suggestions, applySuggestion, generateSuggestions } = useAiSuggestions(postId);

  const editor = useEditor({
    extensions: [StarterKit],
    content,
    onUpdate: ({ editor }) => {
      onChange(editor.getHTML());
    },
  });

  const handleAiImprove = async (type: 'improve' | 'shorten' | 'expand') => {
    const selection = editor?.state.selection;
    if (!selection || selection.empty) return;

    const selectedText = editor.state.doc.textBetween(
      selection.from,
      selection.to
    );

    const suggestion = await generateSuggestions({
      text: selectedText,
      type,
      context: editor.getText(),
    });

    // Show suggestion in a tooltip/popover
    editor.commands.setContent(suggestion.text);
  };

  return (
    <div className="rich-text-editor">
      <EditorContent editor={editor} />

      <AiToolbar
        onImprove={() => handleAiImprove('improve')}
        onShorten={() => handleAiImprove('shorten')}
        onExpand={() => handleAiImprove('expand')}
      />

      <SuggestionsPanel
        suggestions={suggestions}
        onApply={applySuggestion}
      />
    </div>
  );
}
```

### 10.2 Frontend: Workflow Stage Component

```typescript
// components/workflow-stage.tsx
import { useWorkflow } from '@/features/projects/hooks/use-workflow';

interface WorkflowStageProps {
  projectId: string;
}

export function WorkflowStage({ projectId }: WorkflowStageProps) {
  const { currentPhase, phases, approvePhase, rejectPhase } = useWorkflow(projectId);

  return (
    <div className="workflow-stage">
      <div className="phase-indicator">
        {phases.map((phase, index) => (
          <PhaseNode
            key={phase.id}
            name={phase.name}
            status={phase.status}
            isActive={phase.id === currentPhase}
            isCompleted={phase.isCompleted}
            index={index}
          />
        ))}
      </div>

      <div className="phase-content">
        {phases.map((phase) => (
          phase.id === currentPhase && (
            <PhasePanel key={phase.id} phase={phase}>
              {phase.status === 'awaiting_human' && (
                <div className="approval-actions">
                  <button onClick={() => approvePhase(phase.id)}>
                    Approve & Continue
                  </button>
                  <button onClick={() => rejectPhase(phase.id)}>
                    Request Changes
                  </button>
                </div>
              )}
            </PhasePanel>
          )
        ))}
      </div>
    </div>
  );
}
```

### 10.3 Backend: Workflow State Machine

```python
# domain/workflows/carousel_workflow.py
from enum import Enum, auto
from dataclasses import dataclass
from typing import Optional
from datetime import datetime

class PhaseStatus(Enum):
    PENDING = auto()
    IN_PROGRESS = auto()
    AWAITING_HUMAN = auto()
    APPROVED = auto()
    REJECTED = auto()

class CarouselPhase(Enum):
    BRIEF = "brief"
    RESEARCH = "research"
    OUTLINE = "outline"
    CONTENT = "content"
    DESIGN = "design"
    IMAGES = "images"
    FINAL_REVIEW = "final_review"

@dataclass
class PhaseState:
    phase: CarouselPhase
    status: PhaseStatus
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    reviewer_id: Optional[str]
    review_notes: Optional[str]
    data: dict  # phase-specific data

class CarouselWorkflow:
    PHASE_ORDER = [
        CarouselPhase.BRIEF,
        CarouselPhase.RESEARCH,
        CarouselPhase.OUTLINE,
        CarouselPhase.CONTENT,
        CarouselPhase.DESIGN,
        CarouselPhase.IMAGES,
        CarouselPhase.FINAL_REVIEW,
    ]

    def __init__(self, project_id: str):
        self.project_id = project_id
        self.phase_states: dict[CarouselPhase, PhaseState] = {
            phase: PhaseState(
                phase=phase,
                status=PhaseStatus.PENDING,
                started_at=None,
                completed_at=None,
                reviewer_id=None,
                review_notes=None,
                data={},
            )
            for phase in self.PHASE_ORDER
        }
        self.current_phase = CarouselPhase.BRIEF

    def start_phase(self, phase: CarouselPhase):
        self.phase_states[phase].status = PhaseStatus.IN_PROGRESS
        self.phase_states[phase].started_at = datetime.now()
        self.current_phase = phase

    def request_human_review(self, phase: CarouselPhase, message: str):
        self.phase_states[phase].status = PhaseStatus.AWAITING_HUMAN
        # Emit event: project.review.requested

    def approve_phase(self, phase: CarouselPhase, reviewer_id: str, notes: str = ""):
        self.phase_states[phase].status = PhaseStatus.APPROVED
        self.phase_states[phase].completed_at = datetime.now()
        self.phase_states[phase].reviewer_id = reviewer_id
        self.phase_states[phase].review_notes = notes

        # Move to next phase
        current_index = self.PHASE_ORDER.index(phase)
        if current_index < len(self.PHASE_ORDER) - 1:
            next_phase = self.PHASE_ORDER[current_index + 1]
            self.start_phase(next_phase)

    def reject_phase(self, phase: CarouselPhase, reviewer_id: str, feedback: str):
        self.phase_states[phase].status = PhaseStatus.REJECTED
        self.phase_states[phase].reviewer_id = reviewer_id
        self.phase_states[phase].review_notes = feedback

        # Return to previous phase or stay in current for revision
        # depending on the feedback
```

### 10.4 Backend: Blog Post with Versioning

```python
# infrastructure/database/models/blog_post.py
from sqlalchemy import Column, String, DateTime, Integer, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid

class BlogPostModel(Base):
    __tablename__ = "blog_posts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=True)
    title = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, nullable=False)
    status = Column(String(50), default="draft")  # draft, under_review, approved, published, archived

    # Content stored as JSONB for rich text
    content = Column(JSONB, default={})
    excerpt = Column(String(500))
    featured_image_url = Column(String(500))

    # Editorial
    author_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    reviewer_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    # SEO
    meta_title = Column(String(255))
    meta_description = Column(String(500))
    keywords = Column(JSONB, default=[])

    # Engagement
    view_count = Column(Integer, default=0)
    like_count = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    submitted_for_review_at = Column(DateTime, nullable=True)
    approved_at = Column(DateTime, nullable=True)
    published_at = Column(DateTime, nullable=True)
    scheduled_publish_at = Column(DateTime, nullable=True)

    # Relationships
    versions = relationship("ContentVersionModel", back_populates="blog_post")
    comments = relationship("EditorialCommentModel", back_populates="blog_post")
    sources = relationship("ContentSourceModel", back_populates="blog_posts")

class ContentVersionModel(Base):
    __tablename__ = "content_versions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    blog_post_id = Column(UUID(as_uuid=True), ForeignKey("blog_posts.id"))
    version_number = Column(Integer, nullable=False)
    snapshot = Column(JSONB, nullable=False)  # Full content snapshot
    change_summary = Column(String(500))
    author_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)

    blog_post = relationship("BlogPostModel", back_populates="versions")

class EditorialCommentModel(Base):
    __tablename__ = "editorial_comments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    blog_post_id = Column(UUID(as_uuid=True), ForeignKey("blog_posts.id"))
    content_type = Column(String(50))  # "paragraph", "slide", "section"
    position = Column(JSONB)  # {"paragraph_index": 3, "offset": 120}
    text = Column(String(2000), nullable=False)
    author_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    status = Column(String(50), default="open")  # open, resolved, dismissed
    ai_suggestion = Column(String(2000), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)

    blog_post = relationship("BlogPostModel", back_populates="comments")
```

### 10.5 Database Migration

```python
# migrations/alembic/versions/add_blog_posts_and_workflow.py
"""Add blog posts, content versions, editorial comments, and workflow state.

Revision ID: add_blog_posts_and_workflow
Revises: previous_revision
Create Date: 2026-05-23
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid

# revision identifiers
revision = 'add_blog_posts_and_workflow'
down_revision = 'previous_revision'


def upgrade():
    # Create blog_posts table
    op.create_table(
        'blog_posts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('projects.id'), nullable=True),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('slug', sa.String(255), unique=True, nullable=False),
        sa.Column('status', sa.String(50), default='draft'),
        sa.Column('content', postgresql.JSONB, default={}),
        sa.Column('excerpt', sa.String(500)),
        sa.Column('featured_image_url', sa.String(500)),
        sa.Column('author_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id')),
        sa.Column('reviewer_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('meta_title', sa.String(255)),
        sa.Column('meta_description', sa.String(500)),
        sa.Column('keywords', postgresql.JSONB, default=[]),
        sa.Column('view_count', sa.Integer, default=0),
        sa.Column('like_count', sa.Integer, default=0),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('submitted_for_review_at', sa.DateTime, nullable=True),
        sa.Column('approved_at', sa.DateTime, nullable=True),
        sa.Column('published_at', sa.DateTime, nullable=True),
        sa.Column('scheduled_publish_at', sa.DateTime, nullable=True),
    )

    # Create content_versions table
    op.create_table(
        'content_versions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('blog_post_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('blog_posts.id')),
        sa.Column('version_number', sa.Integer, nullable=False),
        sa.Column('snapshot', postgresql.JSONB, nullable=False),
        sa.Column('change_summary', sa.String(500)),
        sa.Column('author_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id')),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
    )

    # Create editorial_comments table
    op.create_table(
        'editorial_comments',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('blog_post_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('blog_posts.id')),
        sa.Column('content_type', sa.String(50)),
        sa.Column('position', postgresql.JSONB),
        sa.Column('text', sa.String(2000), nullable=False),
        sa.Column('author_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id')),
        sa.Column('status', sa.String(50), default='open'),
        sa.Column('ai_suggestion', sa.String(2000), nullable=True),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
        sa.Column('resolved_at', sa.DateTime, nullable=True),
    )

    # Add new columns to projects table
    op.add_column('projects', sa.Column('creative_brief', sa.Text, nullable=True))
    op.add_column('projects', sa.Column('persona_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('projects', sa.Column('rubric_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('projects', sa.Column('instructions', sa.Text, nullable=True))
    op.add_column('projects', sa.Column('current_phase', sa.String(50), default='brief'))
    op.add_column('projects', sa.Column('phase_status', sa.String(50), default='pending'))

    # Create persona_profiles table
    op.create_table(
        'persona_profiles',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('tone_attributes', postgresql.JSONB, default={}),
        sa.Column('writing_samples', postgresql.JSONB, default=[]),
        sa.Column('forbidden_phrases', postgresql.JSONB, default=[]),
        sa.Column('preferred_phrases', postgresql.JSONB, default=[]),
        sa.Column('sentence_structure_preferences', sa.Text),
        sa.Column('paragraph_style', sa.Text),
        sa.Column('opinion_expression', sa.Text),
        sa.Column('expertise_areas', postgresql.JSONB, default=[]),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('version', sa.Integer, default=1),
    )

    # Create indexes
    op.create_index('ix_blog_posts_status', 'blog_posts', ['status'])
    op.create_index('ix_blog_posts_slug', 'blog_posts', ['slug'])
    op.create_index('ix_blog_posts_author', 'blog_posts', ['author_id'])
    op.create_index('ix_content_versions_post', 'content_versions', ['blog_post_id'])
    op.create_index('ix_editorial_comments_post', 'editorial_comments', ['blog_post_id'])
    op.create_index('ix_projects_phase', 'projects', ['current_phase', 'phase_status'])


def downgrade():
    op.drop_table('editorial_comments')
    op.drop_table('content_versions')
    op.drop_table('blog_posts')
    op.drop_table('persona_profiles')

    op.drop_column('projects', 'creative_brief')
    op.drop_column('projects', 'persona_id')
    op.drop_column('projects', 'rubric_id')
    op.drop_column('projects', 'instructions')
    op.drop_column('projects', 'current_phase')
    op.drop_column('projects', 'phase_status')
```

---

## 11. Gherkin Scenarios

### 11.1 Feature: Carousel Workflow with Human-in-the-Loop

```gherkin
Feature: Carousel Creation with Enhanced Workflow
  As a content creator
  I want to guide the AI through each phase of carousel creation
  So that the output matches my vision and maintains quality

  Background:
    Given I am logged in as "Pedro"
    And I have a persona profile "Pedro's Professional Voice"
    And I have a quality rubric "Instagram Carousel Standard"

  # === HAPPY PATH ===

  Scenario: Create carousel with full workflow
    Given I navigate to the carousel creation page
    When I fill in the creative brief:
      | field        | value                                      |
      | topic        | "AI Security Threats in 2026"              |
      | audience     | "CISOs and security architects"              |
      | instructions | "Focus on real breaches, not predictions"   |
    And I upload source materials:
      | type     | title                    |
      | document | "Q1 2026 Breach Report"  |
      | url      | "https://example.com/..."|
    And I select persona "Pedro's Professional Voice"
    And I select rubric "Instagram Carousel Standard"
    And I submit the brief
    Then the project status should be "researching"
    And I should see "Research in progress..."

    When the research phase completes
    Then I should see research findings with key points
    And I should see a "Review Research" button

    When I click "Review Research"
    And I add a note: "Add more details about the Marriott breach"
    And I click "Approve & Continue"
    Then the project status should be "outlining"
    And I should see "Outline in progress..."

    When the outline phase completes
    Then I should see a slide-by-slide outline
    And I should be able to reorder slides
    And I should be able to edit slide titles

    When I move slide 3 to position 1
    And I edit slide 2 title to "The Real Cost of AI Breaches"
    And I click "Approve Outline"
    Then the project status should be "content_drafting"
    And I should see "Drafting slide content..."

    When the content phase completes
    Then I should see draft text for each slide
    And each slide should show:
      | field            | value                          |
      | draft text       | "AI breaches cost $4.2M on avg..." |
      | sources used     | "Q1 2026 Breach Report"        |
      | confidence score | "0.92"                         |

    When I edit slide 1 text to add a personal anecdote
    And I click "Approve Content"
    Then the project status should be "designing"

    When the design phase completes
    Then I should see the styled carousel preview
    And I should see a "Request Design Changes" button

    When I click "Approve Design"
    Then the project status should be "image_generating"

    When the images phase completes
    Then I should see generated images for each slide
    And I should see an "Upload Custom Image" button

    When I replace image 2 with a custom upload
    And I click "Approve Images"
    Then the project status should be "final_review"
    And I should see a quality score of "87/100"
    And I should see "All criteria passed"

    When I click "Publish"
    Then the project status should be "published"
    And I should see "Carousel published successfully"
    And the carousel should be visible on the public page

  # === EDGE CASES ===

  Scenario: Reject research and provide feedback
    Given the research phase has completed
    When I review the findings
    And I click "Request Changes"
    And I enter feedback: "Include more recent sources from 2026"
    Then the project should return to "researching" phase
    And the AI should re-research with the new criteria
    And I should see "Re-researching with updated criteria..."

  Scenario: Skip phases for trusted user
    Given I have "trusted_user" role
    And I have created 10+ carousels with 90%+ approval rate
    When I create a new carousel
    And I enable "Skip to Content Draft" option
    Then the project should skip "research" and "outline" phases
    And start directly at "content_drafting"

  Scenario: Content fails quality rubric
    Given the content phase has completed
    When the quality agent scores the content:
      | criterion         | score | threshold |
      | E-E-A-T           | 45    | 70        |
      | originality       | 60    | 75        |
      | voice_consistency | 80    | 70        |
    Then I should see "Quality check failed"
    And I should see specific feedback:
      | criterion   | issue                          |
      | E-E-A-T     | "Lacks first-hand experience"  |
      | originality | "Too similar to source material"|
    And the project should remain in "content_drafting" phase
    And I should see "AI is revising based on feedback..."

  Scenario: Workflow interruption and recovery
    Given the project is in "content_drafting" phase
    When the server restarts
    And I navigate back to the project
    Then the project should resume from "content_drafting" phase
    And I should see "Resuming from checkpoint..."
    And no progress should be lost

  Scenario: Concurrent editing prevention
    Given the project is in "content_review" phase
    And "Pedro" is reviewing the content
    When "Maria" attempts to approve the phase
    Then "Maria" should see "This phase is being reviewed by Pedro"
    And the approval should be rejected
    And "Maria" should see a "Request Review Handoff" option

  Scenario: Source material limits
    Given I am creating a carousel
    When I attempt to upload a 500MB video file as source material
    Then I should see "Source material must be under 50MB"
    And the upload should be rejected
    And I should see "Consider compressing or providing a transcript"

  # === ERROR CASES ===

  Scenario: AI generation timeout
    Given the project is in "image_generating" phase
    When the image generation exceeds 5 minutes
    Then I should see "Image generation is taking longer than expected"
    And I should see a "Retry" button
    And I should see a "Skip Images & Use Placeholders" option
    And the project should remain in "image_generating" phase

  Scenario: Invalid persona configuration
    Given I select a persona with no writing samples
    When I submit the brief
    Then I should see "Persona has no writing samples. Add examples first."
    And the brief submission should be blocked
    And I should see a link to "Edit Persona"
```

### 11.2 Feature: Blog Post Editorial Workflow

```gherkin
Feature: Blog Post Creation with Editorial Workflow
  As a content creator
  I want to write blog posts with AI assistance and editorial review
  So that I publish high-quality, original content

  Background:
    Given I am logged in as "Pedro"
    And I have a persona profile "Pedro's Professional Voice"

  # === HAPPY PATH ===

  Scenario: Create and publish blog post with AI assistance
    Given I navigate to the blog post creation page
    When I enter the title "The Real Cost of AI Security Breaches"
    And I select template "Opinion Piece"
    And I click "Create Draft"
    Then the post status should be "draft"
    And I should see a rich text editor

    When I type "AI security breaches are becoming more frequent..."
    And I click "AI Suggest"
    Then I should see suggestions:
      | type        | suggestion                                           |
      | improve     | "Add a specific statistic about 2026 breach costs" |
      | shorten     | "This paragraph is 200 words — consider splitting"   |
      | add_opinion | "Pedro's take: I predicted this in my 2024 talk..."  |

    When I click the "add_opinion" suggestion
    Then the text should be inserted with Pedro's opinion
    And I should see "Added based on your persona"

    When I upload an image " breach-chart.jpg"
    And I position it after paragraph 2
    Then the image should appear in the editor
    And I should see "Alt text: AI security breach cost chart showing..."

    When I add a source reference:
      | type  | title                    | url                        |
      | url   | "2026 Breach Report"     | "https://example.com/..."  |
    Then the source should appear in the references section
    And in-text citations should be updated

    When I click "Submit for Review"
    Then the post status should be "under_review"
    And "Pedro" should receive a review notification

    When "Pedro" reviews the post
    And adds a comment on paragraph 3: "Add more detail about the Marriott case"
    And clicks "Request Changes"
    Then the post status should be "draft"
    And I should see the comment in the editor

    When I address the comment by adding Marriott details
    And click "Resolve Comment"
    And click "Submit for Review" again
    Then the post status should be "under_review"

    When "Pedro" approves the post
    Then the post status should be "approved"
    And I should see "Ready to publish"

    When I click "Publish Now"
    Then the post status should be "published"
    And the post should be visible at "/blog/the-real-cost-of-ai-security-breaches"
    And the post should appear in the RSS feed
    And a social media preview should be generated

  Scenario: AI generates image for blog post
    Given I am editing a blog post in "draft" status
    When I click "Generate Image"
    And I enter prompt: "Abstract visualization of AI security vulnerabilities"
    Then the AI should generate an image
    And I should see a preview of the generated image
    And I should see "Generated in 12 seconds"

    When I click "Use This Image"
    Then the image should be inserted into the post
    And the alt text should be auto-generated
    And the image should be stored in the asset library

  # === EDGE CASES ===

  Scenario: Version history and rollback
    Given I have a published blog post
    And it has 5 versions in history
    When I navigate to "Version History"
    Then I should see a list of versions with:
      | version | date       | author | change_summary              |
      | 5       | 2026-05-20 | Pedro  | "Added conclusion paragraph"|
      | 4       | 2026-05-19 | Pedro  | "Fixed typo in title"       |

    When I select version 4
    And click "Preview Version"
    Then I should see the post as it appeared in version 4

    When I click "Restore This Version"
    And confirm "This will create version 6 with the content from version 4"
    Then a new version 6 should be created
    And the post content should match version 4
    And the post status should remain "published"
    And the public URL should serve the updated content

  Scenario: Collaborative editing with conflict
    Given "Pedro" is editing paragraph 3 of a blog post
    And "Maria" is editing the same paragraph simultaneously
    When "Pedro" saves changes
    And "Maria" attempts to save changes 2 seconds later
    Then "Maria" should see "This section was modified by Pedro"
    And she should see a diff view showing both versions
    And she should be able to:
      | option                    | action                                  |
      | Keep my changes           | Overwrite with Maria's version          |
      | Keep Pedro's changes      | Discard Maria's changes                 |
      | Merge both              | Combine changes (if non-conflicting)    |
      | Save as new version     | Create a branch for review              |

  Scenario: Scheduled publishing
    Given a blog post is in "approved" status
    When I set scheduled publish to "2026-06-01 09:00:00"
    And click "Schedule"
    Then the post status should be "approved"
    And I should see "Scheduled for June 1, 2026 at 9:00 AM"
    And the post should not be publicly visible

    When the scheduled time arrives
    Then the post should automatically change status to "published"
    And I should receive a notification "Your post is now live"

  Scenario: Unpublish and edit
    Given a blog post is "published"
    When I click "Unpublish"
    And confirm "This will make the post invisible to readers"
    Then the post status should be "draft"
    And the public URL should return 404
    And SEO crawlers should see "noindex"

    When I edit the post and add new content
    And click "Publish"
    Then the post should be visible again
    And the URL should remain the same
    And returning readers should see the updated content

  # === ERROR CASES ===

  Scenario: AI suggestion on empty selection
    Given I am editing a blog post
    When I click "AI Improve" without selecting any text
    Then I should see "Please select text to improve"
    And no AI request should be made

  Scenario: Duplicate slug prevention
    Given a blog post exists with slug "ai-security-2026"
    When I create a new post with title "AI Security 2026"
    Then the slug should be auto-generated as "ai-security-2026-2"
    And I should see "Slug adjusted to avoid conflict"

  Scenario: Image generation failure
    Given I request an AI-generated image
    When the image generation fails after 3 retries
    Then I should see "Image generation failed"
    And I should see fallback options:
      | option                  | description                          |
      | Retry                   | Try again with same prompt           |
      | Simplify Prompt         | Use a shorter, simpler prompt        |
      | Upload Image            | Use your own image instead           |
      | Skip Image             | Continue without an image            |
```

### 11.3 Feature: Persona and Voice Management

```gherkin
Feature: Persona Profile Management
  As a content creator
  I want to define and refine my writing persona
  So that AI-generated content matches my authentic voice

  Background:
    Given I am logged in as "Pedro"

  Scenario: Create persona from writing samples
    When I navigate to "Persona Settings"
    And I enter persona name "Pedro's Professional Voice"
    And I upload 5 writing samples:
      | sample_title                    | file              |
      | "LinkedIn Post - AI Ethics"     | "sample1.txt"     |
      | "Blog - Startup Lessons"        | "sample2.txt"     |
      | "Twitter Thread - Security"     | "sample3.txt"     |
      | "Newsletter - May 2026"         | "sample4.txt"     |
      | "Conference Talk Transcript"    | "sample5.txt"     |
    And I click "Analyze Voice"
    Then the AI should analyze the samples and extract:
      | attribute                     | value                                      |
      | tone                          | "conversational, confident, occasionally humorous" |
      | sentence_length               | "Short punchy sentences (avg 12 words)"     |
      | paragraph_structure           | "1-3 sentences per paragraph"               |
      | opinion_expression            | "Strong opinions, loosely held"             |
      | common_phrases                | ["Here's the thing", "What most people miss"] |
      | forbidden_patterns            | ["In today's world", "Let's dive in"]       |
    And I should see a persona preview with sample rewrite

    When I adjust the "formality" slider to 0.3
    Then the sample rewrite should update in real-time
    And it should sound less formal

    When I click "Save Persona"
    Then the persona should be saved
    And I should see "Persona 'Pedro's Professional Voice' created"

  Scenario: Persona feedback loop
    Given I have a persona "Pedro's Professional Voice"
    And I generated a carousel with AI
    When I edit slide 2 and replace:
      | original                         | replacement                                    |
      | "AI is transforming industries"    | "AI isn't just changing industries — it's eating them alive" |
    And I click "This edit improves the voice match"
    Then the system should record this as a positive example
    And future AI outputs should lean toward:
      | pattern          | example                              |
      | strong_opinions  | "isn't just... it's eating them alive" |
      | vivid_language   | "eating them alive"                    |

    When I generate another carousel
    Then the AI should use more vivid language and strong opinions

  Scenario: Voice match scoring
    Given I have a persona "Pedro's Professional Voice"
    When I paste text: "In today's world, AI is transforming how we work. Let's dive into the details."
    And click "Check Voice Match"
    Then I should see a score of "23/100"
    And I should see specific issues:
      | issue                    | suggestion                          |
      | "In today's world"       | "Remove — it's a forbidden phrase"  |
      | "Let's dive into"        | "Replace with 'Here's what actually matters'" |
      | "transforming how we work"| "Too neutral — add Pedro's opinion" |
    And I should see a rewritten version that scores "91/100"
```

---

## 12. Implementation Task List

### Phase 1: Foundation (Weeks 1-2) — ✅ COMPLETED 2026-05-23

**Backend Tasks**

- [x] **DB-001**: Create migration for `blog_posts`, `content_versions`, `editorial_comments`, `persona_profiles`, `quality_rubrics`, `content_sources` tables
- [x] **DB-002**: Add workflow state columns to `projects` table (`current_phase`, `phase_status`, `creative_brief`, `persona_id`, `rubric_id`, `instructions`)
- [x] **DB-003**: Create indexes for workflow queries and blog post lookups
- [x] **API-001**: Implement `POST /api/personas` and `GET /api/personas` endpoints
- [x] **API-002**: Implement `POST /api/rubrics` and `GET /api/rubrics` endpoints
- [x] **API-003**: Implement `POST /api/projects/{id}/sources` CRUD endpoints
- [x] **API-004**: Implement blog post CRUD endpoints (`POST/GET/PUT/DELETE /api/blog-posts`)
- [x] **API-005**: Implement blog post workflow endpoints (`submit-review`, `approve`, `reject`, `publish`, `unpublish`)
- [x] **API-006**: Implement editorial comment endpoints
- [x] **API-007**: Implement content version endpoints (`GET versions`, `POST restore-version`)
- [ ] **API-008**: Implement project workflow action endpoints (`submit-brief`, `approve-phase`, `reject-phase`)
- [x] **AUTH-001**: Add role-based access control (admin, editor, reviewer, author)
- [ ] **TEST-001**: Write unit tests for all new API endpoints (target: 90%+ coverage)
- [x] **TEST-002**: Write integration tests for blog post workflow

**Frontend Tasks**

- [x] **UI-001**: Create persona management page (`/personas`)
- [x] **UI-002**: Create rubric management page (`/rubrics`)
- [ ] **UI-003**: Create source material upload component
- [ ] **UI-004**: Create workflow stage indicator component
- [x] **UI-005**: Create blog post list page with status filters
- [ ] **UI-006**: Create blog post editor page with rich text editor (TipTap)
- [ ] **UI-007**: Create editorial comment thread component
- [ ] **UI-008**: Create version history sidebar with diff view
- [ ] **UI-009**: Update project creation form with new fields (brief, persona, rubric, sources)
- [ ] **UI-010**: Create AI suggestion tooltip component for editor
- [ ] **TEST-003**: Write component tests for new UI components
- [ ] **TEST-004**: Write E2E tests for blog post creation workflow

### Phase 2: AI Integration (Weeks 3-4)

**Backend Tasks**

- [x] **AI-001**: Implement `PersonaAgent` with voice enforcement and scoring
- [x] **AI-002**: Implement `QualityAgent` with rubric evaluation
- [x] **AI-003**: Implement `FeedbackLearningLoop` for recording corrections
- [x] **AI-004**: Extend carousel workflow with 7 phases and human interrupt points
- [x] **AI-005**: Implement blog post AI assistance endpoints (`ai-suggest`, `ai-improve`, `generate-image`)
- [x] **AI-006**: Implement source synthesis agent (extract key points from uploaded materials)
- [x] **AI-007**: Implement outline generation with human-editable output
- [x] **AI-008**: Implement content draft generation with persona enforcement
- [x] **AI-009**: Implement quality auto-evaluation with threshold checks
- [x] **AI-010**: Add originality scoring using similarity detection
- [x] **CACHE-001**: Implement caching layer for AI prompt responses
- [x] **TEST-005**: Write tests for all AI agents
- [x] **OBS-001**: Implement Langfuse trace tree for carousel workflows (all phases visible)
- [x] **OBS-002**: Implement Langfuse trace tree for blog post workflows (independent creation)
- [x] **OBS-003**: Link blog post traces to parent carousel traces (cross-trace visibility)
- [x] **OBS-004**: Add `propagate_attributes()` for multi-agent workflow tracing
- [x] **OBS-005**: Implement custom spans for human review gates with events
- [x] **OBS-006**: Add Langfuse scores for quality, voice match, originality per trace

**Frontend Tasks**

- [x] **UI-011**: Integrate AI suggestion panel into rich text editor
- [x] **UI-012**: Create AI image generation modal with prompt input and preview
- [x] **UI-013**: Create persona voice match scorer with real-time feedback
- [x] **UI-014**: Create quality rubric display with pass/fail indicators
- [x] **UI-015**: Implement workflow phase panels (research, outline, content, design, images)
- [x] **UI-016**: Implement real-time workflow status updates via SSE
- [x] **UI-017**: Create source material viewer with AI-extracted key points

### Phase 3: Workflow & Collaboration (Weeks 5-6)

**Backend Tasks**

- [x] **WF-001**: Implement event-driven workflow engine with Kafka/Redis Streams
- [x] **WF-002**: Implement workflow persistence with checkpoints (LangGraph checkpointer)
- [x] **WF-003**: Implement phase approval/rejection with notification system
- [x] **WF-004**: Implement workflow audit log (event sourcing)
- [x] **WF-005**: Implement concurrent editing prevention (optimistic locking)
- [x] **NOTIF-001**: Implement notification system (email, in-app) for review requests
- [x] **NOTIF-002**: Implement deadline reminders for pending reviews
- [x] **SCHED-001**: Implement scheduled publishing with cron worker
- [x] **SCHED-002**: Implement content calendar view endpoint

**Frontend Tasks**

- [x] **UI-018**: Create workflow Kanban board view
- [x] **UI-019**: Create notification center component
- [x] **UI-020**: Create content calendar view
- [x] **UI-021**: Implement collaborative editing with Yjs or Liveblocks
- [x] **UI-022**: Create review assignment interface
- [x] **UI-023**: Create diff view for version comparison
- [x] **UI-024**: Implement scheduled publish datetime picker

### Phase 4: Quality & Polish (Weeks 7-8)

**Backend Tasks**

- [x] **QUAL-001**: Implement plagiarism detection integration
- [x] **QUAL-002**: Implement AI content disclosure labeling
- [x] **QUAL-003**: Implement SEO analysis endpoint
- [x] **QUAL-004**: Implement accessibility check (alt text, color contrast)
- [x] **PERF-001**: Optimize database queries for blog post listings
- [x] **PERF-002**: Implement CDN integration for image assets
- [x] **MON-001**: Add OpenTelemetry instrumentation for new services
- [x] **SEC-001**: Implement audit logging for all editorial actions

**Frontend Tasks**

- [x] **UI-025**: Implement SEO preview component (title, description, social cards)
- [x] **UI-026**: Implement accessibility checker with warnings
- [x] **UI-027**: Create dashboard analytics (content velocity, quality scores)
- [x] **UI-028**: Implement search and filter for blog posts
- [x] **UI-029**: Create mobile-responsive workflow views
- [x] **UI-030**: Add keyboard shortcuts for editor
- [x] **I18N-001**: Add translations for all new UI text

### Phase 5: Migration & Launch (Week 9)

**Tasks**

- [x] **MIG-001**: Migrate existing projects to new schema (creative_brief = concatenation of existing fields)
- [x] **MIG-002**: Create default persona from existing carousel outputs
- [x] **MIG-003**: Create default quality rubric
- [x] **MIG-004**: Backfill workflow state for in-progress projects
- [x] **DOC-001**: Update API documentation
- [x] **DOC-002**: Create user guide for new workflow features
- [x] **DOC-003**: Update architecture documentation
- [x] **DEPLOY-001**: Deploy to staging environment
- [x] **DEPLOY-002**: Run load tests on new endpoints
- [x] **DEPLOY-003**: Deploy to production with feature flags
- [x] **MON-002**: Set up alerts for workflow failures

---

## 12. Technical Debt Backlog (Post–Phase 5)

Phase 2 QA remediation cleared all **blockers** (score: 78/100). Remaining items are deferred until after Phase 5 launch.

**Full register:** [docs/TECHNICAL_DEBT.md](TECHNICAL_DEBT.md)

| ID | Priority | Summary |
|----|----------|---------|
| TD-001 | P1 | `use-blog-posts.ts` → `authenticatedFetch`; remove stale `reviewer_id` |
| TD-002 | P1 | Mutation score ≥ 70% (ADR-005) — carousel workflow + blog AI tests |
| TD-003 | P1 | Vitest tests for Phase 2 UI components/hooks |
| TD-004 | P1 | Wire Gherkin specs or demote to manual test plans |
| TD-005 | P2 | Persist `FeedbackLearningLoop` to database |
| TD-006 | P2 | Replace in-memory editorial workflow cache (Redis/checkpointer) |
| TD-007 | P2 | Generic error responses in `documents.py` |
| TD-008 | P2 | API route integration tests (blog AI, editorial workflow) |
| TD-009 | P2 | Observability test coverage (OBS-003–006) |
| TD-010 | P3 | i18n for AI hook error strings |
| TD-011 | P3 | Wire `personaId` into `AiSuggestionPanel` |
| TD-012 | P3 | Consolidate rubric threshold constants |
| TD-013 | P3 | Strengthen prompt-injection defenses |
| TD-014 | P3 | `documents.py` ruff cleanup |
| TD-015 | P3 | Resolve npm moderate advisories |
| TD-016 | P3 | Remove unused exports / document test-only APIs |

---

## 13. Appendix: Research Citations

### Instagram Carousel Best Practices
- Hootsuite — Instagram Carousel Guide: https://blog.hootsuite.com/instagram-carousel/
- Buffer — Instagram Carousel Ideas: https://buffer.com/library/instagram-carousel/
- Later — Instagram Carousel Posts: https://later.com/blog/instagram-carousel-posts/
- Sprout Social — Content Creation: https://sproutsocial.com/insights/social-media-content-creation/
- Search Engine Journal — Instagram Carousel Study: https://www.searchenginejournal.com/instagram-carousels/379311/
- SocialInsider — Instagram Carousel Benchmarks 2026: https://www.socialinsider.io/blog/instagram-carousel-research/

### Blog Editorial Workflows
- WordPress.com Blog: https://wordpress.com/blog/2024/
- Ghost Blog: https://ghost.org/blog/
- Medium Blog: https://blog.medium.com/
- Substack About: https://substack.com/about
- Grammarly Blog: https://www.grammarly.com/blog/

### AI-Human Collaboration
- Google AI Blog: https://blog.google/technology/ai/
- OpenAI Research: https://openai.com/research/
- Anthropic Research: https://www.anthropic.com/research
- SEMrush AI Content: https://www.semrush.com/blog/ai-content-creation/
- Neil Patel AI Content: https://neilpatel.com/blog/ai-content-creation/

### Observability & Langfuse
- Langfuse Documentation: https://langfuse.com/docs
- LangChain Integration: https://langfuse.com/docs/integrations/frameworks/langchain
- LangGraph Observability: https://langfuse.com/docs/integrations/frameworks/langgraph
- Langfuse Metadata & Propagation: https://langfuse.com/docs/tracing-features/metadata

### Technical Architecture
- Martin Fowler — Patterns of Distributed Systems: https://martinfowler.com/articles/patterns-of-distributed-systems/
- Confluent Blog: https://www.confluent.io/blog/
- Redis Blog: https://redis.com/blog/
- Supabase Blog: https://supabase.com/blog

---

**End of Plan**
