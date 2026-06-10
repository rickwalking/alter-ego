# Carousel Pipeline Shared Standards

Canonical behavior specifications for carousel content quality. Extracted from the legacy monolith (`SKILL.md` + `workflow.md`) during CP-001 migration.

## Three-layer alignment

When carousel standards change, update in this order:

| Layer | Path | Role | Update order |
|-------|------|------|--------------|
| **Skills** | `skills/carousel-pipeline/_shared/` | Human-readable canonical spec for Deep Agent subagents, developers, QA | **First** — source of truth |
| **Prompts** | `backend/src/rag_backend/agents/prompts/carousel/v1/` | Runtime Jinja2/YAML templates sent to LLMs | **Second** — must reflect `_shared/` contracts |
| **Code** | Python agents, validators, HTML renderers, `CarouselTemplateBuilder` | Execution and enforcement | **Third** — enforce contracts in code |

Skills instruct **what** good output looks like. Prompts **parameterize** LLM calls. Python **produces and validates** output. None replaces the others.

## File index

| File | Contents |
|------|----------|
| [`critical-rules.md`](critical-rules.md) | Language, fact-checking, bilingual storage, fail-loudly, user sources authoritative, prerequisites |
| [`anti-patterns.md`](anti-patterns.md) | Symptom / root cause / fix table from production failures |
| [`content-contracts.md`](content-contracts.md) | JSON return shape, slide types, `features`/`stats`/`insight`, tool vocabulary |
| [`text-formatting.md`](text-formatting.md) | Em-dash ban, `**bold**` vs `` `code` ``, heading accent highlights |
| [`design-system.md`](design-system.md) | Theme palettes, brand detection, token schema, typography, layout CSS |
| [`image-generation.md`](image-generation.md) | Scene-only `image_prompt`, Gemini wrapper, slide scope, rate limiting |
| [`export-and-caption.md`](export-and-caption.md) | Playwright 1080×1350 export, caption structure, blog rules, API endpoints |

## Phase skill loading (progressive disclosure)

Each phase subagent loads **one phase skill** plus **only the `_shared/` files it needs**:

| Subagent / node | Phase skill | Shared standards loaded |
|-----------------|-------------|-------------------------|
| `research_synthesizer` | `phases/research` | critical-rules, anti-patterns |
| `outline_planner` | `phases/outline` | critical-rules, text-formatting |
| `content_drafter` | `phases/content` | content-contracts, text-formatting, anti-patterns |
| `apply_design` | `phases/design` | design-system |
| `render_images` | `phases/images` | image-generation |
| `compose_blog` + `score_quality` | `phases/final-review` | export-and-caption, content-contracts |

Parent agents (`RAGAgent`) do **not** load the full carousel skill stack — they delegate via `task` to phase subagents.

## Related docs

- [ADR-007: Consolidate Carousel Pipelines Under DeepAgents](../../../docs/decisions/0007-consolidate-carousel-pipelines-under-deepagents.md)
- [Carousel Pipeline Consolidation Plan](../../../docs/plans/carousel-pipeline-consolidation.md)
