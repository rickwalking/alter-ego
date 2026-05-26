# LangChain Deep Agents: Comprehensive Implementation Guide for Alter-Ego

**Version:** 1.0
**Date:** 2026-05-23
**Status:** Research Complete — Ready for Implementation
**Based on:** LangGraph 0.3.x, LangChain 0.3.x, Deep Agents Beta

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [What Are Deep Agents?](#2-what-are-deep-agents)
3. [Multi-Agent Patterns](#3-multi-agent-patterns)
4. [Production Configuration](#4-production-configuration)
5. [Human-in-the-Loop (HITL)](#5-human-in-the-loop-hitl)
6. [Memory Architecture](#6-memory-architecture)
7. [Anti-Patterns & Pitfalls](#7-anti-patterns--pitfalls)
8. [Implementation for Alter-Ego](#8-implementation-for-alter-ego)
9. [Code Examples](#9-code-examples)
10. [Testing Deep Agents](#10-testing-deep-agents)
11. [Resources & References](#11-resources--references)

---

## 1. Executive Summary

LangChain Deep Agents are a "batteries-included" harness built on LangGraph that adds planning, virtual filesystem tools, subagent spawning, QuickJS interpreters, auto-summarization, and built-in human-in-the-loop. They are the recommended abstraction for complex, multi-step AI workflows like Alter-Ego's carousel and blog post pipelines.

**Key recommendation for Alter-Ego:**
- Use **Deep Agents** for the high-level orchestration (carousel workflow, blog post workflow)
- Use **raw LangGraph** for custom nodes that don't need the Deep Agent harness (e.g., deterministic formatting)
- Use **Subagent pattern** for parallel research and content drafting
- Use **interrupt()** for all human approval gates

---

## 2. What Are Deep Agents?

### 2.1 Deep Agents vs. Simple Agents

| Feature | Simple Agent (`create_agent`) | Deep Agent (`create_deep_agent`) |
|---------|------------------------------|----------------------------------|
| Planning | No | Built-in (`write_todos`) |
| Tool Composition | Static | Dynamic (QuickJS interpreter) |
| Subagents | No | Yes (`task` tool spawns subgraphs) |
| Memory | Basic | Auto-summarization + persistent |
| HITL | Manual | Built-in (`interrupt()`) |
| File System | No | Virtual filesystem tools |
| Permissions | None | Declarative permission system |

**Rule of thumb:**
- Use `create_agent` for simple Q&A ("What is the weather?")
- Use `create_deep_agent` for complex workflows ("Create a 10-slide carousel about AI security")
- Use raw LangGraph when you need full control over graph topology

### 2.2 When to Use What in Alter-Ego

| Component | Recommended Abstraction | Why |
|-----------|------------------------|-----|
| Carousel workflow orchestration | Deep Agent | Needs planning, subagents, HITL |
| Blog post workflow orchestration | Deep Agent | Needs planning, subagents, HITL |
| Research subagent | Deep Agent subagent | Isolated context per research task |
| Content drafting subagent | Deep Agent subagent | Isolated context per slide/section |
| Image generation node | Raw LangGraph node | Deterministic, no reasoning needed |
| PDF export node | Raw LangGraph node | Deterministic, no reasoning needed |
| Quality scoring node | Raw LangGraph node | Deterministic evaluation |
| Voice enforcement | Raw LangGraph node | Single LLM call with persona prompt |

---

## 3. Multi-Agent Patterns

LangGraph officially supports 5 multi-agent patterns. Based on our research and community validation (GitHub, Reddit, blog posts), here's how they apply to Alter-Ego:

### 3.1 Subagents (Recommended for Alter-Ego)

**What:** Parent agent spawns child agents with isolated state and context. Each subagent completes a task and returns results.

**Best for:** Parallel research, parallel drafting, isolated tasks with strong context boundaries.

**Performance:** Excellent for parallel multi-domain work. Each subagent gets a fresh context window.

```python
from langgraph_deep import create_deep_agent

# Parent orchestrator
orchestrator = create_deep_agent(
    model="claude-sonnet-4-20250514",
    tools=["task"],  # Enables subagent spawning
    name="carousel_orchestrator",
)

# Research subagent
research_subagent = create_deep_agent(
    model="gpt-4o",
    tools=["web_search", "read_url", "write_file"],
    name="researcher",
)

# Content subagent
content_subagent = create_deep_agent(
    model="claude-sonnet-4-20250514",
    tools=["write_file", "read_file"],
    name="content_drafter",
)

# Spawn parallel research tasks
results = await orchestrator.ainvoke({
    "messages": [{
        "role": "user",
        "content": "Create carousel about AI security. Spawn 3 research subagents: "
                   "1) Recent breaches, 2) Cost statistics, 3) Prevention strategies."
    }]
})
```

**Alter-Ego Use Case:**
- Research phase: Spawn subagents per source material topic
- Content phase: Spawn subagents per slide (parallel drafting)
- Each subagent has isolated context — no token bloat from other slides

### 3.2 Handoffs

**What:** Conversational flow where agents "pass the phone" to each other based on context.

**Best for:** Conversational UI, chatbots, support flows.

**Alter-Ego Use Case:**
- Publish page chat assistant (already implemented)
- Not recommended for workflow phases (too conversational)

### 3.3 Skills

**What:** On-demand specialized tools that the agent invokes for specific tasks.

**Best for:** Simple repeated tasks with knowledge retrieval.

**Alter-Ego Use Case:**
- "Improve this paragraph" skill
- "Generate alt text" skill
- "Check voice match" skill

### 3.4 Router

**What:** Classifies input and dispatches to parallel workers.

**Best for:** Multi-intent classification, content moderation.

**Alter-Ego Use Case:**
- Route user feedback to correct subagent (content vs. design vs. images)
- Classify source material type (document, URL, data, interview)

### 3.5 Custom Workflow

**What:** Mix of deterministic logic and agentic behavior in a hand-crafted graph.

**Best for:** Complex workflows with precise control over execution order.

**Alter-Ego Use Case:**
- The main carousel workflow graph (custom nodes + agentic subagents)
- Blog post editorial workflow (deterministic state transitions + agentic suggestions)

---

## 4. Production Configuration

### 4.1 Checkpoint Persistence

```python
from langgraph.checkpoint.postgres import PostgresSaver
from psycopg_pool import ConnectionPool

# Connection pool for production
pool = ConnectionPool(
    conninfo="postgresql://user:pass@localhost/rag_db",
    max_size=20,
    kwargs={"autocommit": True, "prepare_threshold": 0},
)

# Postgres checkpointer
checkpointer = PostgresSaver(pool)
checkpointer.setup()  # Create tables if not exist

# Compile workflow with persistence
workflow = StateGraph(CarouselWorkflowState)
# ... add nodes ...
app = workflow.compile(checkpointer=checkpointer)
```

### 4.2 DeltaChannel (Critical for Long Workflows)

LangGraph 1.2+ introduces `DeltaChannel` which reduces checkpoint storage from O(N²) to O(N) — a **41× reduction** for long sessions.

```python
from langgraph.channels import DeltaChannel

class CarouselWorkflowState(TypedDict):
    # Use DeltaChannel for append-only lists
    slide_drafts: Annotated[list[dict], DeltaChannel]
    ai_suggestions: Annotated[list[dict], DeltaChannel]

    # Use regular channels for replaceable values
    current_phase: str
    status: str
```

**Without DeltaChannel:** 50 slides × 50 checkpoints = 2500 state copies stored
**With DeltaChannel:** 50 slides × 1 base + 49 deltas = ~50 state copies stored

### 4.3 Durability Modes

| Mode | Use Case | Trade-off |
|------|----------|-----------|
| `exit` | Fastest | May lose last few steps on crash |
| `async` | Balanced | Good for most production use |
| `sync` | Safest | Slowest, waits for disk flush |

**Recommendation for Alter-Ego:** Use `async` for workflow checkpoints, `sync` for human approval gates.

```python
app = workflow.compile(
    checkpointer=checkpointer,
    checkpointer_durability="async",
)
```

---

## 5. Human-in-the-Loop (HITL)

### 5.1 The `interrupt()` Pattern

```python
from langgraph.types import interrupt

async def content_review_node(state: CarouselWorkflowState):
    """Pause workflow and wait for human approval."""

    # Present draft to human
    human_response = interrupt({
        "type": "content_review",
        "slide_drafts": state["slide_drafts"],
        "sources_used": state["sources"],
        "voice_match_scores": state["voice_scores"],
        "message": "Please review the slide drafts. Approve or request changes.",
    })

    # Process human response
    if human_response["action"] == "approve":
        return {"content_approved": True, "reviewer_id": human_response["user_id"]}

    elif human_response["action"] == "reject":
        return {
            "content_approved": False,
            "review_feedback": human_response["feedback"],
            "reviewer_id": human_response["user_id"],
        }

    elif human_response["action"] == "edit":
        # Apply human edits and re-review
        return {
            "slide_drafts": human_response["edited_slides"],
            "content_approved": False,  # Go through review again
            "reviewer_id": human_response["user_id"],
        }
```

### 5.2 Resuming from Interrupt

```python
# Frontend calls this when user submits review
config = {"configurable": {"thread_id": project_id}}

# Resume workflow with human input
result = await app.ainvoke(
    Command(resume={
        "action": "approve",
        "user_id": "pedro-user-id",
    }),
    config,
)
```

### 5.3 Critical Production Rules

1. **Never wrap `interrupt()` in bare `try/except`** — this swallows the interrupt
2. **Always make side effects before `interrupt()` idempotent** — workflow may retry
3. **Keep `interrupt()` calls in deterministic order** — same inputs → same interrupt points
4. **Set explicit timeouts** — auto-reject after N hours to prevent stuck workflows
5. **Use durable checkpointer** — `PostgresSaver`, never in-memory for production

### 5.4 Timeout Handling

```python
import asyncio
from datetime import datetime, timedelta

async def review_with_timeout(state):
    try:
        # 24-hour timeout for human review
        human_response = await asyncio.wait_for(
            interrupt({"type": "review", "data": state}),
            timeout=86400,  # 24 hours
        )
        return {"approved": True, "response": human_response}
    except asyncio.TimeoutError:
        # Auto-reject after timeout
        return {
            "approved": False,
            "reason": "timeout",
            "auto_rejected": True,
        }
```

---

## 6. Memory Architecture

Deep Agents and LangGraph support four memory types. Alter-Ego needs all four:

### 6.1 Working Memory (Short-Term)

**Scope:** Single workflow thread/session
**Implementation:** Thread-scoped via checkpointer
**Use in Alter-Ego:** Current carousel state, draft content, review feedback

```python
# Working memory is automatic with checkpointer
# State persists across checkpoints within a thread
config = {"configurable": {"thread_id": project_id}}
state = app.get_state(config)  # Get current working memory
```

### 6.2 Episodic Memory (Action History)

**Scope:** Cross-thread, per user
**Implementation:** LangGraph Store (`BaseStore`)
**Use in Alter-Ego:** Past carousel corrections, previous review feedback, common edit patterns

```python
from langgraph.store import InMemoryStore  # Dev; use Postgres in prod

store = InMemoryStore()

# Save episodic memory
store.put(
    ("pedro_user_id", "corrections"),
    "carousel_123_slide_2",
    {
        "original": "AI is transforming industries",
        "corrected": "AI isn't just changing industries — it's eating them alive",
        "type": "voice_enforcement",
        "timestamp": "2026-05-23T10:00:00Z",
    }
)

# Retrieve relevant past corrections
memories = store.search(
    ("pedro_user_id", "corrections"),
    query="strong opinions about AI",
    limit=5,
)
```

### 6.3 Semantic Memory (Knowledge/Facts)

**Scope:** Cross-thread, per persona/project
**Implementation:** Vector search (Pinecone) + LangGraph Store
**Use in Alter-Ego:** Writing samples, source materials, brand guidelines, expertise areas

```python
# Already implemented via Pinecone + RAG
# Enhance by storing in LangGraph Store for faster access
store.put(
    ("persona", "pedro_professional"),
    "writing_samples",
    {
        "samples": writing_samples,
        "tone_attributes": persona.tone_attributes,
        "forbidden_phrases": persona.forbidden_phrases,
    }
)
```

### 6.4 Procedural Memory (Self-Improving Skills)

**Scope:** System-wide
**Implementation:** Self-updating system prompts via reflection
**Use in Alter-Ego:** System prompt improvements based on aggregate feedback, automatic prompt optimization

```python
async def reflection_node(state):
    """Critique workflow performance and update procedural memory."""

    # Analyze what worked and what didn't
    critique = await llm.complete(f"""
    Review this carousel creation workflow:
    - Phase transitions: {state['phase_history']}
    - Human rejections: {state['rejection_count']}
    - Quality scores: {state['quality_scores']}

    What patterns lead to rejections?
    How can we improve the system prompt for next time?
    """)

    # Update procedural memory
    store.put(
        ("system", "procedural"),
        "carousel_lessons",
        {"critique": critique, "timestamp": datetime.now()},
    )

    return {"reflection_completed": True}
```

---

## 7. Anti-Patterns & Pitfalls

Based on community reports (Reddit r/LangChain, GitHub issues, blog posts), here are the most common failures:

### 7.1 Over-Engineering with Multi-Agent

**Anti-Pattern:** Using 5+ agents when 1-2 would suffice.

**Symptom:** High token usage, slow response times, agents passing buck endlessly.

**Fix:** Start with a single agent. Add subagents only when:
- Tasks are truly parallelizable
- Context isolation is required (one task shouldn't see another's context)
- Different models are optimal for different tasks (cheap model for research, expensive for writing)

### 7.2 Wrapping `interrupt()` in Bare `try/except`

**Anti-Pattern:**
```python
try:
    result = interrupt({"type": "review"})
except Exception:
    pass  # SILENTLY SWALLOWS INTERRUPT!
```

**Fix:**
```python
try:
    result = interrupt({"type": "review"})
except GraphInterrupt:
    raise  # Re-raise — let LangGraph handle it
except ValueError as e:
    # Only catch specific expected errors
    return {"error": str(e)}
```

### 7.3 Non-Deterministic Control Flow

**Anti-Pattern:** Using `datetime.now()` or `random()` in node logic.

**Symptom:** Replaying the graph produces different results — checkpoints become unreliable.

**Fix:** Pass timestamps/random seeds as state; make nodes pure functions of state.

```python
# BAD
async def my_node(state):
    if datetime.now().hour > 12:  # Non-deterministic!
        return {"afternoon": True}

# GOOD
async def my_node(state):
    if state["current_hour"] > 12:  # Deterministic!
        return {"afternoon": True}
```

### 7.4 Mixing Static Edges and Dynamic `Command`

**Anti-Pattern:** Using both `add_conditional_edges()` and `Command(goto=...)` in the same node.

**Symptom:** Confusing execution flow, hard to debug.

**Fix:** Use static edges for structure, `Command` only for subagent handoffs or dynamic routing.

### 7.5 Ignoring Checkpoint Storage Growth

**Anti-Pattern:** Using default channels for append-only lists without `DeltaChannel`.

**Symptom:** PostgreSQL table grows to gigabytes; query performance degrades.

**Fix:** Use `DeltaChannel` for append-only state; set checkpoint TTL (e.g., 90 days).

### 7.6 Insufficient Error Handling in Subagents

**Anti-Pattern:** Subagent crashes bubble up and kill the entire parent workflow.

**Fix:** Wrap subagent calls in error handlers; return partial results + error log.

```python
async def safe_subagent(task):
    try:
        return await subagent.ainvoke(task)
    except Exception as e:
        return {"error": str(e), "partial_results": []}
```

---

## 8. Implementation for Alter-Ego

### 8.1 Recommended Architecture

```
┌────────────────────────────────────────────────────────────┐
│                  DEEP AGENT ORCHESTRATOR                    │
│              (LangGraph workflow with HITL)               │
├────────────────────────────────────────────────────────────┤
│  Nodes:                                                    │
│  ├─ brief_review ──interrupt()──→ wait for human         │
│  ├─ research_spawn ──task tool──→ 3 parallel subagents  │
│  ├─ research_synthesize (deterministic)                  │
│  ├─ outline_review ──interrupt()──→ wait for human         │
│  ├─ content_spawn ──task tool──→ N parallel subagents     │
│  ├─ content_review ──interrupt()──→ wait for human         │
│  ├─ design_apply (deterministic)                           │
│  ├─ design_review ──interrupt()──→ wait for human          │
│  ├─ image_spawn ──task tool──→ parallel image generation   │
│  ├─ image_review ──interrupt()──→ wait for human           │
│  ├─ quality_check (deterministic scoring)                  │
│  └─ final_review ──interrupt()──→ wait for human           │
└────────────────────────────────────────────────────────────┘
                              │
┌────────────────────────────────────────────────────────────┐
│                      SUBAGENTS                              │
│  ├─ Research Subagent: web search, read URL, synthesize   │
│  ├─ Content Subagent: draft slide copy with persona        │
│  ├─ Image Subagent: generate, edit, describe             │
│  └─ Quality Subagent: score against rubric                 │
└────────────────────────────────────────────────────────────┘
                              │
┌────────────────────────────────────────────────────────────┐
│                     MEMORY LAYER                            │
│  ├─ Working: Postgres checkpointer (thread-scoped)       │
│  ├─ Episodic: LangGraph Store (user corrections)         │
│  ├─ Semantic: Pinecone + LangGraph Store (samples)       │
│  └─ Procedural: LangGraph Store (system improvements)     │
└────────────────────────────────────────────────────────────┘
```

### 8.2 Model Selection Strategy

| Task | Model | Why |
|------|-------|-----|
| Orchestrator | Claude Sonnet 4 | Complex reasoning, long context |
| Research | GPT-4o-mini | Fast, cheap, good at web search |
| Content drafting | Claude Sonnet 4 | Creative writing, voice matching |
| Image generation | DALL-E 3 / Stable Diffusion | Visual quality |
| Quality scoring | GPT-4o-mini | Deterministic, cheap |
| Alt text | GPT-4o-mini | Simple description task |

### 8.3 Token Budget Planning

| Phase | Est. Tokens | Model | Est. Cost |
|-------|-------------|-------|-----------|
| Research (3 parallel) | 15k × 3 = 45k | GPT-4o-mini | $0.03 |
| Synthesize | 10k | Claude Sonnet | $0.15 |
| Outline | 8k | Claude Sonnet | $0.12 |
| Content (10 slides) | 12k × 10 = 120k | Claude Sonnet | $1.80 |
| Design | 5k | Claude Sonnet | $0.08 |
| Images (10) | 2k × 10 = 20k | DALL-E 3 | $2.00 |
| Quality | 8k | GPT-4o-mini | $0.01 |
| **Total** | **~216k** | | **~$4.19** |

**Optimization:** Use cheaper models for research/quality; reserve Claude for creative tasks.

---

## 9. Code Examples

### 9.1 Complete Carousel Workflow Graph

```python
from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, END
from langgraph.types import interrupt
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.channels import DeltaChannel
import operator

# ─── STATE ───
class CarouselState(TypedDict):
    project_id: str
    current_phase: str
    brief: dict
    research_findings: Annotated[list[dict], operator.add]
    outline: list[dict]
    slide_drafts: Annotated[list[dict], DeltaChannel]
    design_template: dict
    image_urls: list[str]
    quality_score: float
    human_approvals: Annotated[list[dict], DeltaChannel]
    errors: Annotated[list[str], operator.add]

# ─── NODES ───
async def review_brief(state: CarouselState):
    """Human reviews the creative brief."""
    response = interrupt({
        "type": "brief_review",
        "brief": state["brief"],
        "message": "Review the creative brief before research begins.",
    })
    return {"human_approvals": [{"phase": "brief", "action": response["action"]}]}

async def spawn_research(state: CarouselState):
    """Spawn parallel research subagents."""
    topics = state["brief"]["research_topics"]

    # Use task tool to spawn subagents
    tasks = [
        {"agent": "researcher", "prompt": f"Research: {topic}"}
        for topic in topics
    ]

    # Parallel execution
    results = await asyncio.gather(*[
        run_subagent(task) for task in tasks
    ], return_exceptions=True)

    findings = []
    errors = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            errors.append(f"Research task {i} failed: {result}")
        else:
            findings.append(result)

    return {
        "research_findings": findings,
        "errors": errors,
    }

async def synthesize_research(state: CarouselState):
    """Synthesize findings into key points."""
    # Deterministic node — no AI needed, just structured combination
    all_points = []
    for finding in state["research_findings"]:
        all_points.extend(finding["key_points"])

    return {"research_synthesis": all_points}

async def review_research(state: CarouselState):
    """Human reviews synthesized research."""
    response = interrupt({
        "type": "research_review",
        "findings": state["research_findings"],
        "synthesis": state.get("research_synthesis", []),
    })
    return {"human_approvals": [{"phase": "research", "action": response["action"]}]}

async def generate_outline(state: CarouselState):
    """AI generates slide-by-slide outline."""
    outline = await content_agent.generate_outline(
        brief=state["brief"],
        research=state["research_findings"],
        persona_id=state["brief"]["persona_id"],
    )
    return {"outline": outline}

async def review_outline(state: CarouselState):
    """Human reviews and edits outline."""
    response = interrupt({
        "type": "outline_review",
        "outline": state["outline"],
    })
    return {
        "outline": response.get("edited_outline", state["outline"]),
        "human_approvals": [{"phase": "outline", "action": response["action"]}],
    }

async def spawn_content_drafting(state: CarouselState):
    """Spawn parallel content subagents per slide."""
    slides = state["outline"]

    tasks = [
        {
            "agent": "content_drafter",
            "prompt": f"Draft slide {i+1}: {slide['title']}\nKey points: {slide['key_points']}",
        }
        for i, slide in enumerate(slides)
    ]

    results = await asyncio.gather(*[
        run_subagent(task) for task in tasks
    ], return_exceptions=True)

    drafts = []
    errors = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            errors.append(f"Slide {i+1} draft failed: {result}")
            drafts.append({"slide_index": i, "content": "", "error": True})
        else:
            drafts.append({"slide_index": i, "content": result["content"], "error": False})

    return {"slide_drafts": drafts, "errors": errors}

async def review_content(state: CarouselState):
    """Human reviews slide drafts."""
    response = interrupt({
        "type": "content_review",
        "slide_drafts": state["slide_drafts"],
    })
    return {
        "slide_drafts": response.get("edited_slides", state["slide_drafts"]),
        "human_approvals": [{"phase": "content", "action": response["action"]}],
    }

async def apply_design(state: CarouselState):
    """Apply visual theme to slides."""
    # Deterministic — no AI reasoning needed
    designed = await design_service.apply_template(
        slides=state["slide_drafts"],
        template=state["brief"]["visual_theme"],
    )
    return {"design_template": designed}

async def review_design(state: CarouselState):
    """Human reviews design."""
    response = interrupt({
        "type": "design_review",
        "preview": state["design_template"],
    })
    return {"human_approvals": [{"phase": "design", "action": response["action"]}]}

async def spawn_image_generation(state: CarouselState):
    """Generate images for each slide."""
    slides = state["slide_drafts"]

    tasks = [
        {
            "agent": "image_generator",
            "prompt": slide.get("image_prompt", f"Illustration for: {slide['content'][:100]}"),
        }
        for slide in slides
    ]

    results = await asyncio.gather(*[
        run_subagent(task) for task in tasks
    ], return_exceptions=True)

    urls = []
    errors = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            errors.append(f"Image {i+1} failed: {result}")
            urls.append("")
        else:
            urls.append(result["url"])

    return {"image_urls": urls, "errors": errors}

async def review_images(state: CarouselState):
    """Human reviews generated images."""
    response = interrupt({
        "type": "image_review",
        "images": state["image_urls"],
    })
    return {
        "image_urls": response.get("edited_images", state["image_urls"]),
        "human_approvals": [{"phase": "images", "action": response["action"]}],
    }

async def quality_check(state: CarouselState):
    """Score final carousel against rubric."""
    scores = await quality_agent.evaluate(
        slides=state["slide_drafts"],
        rubric_id=state["brief"]["rubric_id"],
    )
    return {"quality_score": scores["overall"], "quality_details": scores}

async def final_review(state: CarouselState):
    """Final human approval before publish."""
    response = interrupt({
        "type": "final_review",
        "carousel": {
            "slides": state["slide_drafts"],
            "images": state["image_urls"],
            "score": state["quality_score"],
        },
    })
    return {
        "human_approvals": [{"phase": "final", "action": response["action"]}],
        "current_phase": "published" if response["action"] == "publish" else "draft",
    }

# ─── EDGES ───
def route_brief_review(state: CarouselState):
    last = state["human_approvals"][-1]
    return "research" if last["action"] == "approve" else END

def route_research_review(state: CarouselState):
    last = state["human_approvals"][-1]
    return "outline" if last["action"] == "approve" else "research"

def route_outline_review(state: CarouselState):
    last = state["human_approvals"][-1]
    return "content" if last["action"] == "approve" else "outline"

def route_content_review(state: CarouselState):
    last = state["human_approvals"][-1]
    return "design" if last["action"] == "approve" else "content"

def route_design_review(state: CarouselState):
    last = state["human_approvals"][-1]
    return "images" if last["action"] == "approve" else "design"

def route_image_review(state: CarouselState):
    last = state["human_approvals"][-1]
    return "quality" if last["action"] == "approve" else "images"

def route_quality(state: CarouselState):
    return "final" if state["quality_score"] >= 70 else "content"

def route_final(state: CarouselState):
    last = state["human_approvals"][-1]
    return END if last["action"] == "publish" else "draft"

# ─── BUILD GRAPH ───
workflow = StateGraph(CarouselState)

workflow.add_node("brief_review", review_brief)
workflow.add_node("research", spawn_research)
workflow.add_node("synthesize", synthesize_research)
workflow.add_node("research_review", review_research)
workflow.add_node("outline", generate_outline)
workflow.add_node("outline_review", review_outline)
workflow.add_node("content", spawn_content_drafting)
workflow.add_node("content_review", review_content)
workflow.add_node("design", apply_design)
workflow.add_node("design_review", review_design)
workflow.add_node("images", spawn_image_generation)
workflow.add_node("image_review", review_images)
workflow.add_node("quality", quality_check)
workflow.add_node("final_review", final_review)

workflow.set_entry_point("brief_review")
workflow.add_conditional_edges("brief_review", route_brief_review)
workflow.add_edge("research", "synthesize")
workflow.add_edge("synthesize", "research_review")
workflow.add_conditional_edges("research_review", route_research_review)
workflow.add_edge("outline", "outline_review")
workflow.add_conditional_edges("outline_review", route_outline_review)
workflow.add_edge("content", "content_review")
workflow.add_conditional_edges("content_review", route_content_review)
workflow.add_edge("design", "design_review")
workflow.add_conditional_edges("design_review", route_design_review)
workflow.add_edge("images", "image_review")
workflow.add_conditional_edges("image_review", route_image_review)
workflow.add_edge("quality", "final_review")
workflow.add_conditional_edges("final_review", route_final)

# Compile with persistence
pool = ConnectionPool(conninfo="postgresql://...")
checkpointer = PostgresSaver(pool)
checkpointer.setup()

app = workflow.compile(checkpointer=checkpointer)
```

### 9.2 Subagent Implementation

```python
from langgraph_deep import create_deep_agent
from langchain_core.tools import tool

@tool
def web_search(query: str) -> str:
    """Search the web for information."""
    return search_service.search(query)

@tool
def read_url(url: str) -> str:
    """Read and extract text from a URL."""
    return extraction_service.extract(url)

@tool
def write_file(path: str, content: str) -> str:
    """Write content to the virtual filesystem."""
    return vfs.write(path, content)

research_subagent = create_deep_agent(
    model="gpt-4o-mini",
    tools=[web_search, read_url, write_file],
    name="researcher",
    system_prompt="""
    You are a research assistant. Your job is to find accurate, up-to-date information.

    Rules:
    - Always cite sources with URLs
    - Extract key points, not full text
    - Flag uncertain information
    - Write findings to the virtual filesystem
    """,
)

content_subagent = create_deep_agent(
    model="claude-sonnet-4-20250514",
    tools=[write_file],
    name="content_drafter",
    system_prompt="""
    You are a content writer. Draft engaging slide copy for Instagram carousels.

    Rules:
    - Maximum 40 words per slide
    - Use strong opinions, not neutral statements
    - Include data and statistics where relevant
    - Write in the persona's voice (provided in context)
    - Avoid: "In today's world", "Let's dive in", "It is important to note"
    """,
)

async def run_subagent(task: dict) -> dict:
    """Run a subagent with error handling."""
    agent_type = task["agent"]
    prompt = task["prompt"]

    agents = {
        "researcher": research_subagent,
        "content_drafter": content_subagent,
        "image_generator": image_subagent,
    }

    agent = agents.get(agent_type)
    if not agent:
        raise ValueError(f"Unknown agent type: {agent_type}")

    try:
        result = await agent.ainvoke({"messages": [{"role": "user", "content": prompt}]})
        return {"content": result["messages"][-1].content, "success": True}
    except Exception as e:
        return {"error": str(e), "success": False}
```

---

## 10. Testing Deep Agents

### 10.1 Unit Testing Graph Nodes

```python
import pytest
from unittest.mock import Mock, AsyncMock

@pytest.mark.asyncio
async def test_review_brief_approval():
    """Given user approves brief, when review node runs, then advances to research."""
    state = {
        "project_id": "test-123",
        "brief": {"topic": "AI Security"},
        "human_approvals": [],
    }

    # Mock interrupt to simulate human approval
    with patch("langgraph.types.interrupt", return_value={"action": "approve", "user_id": "pedro"}):
        result = await review_brief(state)

    assert result["human_approvals"] == [{"phase": "brief", "action": "approve"}]

@pytest.mark.asyncio
async def test_spawn_research_parallel():
    """Given 3 research topics, when spawn node runs, then executes 3 tasks in parallel."""
    state = {
        "brief": {"research_topics": ["breaches", "costs", "prevention"]},
        "research_findings": [],
    }

    with patch("__main__.run_subagent", new_callable=AsyncMock) as mock:
        mock.side_effect = [
            {"key_points": ["Breach 1", "Breach 2"]},
            {"key_points": ["Cost: $4.2M"]},
            {"key_points": ["Use MFA"]},
        ]
        result = await spawn_research(state)

    assert len(result["research_findings"]) == 3
    assert mock.call_count == 3  # Parallel execution
```

### 10.2 Integration Testing with Mock Checkpointer

```python
from langgraph.checkpoint.memory import MemorySaver

@pytest.mark.asyncio
async def test_full_workflow_happy_path():
    """Given valid brief, when full workflow runs with approvals, then publishes carousel."""

    # Use in-memory checkpointer for tests
    memory_checkpointer = MemorySaver()
    test_app = workflow.compile(checkpointer=memory_checkpointer)

    config = {"configurable": {"thread_id": "test-workflow-123"}}

    # Start workflow
    await test_app.ainvoke({"brief": {"topic": "Test"}}, config)

    # Simulate human approvals at each interrupt
    for phase in ["brief", "research", "outline", "content", "design", "images", "final"]:
        state = test_app.get_state(config)
        if state.next == ("__interrupt__",):
            await test_app.ainvoke(
                Command(resume={"action": "approve", "user_id": "test-user"}),
                config,
            )

    # Verify final state
    final_state = test_app.get_state(config)
    assert final_state.values["current_phase"] == "published"
```

### 10.3 Mutation Testing Considerations

When mutation testing Deep Agent code:
- **Equality mutations** on routing logic are critical (e.g., `score >= 70` → `score > 70`)
- **Conditional mutations** on interrupt checks (e.g., `if response["action"] == "approve"` → `if True`)
- **Arithmetic mutations** on quality scoring (e.g., weighted average calculations)
- **Skip** logging and error message mutations (use `do_not_mutate_patterns`)

---

## 11. Resources & References

### Official Documentation
- **LangGraph Docs:** https://langchain-ai.github.io/langgraph/
- **LangChain How-To:** https://python.langchain.com/docs/how_to/
- **Deep Agents (Beta):** https://github.com/langchain-ai/deep-agent
- **LangGraph Store:** https://langchain-ai.github.io/langgraph/reference/store/

### GitHub Examples
- **Multi-agent patterns:** https://github.com/langchain-ai/langgraph/tree/main/examples/multi_agent
- **Human-in-the-loop:** https://github.com/langchain-ai/langgraph/tree/main/examples/human-in-the-loop
- **Reflection agents:** https://github.com/langchain-ai/langgraph/tree/main/examples/reflection

### Community Discussions
- **Reddit r/LangChain:** https://www.reddit.com/r/LangChain/
- **LangChain Blog:** https://blog.langchain.dev/
- **LangChain Discord:** #langgraph channel

### Production Case Studies
- **LangChain GTM Agent:** Deep Agents with parallel subagents, Slack HITL, memory loop
- **Chat LangChain:** Simple vs. Deep agent comparison for docs Q&A
- **Reflection Patterns:** Reflexion, LATS, CRITIC implementations

### Academic Papers
- **ReAct:** Yao et al. (2022) — Reasoning + Acting in LLMs
- **Reflexion:** Shinn et al. (2023) — Self-reflective agents
- **LATS:** Zhou et al. (2023) — Language Agent Tree Search
- **CRITIC:** Gou et al. (2023) — Tool-interactive critiquing

---

**End of LangChain Deep Agents Guide**
