# Agentic Architecture Refactoring Plan

> **Scope:** `rag_backend.application.services` — RAGAgent, CarouselAgent, LangGraph pipeline
> **Last updated:** 2026-04-24
> **Status:** ✅ All 5 phases implemented and deployed

---

## Implementation Summary

| Phase | Status | Key Deliverables |
|-------|--------|------------------|
| 1. Prompt Externalization | ✅ Complete | `agents/prompts/` with Jinja2 registry, 8 prompts extracted to YAML/Markdown |
| 2. Tool Registry Refactor | ✅ Complete | `application/tools/` with domain-separated modules (knowledge_base/, carousel/) |
| 3. Agent Reclassification | ✅ Complete | `agents/rag_agent.py`, `agents/carousel_orchestrator.py`, backward-compat shims |
| 4. Subgraph Decomposition | ✅ Complete | `carousel/phases/` with 8 phase modules, graph.py is ~80-line orchestrator |
| 5. Deep Agents Alignment | ✅ Complete | Subagent registration, skill files, `agents/AGENTS.md`, `skills/` expanded |

**Quality gates:** ruff ✅ bandit ✅ vulture ✅ import-linter (4/4) ✅ **Tests:** 252 passed

---

## Table of Contents

1. [Current State Analysis](#1-current-state-analysis)
2. [Identified Issues](#2-identified-issues)
3. [Research Summary](#3-research-summary)
4. [Proposed Target Architecture](#4-proposed-target-architecture)
5. [Phase 1: Prompt Externalization](#5-phase-1-prompt-externalization)
6. [Phase 2: Tool Registry Refactor](#6-phase-2-tool-registry-refactor)
7. [Phase 3: Agent Reclassification](#7-phase-3-agent-reclassification)
8. [Phase 4: LangGraph Subgraph Decomposition](#8-phase-4-langgraph-subgraph-decomposition)
9. [Phase 5: Deep Agents Alignment](#9-phase-5-deep-agents-alignment)
10. [Migration Strategy](#10-migration-strategy)
11. [Decision Records](#11-decision-records)

---

## 1. Current State Analysis

### File Inventory

```
backend/src/rag_backend/application/services/
├── carousel/                  # LangGraph subgraph (good)
│   ├── graph.py               # 415 lines — monolithic builder
│   ├── nodes/
│   │   ├── caption.py         # 1 hardcoded prompt
│   │   ├── content.py         # 2 hardcoded prompts (title, content)
│   │   ├── design.py          # 0 prompts (calls template builder)
│   │   ├── export.py          # 0 prompts
│   │   ├── images.py          # 0 prompts
│   │   ├── linkedin.py        # 0 prompts
│   │   ├── progress.py        # 0 prompts
│   │   └── research.py        # 0 prompts
│   ├── state.py               # PipelineState TypedDict
│   ├── subagent.py            # Compiled subagent graph
│   ├── types.py               # SlideData, etc.
│   └── theme_resolver.py      # Theme resolution logic
├── carousel_agent.py          # 404 lines — agent + phase wrappers
├── carousel_refinement.py     # 206 lines — 2 hardcoded prompt templates
├── carousel_template.py       # 201 lines — 3+ hardcoded prompt builders
├── rag_agent.py               # 345 lines — agent + inline tool definitions
├── rag_agent_tools.py         # 297 lines — 3 tool factories + helpers
├── tools/                     # ONLY contains research_tool.py, image_tool.py
│   ├── research_tool.py
│   └── image_tool.py
├── image_provider_registry.py
├── linkedin_post_generator.py
├── pdf_slide_builder.py
└── writing_style_profile.py
```

### Hardcoded Prompt Inventory

| File | Prompt | Lines | Context |
|------|--------|-------|---------|
| `rag_agent.py:33` | `SYSTEM_PROMPT` | 34 | RAG agent system instructions |
| `rag_agent_tools.py:174` | `rewrite_prompt` | 7 | Carousel copy refinement |
| `carousel_refinement.py` | `IMAGE_PROMPT_REWRITE_TEMPLATE` | 6 | Image prompt rewriting |
| `carousel_refinement.py` | `DESIGN_PROMPT_TEMPLATE` | ~10 | Design CSS generation |
| `carousel_template.py` | `build_title_prompt()` | ~20 | Title optimization |
| `carousel_template.py` | `build_content_prompt()` | ~40 | Content synthesis |
| `carousel_template.py` | `build_caption_prompt()` | ~15 | Instagram caption |
| `carousel/nodes/content.py` | implicit via template | — | Content node orchestration |

**Total:** ~8 distinct prompt templates, ~132 lines of inline prompt text scattered across 5 files.

---

## 2. Identified Issues

### Issue 1: Tools Are Not Where They Belong

**Current:** RAG agent tools (`search_documents`, `list_documents`, `generate_carousel`, `refine_carousel_copy`, `regenerate_slide_image`, `refine_carousel_design`) are defined inline inside `rag_agent.py` and `rag_agent_tools.py`.

**Problem:**
- Tools are domain-specific (knowledge base, carousel generation, copy refinement) but live in generic files
- Tool definitions are mixed with agent orchestration logic
- `rag_agent.py` is 345 lines — 60% is tool code
- No clear boundary between "what the agent can do" and "how the agent decides"
- Adding a new tool requires editing the agent file

**Research consensus:** Deep Agents / LangChain best practice is **domain-separated tool modules** with minimal toolsets per subagent. Tools should be organized by capability domain, not by which agent uses them.

### Issue 2: Prompts Are Hardcoded in Source

**Current:** All prompts are Python string literals embedded in `.py` files.

**Problem:**
- Cannot iterate on prompts without code changes + redeployment
- No versioning — A/B testing different prompt variants is impossible
- No centralized audit trail of prompt changes
- Non-engineers (content team, prompt engineers) cannot contribute
- Prompt drift: same concepts rephrased differently across files
- `carousel_template.py` is 201 lines, 70%+ of which is prompt building

**Research consensus:** Production teams (Weights & Biases, Canva, Hamilton, Anthropic) universally recommend **external prompt files** (YAML/Markdown) with Jinja2 templating, git versioning, and registry-based loading.

### Issue 3: Agents Live in `/services`

**Current:** `RAGAgent` and `CarouselAgent` are in `application/services/`.

**Problem:**
- In Clean Architecture, "services" are business-logic orchestrators (use cases)
- Agents are **orchestration frameworks** — they decide *what* to do, not *how* to do it
- The actual business logic lives in the tools and nodes
- Agents are closer to "controllers" or "workflows" than "services"
- This misplacement makes the architecture harder to reason about

**Research consensus:** LangGraph production templates place graphs in `application/workflows/` or `application/agents/`. Deep Agents treats agents as first-class graph orchestrators, separate from business services.

### Issue 4: LangGraph Pipeline Is a Monolith

**Current:** `build_graph()` in `carousel/graph.py` is a single 415-line function that defines all 11 nodes, edges, and closure-scoped shared state.

**Problem:**
- All 8 pipeline phases share one state schema (`PipelineState`)
- Image generation fan-out uses closure-scoped `asyncio.Lock()` and `list[...]` boxes — fragile and hard to test
- No subgraph decomposition — the entire pipeline is one compiled graph
- Cannot reuse individual phases in other contexts
- Cannot checkpoint at subgraph boundaries independently

**Research consensus:** LangGraph best practice for complex multi-phase pipelines is **subgraph decomposition** — each phase is a compiled subgraph, parent graph orchestrates. This provides namespace isolation, independent development, and per-phase checkpointing.

### Issue 5: Deep Agents Usage Is Shallow

**Current:** `RAGAgent` uses `create_deep_agent()` as a thin wrapper around `ChatAnthropic` + tools.

**Problem:**
- Not using `AGENTS.md` / `SKILL.md` progressive disclosure
- Not using `ToolRuntime` for dependency injection
- Not using subagents for context isolation
- System prompt is a single 34-line string — no skill-based composition
- No middleware (logging, rate limiting, guardrails)

**Research consensus:** Deep Agents is designed for **skill-based prompt composition** and **subagent delegation**. The current usage treats it as a glorified `create_react_agent`, leaving most of its value unused.

---

## 3. Research Summary

### Deep Agents Best Practices

| Concern | Recommendation |
|---------|---------------|
| **Agent structure** | Function-based harness (`create_deep_agent`) + class-based middleware for cross-cutting concerns |
| **Tool organization** | Domain-separated modules; minimal toolsets per subagent; `ToolRuntime` for context |
| **Prompt management** | `AGENTS.md` for persistent memory, `SKILL.md` for progressive-disclosure skills |
| **Persistence** | LangGraph checkpointers for state; `CompositeBackend` + `StoreBackend` for long-term memory |
| **Context isolation** | Subagents for "context quarantine" — delegate heavy work, return summaries |

### LangGraph Best Practices

| Concern | Recommendation |
|---------|---------------|
| **Graph organization** | One workflow = one folder: `state.py`, `nodes.py`, `graph.py` |
| **Complex pipelines** | Use **subgraphs as phase boundaries** for namespace isolation |
| **Dependency injection** | `Runtime` context + `context_schema` (LangGraph >= 1.1) |
| **Checkpointing** | `PostgresSaver` in production; per-invocation subgraphs by default |
| **Send/fan-out** | Conditional edges returning `Send` objects; use reducers |

### Prompt Management Best Practices

| Concern | Recommendation |
|---------|---------------|
| **Storage** | YAML files in `prompts/` organized by domain |
| **Templating** | Jinja2 via `jinja2.Environment` |
| **Versioning** | Git + semantic folder structure (`v1/`, `v2/`) |
| **Loading** | Registry pattern with `@lru_cache` |
| **A/B testing** | Hash-based user bucketing to select prompt versions |
| **Observability** | Log `prompt_slug`, `prompt_version`, content hash with every LLM request |

---

## 4. Proposed Target Architecture

```
# Project root
skills/                                # Deep Agents skills (existing — stays)
├── carousel-pipeline/
│   ├── SKILL.md                       # 7-phase pipeline (existing)
│   ├── bmad-skill-manifest.yaml       # (existing)
│   └── workflow.md                    # (existing)
├── carousel-refinement/               # NEW
│   └── SKILL.md
└── knowledge-base/                    # NEW
    └── SKILL.md

backend/src/rag_backend/
├── agents/                            # NEW — Agent orchestrators
│   ├── __init__.py
│   ├── rag_agent.py                   # RAG chat agent (was services/rag_agent.py)
│   ├── carousel_orchestrator.py       # Carousel pipeline (was services/carousel_agent.py)
│   ├── prompts/                       # NEW — Runtime prompt templates
│   │   ├── _shared/
│   │   │   ├── guidelines/
│   │   │   │   └── security.md
│   │   │   └── variables.yaml
│   │   ├── rag/
│   │   │   ├── v1/
│   │   │   │   ├── system.md          # (was rag_agent.py:33)
│   │   │   │   └── config.yaml
│   │   │   └── v2/
│   │   ├── carousel/
│   │   │   ├── v1/
│   │   │   │   ├── title_prompt.yaml       # (was carousel_template.py title)
│   │   │   │   ├── content_prompt.yaml     # (was carousel_template.py content)
│   │   │   │   ├── caption_prompt.yaml     # (was carousel_template.py caption)
│   │   │   │   └── config.yaml
│   │   │   └── v1.1/
│   │   ├── refinement/
│   │   │   ├── v1/
│   │   │   │   ├── copy_rewrite.yaml       # (was rag_agent_tools.py:174)
│   │   │   │   ├── image_rewrite.yaml      # (was carousel_refinement.py)
│   │   │   │   └── design_css.yaml         # (was carousel_refinement.py)
│   │   │   └── v2/
│   │   └── registry.py                # Prompt loader with caching
│   └── AGENTS.md                      # NEW — Persistent agent memory
│
├── application/
│   ├── services/                      # Business logic services
│   │   ├── carousel/                  # LangGraph subgraph
│   │   │   ├── graph.py               # Refactored to use subgraphs
│   │   │   ├── nodes/                 # Pure node functions
│   │   │   ├── state.py
│   │   │   ├── types.py
│   │   │   └── phases/                # NEW — Subgraph per phase
│   │   │       ├── __init__.py
│   │   │       ├── research/
│   │   │       │   ├── state.py
│   │   │       │   ├── nodes.py
│   │   │       │   └── graph.py
│   │   │       ├── content/
│   │   │       │   ├── state.py
│   │   │       │   ├── nodes.py
│   │   │       │   └── graph.py
│   │   │       ├── images/
│   │   │       │   ├── state.py
│   │   │       │   ├── nodes.py
│   │   │       │   └── graph.py
│   │   │       └── ...
│   │   ├── carousel_template.py       # Refactored: delegates to prompt registry
│   │   ├── carousel_refinement.py     # Refactored: delegates to prompt registry
│   │   └── ...
│   │
│   └── tools/                         # NEW — All agent tools
│       ├── __init__.py
│       ├── knowledge_base/
│       │   ├── __init__.py
│       │   ├── search_documents.py    # (was rag_agent.py)
│       │   └── list_documents.py      # (was rag_agent.py)
│       ├── carousel/
│       │   ├── __init__.py
│       │   ├── generate_carousel.py   # (was rag_agent.py)
│       │   ├── refine_copy.py         # (was rag_agent_tools.py)
│       │   ├── regenerate_image.py    # (was rag_agent_tools.py)
│       │   └── refine_design.py       # (was rag_agent_tools.py)
│       └── registry.py                # Tool discovery & registration
│
├── domain/
│   └── protocols.py                   # CarouselAgent → CarouselOrchestrator
│
└── ...
```

---

## 5. Phase 1: Prompt Externalization

### 5.1 Create Prompt Registry

**File:** `backend/src/rag_backend/agents/prompts/registry.py`

```python
"""Prompt template registry with lazy loading and caching."""

from functools import lru_cache
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader

PROMPTS_DIR = Path(__file__).parent

_jinja_env = Environment(
    loader=FileSystemLoader(PROMPTS_DIR),
    autoescape=False,
)


class PromptNotFoundError(LookupError):
    """Raised when a requested prompt template does not exist."""


@lru_cache(maxsize=128)
def _load_prompt_config(domain: str, name: str, version: str) -> dict:
    """Load and cache a prompt configuration file."""
    path = PROMPTS_DIR / domain / version / f"{name}.yaml"
    if not path.exists():
        raise PromptNotFoundError(f"Prompt not found: {path}")
    with open(path) as f:
        return yaml.safe_load(f)


def render_prompt(
    domain: str,
    name: str,
    variables: dict[str, object],
    *,
    version: str = "v1",
) -> tuple[str, dict[str, object]]:
    """Render a prompt template with variables.

    Returns:
        Tuple of (rendered_prompt, model_config).
    """
    config = _load_prompt_config(domain, name, version)
    template = _jinja_env.from_string(config["template"])
    rendered = template.render(**variables)
    return rendered, config.get("model", {})


def get_system_prompt(
    agent: str,
    *,
    version: str = "v1",
) -> str:
    """Load a system prompt markdown file."""
    path = PROMPTS_DIR / agent / version / "system.md"
    if not path.exists():
        raise PromptNotFoundError(f"System prompt not found: {path}")
    with open(path) as f:
        return f.read()
```

### 5.2 Extract RAG System Prompt

**From:** `rag_agent.py:33` (34-line inline string)

**To:** `backend/src/rag_backend/agents/prompts/rag/v1/system.md`

```markdown
---
name: rag-system
version: "1.0.0"
---

# RAG Agent System Prompt

You are a helpful AI assistant with access to a knowledge base.

## Response Guidelines

1. First, search the knowledge base using the `search_documents` tool
2. Use the retrieved information to provide accurate, contextual answers
3. Cite your sources when providing information from documents
4. If you don't find relevant information, say so clearly
5. Always be helpful, accurate, and concise

## Carousel & Content Generation

You can also create Instagram carousels and blog content. When a user asks to
create a carousel, social media post, or blog content, use the `generate_carousel`
tool to trigger the full 7-phase content generation pipeline.

## Copy Refinement

When a user asks to tweak, shorten, rewrite, or otherwise refine copy on an
existing carousel, call `refine_carousel_copy`. Extract the project UUID from
the UI prefix `(carousel project_id=<uuid>)` and pass it as `project_id`.

Supported targets:
- `instagram_caption`
- `linkedin_post_pt`
- `linkedin_post_en`
- `slide_heading:N` (or `:pt` / `:en` suffix)
- `slide_body:N` (or `:pt` / `:en` suffix)

Slide-text edits trigger automatic re-export of slide JPGs and PDF in the
touched language. Do not regenerate the whole carousel for minor edits.

## Image Regeneration

When a user asks to change or regenerate an image on a carousel slide, call
`regenerate_slide_image` with the slide number and a natural-language instruction.

## Design Refinement

When a user asks to change layout, sizing, spacing, fonts, or any visual CSS
property, call `refine_carousel_design` with a natural-language instruction.
```

### 5.3 Extract Carousel Prompts

**From:** `carousel_template.py` (title, content, caption builders)

**To:** `backend/src/rag_backend/agents/prompts/carousel/v1/`

Example: `title_prompt.yaml`
```yaml
name: carousel_title
version: "1.0.0"
description: "Optimize carousel title/subtitle based on research context"

template: |
  You are a social media content strategist.

  Given the carousel topic "{{ topic }}" and the following research context,
  generate an engaging title and subtitle in PT-BR with an English translation.

  Research context:
  {{ research_context }}

  Return ONLY valid JSON in this exact shape:
  {
    "title_pt": "...",
    "title_en": "...",
    "subtitle_pt": "...",
    "subtitle_en": "..."
  }

model:
  temperature: 0.7
  max_tokens: 512
```

### 5.4 Extract Refinement Prompts

**From:** `rag_agent_tools.py:174`, `carousel_refinement.py`

**To:** `backend/src/rag_backend/agents/prompts/refinement/v1/`

---

## 6. Phase 2: Tool Registry Refactor

### 6.1 Extract Knowledge Base Tools

**From:** `rag_agent.py:113-149` (inline `@tool` functions)

**To:** `backend/src/rag_backend/application/tools/knowledge_base/search_documents.py`

```python
"""Search documents tool for the RAG agent."""

from langchain_core.tools import tool

from rag_backend.domain.models import DocumentStatus, RetrievalQuery
from rag_backend.domain.protocols import DocumentRepository, Retriever


@tool
async def search_documents(
    query: str,
    *,
    retriever: Retriever,
    top_k: int = 5,
) -> str:
    """Search the knowledge base for relevant information.

    Use this tool when you need to find specific information
    from the uploaded documents.

    Args:
        query: The search query string
        top_k: Number of results to return (default: 5)
    """
    results = await retriever.retrieve(RetrievalQuery(query=query, top_k=top_k))
    if not results:
        return "No relevant documents found."

    formatted = []
    for i, result in enumerate(results, 1):
        snippet = result.content[:300]
        formatted.append(f"[{i}] {snippet}... (Score: {result.score:.3f})")

    return "\n\n".join(formatted)
```

**Key change:** Tools receive dependencies via **explicit keyword arguments** instead of closures. The agent assembles the partial function at runtime:

```python
from functools import partial

# In RAGAgent.__init__:
self._tools = [
    partial(search_documents, retriever=self._retriever, top_k=5),
    partial(list_documents, repository=self._document_repository),
]
```

### 6.2 Extract Carousel Tools

**From:** `rag_agent_tools.py` (3 factory functions, 297 lines)

**To:** Individual files in `backend/src/rag_backend/application/tools/carousel/`

| Factory | New File |
|---------|----------|
| `build_refine_carousel_copy_tool` | `tools/carousel/refine_copy.py` |
| `build_regenerate_slide_image_tool` | `tools/carousel/regenerate_image.py` |
| `build_refine_carousel_design_tool` | `tools/carousel/refine_design.py` |
| `generate_carousel` (inline) | `tools/carousel/generate_carousel.py` |

### 6.3 Tool Registry

**File:** `backend/src/rag_backend/application/tools/registry.py`

```python
"""Tool discovery and registration."""

from collections.abc import Callable
from typing import Any

from langchain_core.tools import BaseTool, tool

# Auto-discover all @tool-decorated functions in subpackages
# and expose them via domain-scoped registries.

ToolFactory = Callable[..., BaseTool]


class ToolRegistry:
    """Registry for agent tools organized by domain."""

    def __init__(self) -> None:
        self._tools: dict[str, list[BaseTool]] = {}

    def register(self, domain: str, *tools: BaseTool) -> None:
        """Register one or more tools under a domain namespace."""
        self._tools.setdefault(domain, []).extend(tools)

    def get_domain(self, domain: str) -> list[BaseTool]:
        """Return all tools in a domain."""
        return list(self._tools.get(domain, []))

    def get_all(self) -> list[BaseTool]:
        """Return all registered tools."""
        return [t for tools in self._tools.values() for t in tools]
```

---

## 7. Phase 3: Agent Reclassification

### 7.1 Rename and Relocate

| Current | Target | Rationale |
|---------|--------|-----------|
| `services/rag_agent.py` | `agents/rag_agent.py` | Agent is an orchestrator, not a service |
| `services/carousel_agent.py` | `agents/carousel_orchestrator.py` | "Orchestrator" is the LangGraph term; "agent" is overloaded |
| `domain/protocols.py: CarouselAgent` | `domain/protocols.py: CarouselOrchestrator` | Protocol name matches implementation |

### 7.2 What Stays in `/services`

Services are **business logic** — they do things, they don't decide things:

- `carousel_template.py` — HTML template building (stays, but delegates prompt rendering to registry)
- `carousel_refinement.py` — Copy/design refinement logic (stays, but delegates prompt rendering)
- `document_pipeline.py` — Document processing pipeline
- `conversation_service.py` — Conversation CRUD + history management
- `linkedin_post_generator.py` — LinkedIn post generation
- `pdf_slide_builder.py` — PDF assembly

### 7.3 What Moves to `/agents`

Agents are **orchestration frameworks** — they decide what to do and in what order:

- `rag_agent.py` — Chat agent with tool selection
- `carousel_orchestrator.py` — LangGraph pipeline orchestrator
- `prompts/` — All prompt templates

---

## 8. Phase 4: LangGraph Subgraph Decomposition

### 8.1 Current: Monolithic Graph

```python
# graph.py — 415 lines, all phases in one StateGraph
graph = StateGraph(PipelineState)
graph.add_node(NODE_RESEARCH, research_node)
graph.add_node(NODE_CONTENT, content_node)
# ... 9 more nodes
```

### 8.2 Target: Subgraph-per-Phase

```
backend/src/rag_backend/application/services/carousel/
├── graph.py              # Parent orchestrator (wires subgraphs)
├── state.py              # Shared state schema
├── types.py              # Domain types
├── nodes/                # Leaf nodes (pure functions)
│   └── ...
└── phases/               # NEW — One subgraph per phase
    ├── research/
    │   ├── state.py      # ResearchPhaseState
    │   ├── nodes.py      # research_node (pure function)
    │   └── graph.py      # build_research_graph()
    ├── content/
    │   ├── state.py
    │   ├── nodes.py
    │   └── graph.py
    ├── images/
    │   ├── state.py
    │   ├── nodes.py
    │   └── graph.py      # Send fan-out lives here
    ├── export/
    │   ├── state.py
    │   ├── nodes.py
    │   └── graph.py
    └── ...
```

### 8.3 Parent Orchestrator

**File:** `carousel/graph.py` (refactored to ~150 lines)

```python
"""Parent orchestrator: wires phase subgraphs into the full pipeline."""

from langgraph.graph import END, START, StateGraph

from rag_backend.application.services.carousel.phases.content.graph import (
    build_content_graph,
)
from rag_backend.application.services.carousel.phases.export.graph import (
    build_export_graph,
)
from rag_backend.application.services.carousel.phases.images.graph import (
    build_images_graph,
)
from rag_backend.application.services.carousel.phases.research.graph import (
    build_research_graph,
)
from rag_backend.application.services.carousel.state import PipelineState


def build_graph(deps, *, checkpointer=None):
    """Compile the carousel pipeline from phase subgraphs."""
    graph = StateGraph(PipelineState)

    # Each phase is a compiled subgraph with its own state namespace
    graph.add_node("research", build_research_graph(deps))
    graph.add_node("content", build_content_graph(deps))
    graph.add_node("images", build_images_graph(deps))
    graph.add_node("export", build_export_graph(deps))
    # ... etc

    graph.add_edge(START, "research")
    graph.add_edge("research", "content")
    graph.add_edge("content", "images")
    graph.add_edge("images", "export")
    graph.add_edge("export", END)

    return graph.compile(checkpointer=checkpointer)
```

### 8.4 Benefits

| Benefit | How |
|---------|-----|
| **Namespace isolation** | Each phase has its own `State` TypedDict |
| **Independent checkpointing** | Resume restarts at phase boundaries, not super-steps |
| **Reusability** | `build_research_graph()` can be used in other pipelines |
| **Team ownership** | Different developers own different phase folders |
| **Testability** | Test each subgraph in isolation |

---

## 9. Phase 5: Deep Agents Alignment

### 9.1 Adopt Skill-Based Prompt Composition

> **Updated (ADR-007):** Carousel generation is consolidated under the editorial workflow orchestrator (`CarouselEditorialOrchestrator`). The legacy `agents/carousel_orchestrator/` package remains only for refinement tools (copy/design/image) until CP-024 completes full removal. Runtime prompts for editorial phases live under `agents/prompts/carousel/`; canonical human-readable standards live under `skills/carousel-pipeline/_shared/` and `phases/`.

**Current:** Single monolithic `SYSTEM_PROMPT` string.

**Target:** Decompose into `AGENTS.md` + skill files. The project already has a Deep Agents skill at `skills/carousel-pipeline/SKILL.md` — this stays as the canonical location.

```
skills/                          # Deep Agents skills (project root — stays)
├── carousel-pipeline/
│   ├── SKILL.md                 # 7-phase pipeline skill (existing — keep)
│   ├── bmad-skill-manifest.yaml # Manifest (existing)
│   └── workflow.md              # Workflow (existing)
├── carousel-refinement/         # NEW — Copy/design/image refinement skill
│   └── SKILL.md
└── knowledge-base/              # NEW — Retrieval & search skill
    └── SKILL.md

backend/src/rag_backend/agents/
├── AGENTS.md                    # NEW — Persistent agent memory (always loaded)
│   # Project conventions: Clean Architecture, type safety, API patterns, etc.
└── ...                          # Prompts registry, agent implementations
```

**Why keep `skills/` at the project root?** Deep Agents loads skills by filesystem path. The existing `skills/carousel-pipeline/` is already referenced by the BMAD skill manifest and potentially by agent runtime configuration. Moving it would break existing integrations. The `backend/src/rag_backend/agents/prompts/` directory is for **runtime prompt templates** (title, content, caption prompts that are rendered with Jinja2 and sent to the LLM). The `skills/` directory is for **agent behavior instructions** (the skill frontmatter + instructions that Deep Agents assembles into the system prompt stack). These are different concerns with different consumers.

### 9.2 Adopt ToolRuntime for DI

**Current:** Tools use closure-captured dependencies.

**Target:** Tools receive runtime context through `ToolRuntime`.

```python
from dataclasses import dataclass
from langchain_core.tools import tool, ToolRuntime

@dataclass
class AgentContext:
    retriever: Retriever
    repository: DocumentRepository
    carousel_orchestrator: CarouselOrchestrator | None = None

@tool
async def search_documents(query: str, runtime: ToolRuntime[AgentContext]) -> str:
    """Search the knowledge base."""
    results = await runtime.context.retriever.retrieve(...)
    return format_results(results)
```

### 9.3 Use Subagents for Context Isolation

**Current:** `RAGAgent` has 6 tools in one flat list.

**Target:** Delegate carousel work to a carousel subagent.

```python
from deepagents import create_deep_agent, CompiledSubAgent

# Carousel subagent (isolated context)
carousel_subagent = CompiledSubAgent(
    name="carousel-creator",
    description="Specialized in creating and refining Instagram carousels",
    runnable=carousel_orchestrator,  # The LangGraph pipeline
)

# Main RAG agent delegates carousel requests to subagent
rag_agent = create_deep_agent(
    model=llm,
    tools=[search_documents, list_documents],  # KB tools only
    subagents=[carousel_subagent],             # Carousel work delegated
    system_prompt=load_prompt("rag", "system"),
)
```

**Benefits:**
- Main agent focuses on retrieval + conversation
- Carousel subagent has its own system prompt and toolset
- Token efficiency — carousel instructions only loaded when needed
- Security — carousel tools are not visible to general queries

---

## 10. Migration Strategy

### Phase 1: Prompt Externalization (Low Risk)

1. Create `agents/prompts/` directory structure
2. Extract each hardcoded prompt to a YAML file
3. Create `prompts/registry.py` with loader
4. Refactor callers to use `render_prompt()` / `get_system_prompt()`
5. **Validation:** All existing tests pass; prompt output is byte-identical

**Effort:** 2-3 days
**Risk:** Low — pure refactoring, no behavior change
**Rollback:** Revert to inline strings

### Phase 2: Tool Extraction (Low-Medium Risk)

1. Create `application/tools/` directory structure
2. Move each inline tool to its own module
3. Replace closure-based DI with `partial()` or `ToolRuntime`
4. Create `tools/registry.py`
5. Update `RAGAgent` to use registry
6. **Validation:** All existing tests pass; tool behavior unchanged

**Effort:** 3-4 days
**Risk:** Low-Medium — file moves, import updates
**Rollback:** Restore original files

### Phase 3: Agent Relocation (Low Risk)

1. Create `agents/` directory
2. Move `rag_agent.py` and `carousel_agent.py`
3. Update all imports in API routes, DI container, tests
4. Rename `CarouselAgent` → `CarouselOrchestrator` in protocols
5. **Validation:** All tests pass; app starts successfully

**Effort:** 1-2 days
**Risk:** Low — mechanical moves
**Rollback:** Restore original paths

### Phase 4: Subgraph Decomposition (Medium Risk)

1. Create `carousel/phases/` directory structure
2. Extract each phase's nodes + state into a subgraph module
3. Refactor `build_graph()` to wire subgraphs
4. Migrate closure-scoped shared state (`progress_lock`, `slide_status_box`) to state reducers
5. **Validation:** Integration tests pass; checkpoint resume works

**Effort:** 5-7 days
**Risk:** Medium — changes checkpoint format, affects resume behavior
**Rollback:** Restore monolithic graph

### Phase 5: Deep Agents Alignment (Medium-High Risk)

1. Create `AGENTS.md` and `skills/` files
2. Refactor `RAGAgent` to use `create_deep_agent()` with subagents
3. Adopt `ToolRuntime` for dependency injection
4. Add middleware for logging/rate limiting
5. **Validation:** E2E tests pass; streaming works; tool calls work

**Effort:** 4-5 days
**Risk:** Medium-High — changes agent runtime behavior
**Rollback:** Restore previous agent implementation

### Total Effort Estimate

| Phase | Days | Risk | Parallelizable |
|-------|------|------|----------------|
| 1. Prompts | 2-3 | Low | With Phase 2 |
| 2. Tools | 3-4 | Low-Med | With Phase 1 |
| 3. Relocation | 1-2 | Low | After Phases 1-2 |
| 4. Subgraphs | 5-7 | Medium | After Phase 3 |
| 5. Deep Agents | 4-5 | Med-High | After Phase 4 |
| **Total** | **15-21** | | |

---

## 11. Decision Records

### Why not keep agents in `/services`?

In Clean Architecture, "services" implement business rules and use cases. Agents are **orchestration frameworks** — they use tools and services, but they don't contain business logic themselves. Placing them in `/services` conflates "business logic" with "decision framework", making the architecture harder to reason about and violating the Single Responsibility Principle.

### Why YAML + Markdown for prompts instead of database?

For the current scale (8 prompts, 2-3 developers), a database adds operational complexity without proportional value. YAML files provide:
- Git history and PR reviews for prompt changes
- No runtime dependencies
- Easy local development and testing
- Simple migration path to database later if scale demands it

### Why Jinja2 instead of f-strings or LangChain PromptTemplate?

Jinja2 is the industry standard for prompt templating (used by PromptLayer, PromptFlow, Dify). It supports:
- Conditionals (`{% if %}`)
- Loops (`{% for %}`)
- Includes (`{% include %}`)
- Filters (`| default(...)`)

LangChain `PromptTemplate` is less flexible and couples us to the LangChain ecosystem. F-strings have no caching and are prone to injection.

### Why subgraph decomposition instead of keeping the monolith?

The monolithic graph works today, but as the pipeline grows (more phases, more conditional branches), it becomes:
- Harder to test (must invoke entire graph to test one phase)
- Harder to debug (checkpoints are super-step granularity)
- Harder to reuse (cannot use research phase in another pipeline)

Subgraphs provide namespace isolation and per-phase checkpointing with minimal overhead.

### Why explicit `partial()` DI instead of closures?

Closure-based DI (capturing `self._retriever` in a nested function) makes tools:
- Harder to test (must instantiate the agent to test the tool)
- Harder to reuse (tool is bound to a specific agent instance)
- Opaque to introspection (dependencies are hidden in closure cells)

Explicit `partial()` makes dependencies visible at the call site and enables testing tools in isolation.

### Why keep `skills/` at the project root instead of moving to `agents/skills/`?

The project already has a working Deep Agents skill at `skills/carousel-pipeline/SKILL.md` with a BMAD skill manifest. Deep Agents loads skills by filesystem path — moving the directory would break existing integrations and the skill manifest references. The distinction is:

- **`skills/`** — Deep Agents behavior instructions (SKILL.md frontmatter + instructions assembled into the system prompt stack by the agent framework)
- **`agents/prompts/`** — Runtime prompt templates rendered with Jinja2 and sent directly to the LLM API (title prompts, content prompts, etc.)

These are different concerns with different consumers. The skill tells the agent *what it can do*; the prompt template tells the LLM *what to generate*.

---

## Appendix: References

| Resource | URL |
|----------|-----|
| Deep Agents Overview | https://docs.langchain.com/oss/python/deepagents/overview |
| Deep Agents Subagents | https://docs.langchain.com/oss/python/deepagents/subagents |
| LangGraph Subgraphs | https://docs.langchain.com/oss/python/langgraph/use-subgraphs |
| LangGraph Functional API | https://docs.langchain.com/oss/python/langgraph/functional-api |
| LangGraph Persistence | https://docs.langchain.com/oss/python/langgraph/persistence |
| Production Cookiecutter | https://github.com/hugoromerorico/production-agent-cookiecutter-langgraph |
| Prompt Management Guide | Hamilton / Weights & Biases best practices |
| AGENTS.md Spec | https://agents.md/ |
| Promptfoo (Evaluation) | https://promptfoo.dev/ |
