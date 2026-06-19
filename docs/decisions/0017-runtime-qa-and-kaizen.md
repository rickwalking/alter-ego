# ADR-0017: Best-Effort Runtime Product-QA Subagent + Runtime Kaizen Channel

## Status

Proposed

## Context

There is no runtime/product QA of generated carousels today. `quality_agent.py`
scores *text* against a rubric; Playwright exists only for **export geometry**
(`infrastructure/external/playwright_export.py`, `playwright_geometry.py`), not for
QA navigation. The delivery-side improvement loop (`/handoff` →
`learnings-log.jsonl` → `/kaizen-skill`) exists for **code-delivery** sessions only —
there is no runtime/product equivalent.

The human chose "QA every generation". The skeptical pass
(`.agent/reports/agent-architecture.skeptical-corrections.md` §5) required that this
be **best-effort / non-blocking**: droplet Chromium crashes have precedent (the
`InMemorySaver` fallback at `bootstrap/app_factory.py:167` exists for exactly this
class of environment fragility), and a QA failure must never fail the user's
generation.

## Decision Drivers

- Full signal (every generation) without risking the user's generation.
- Crash-safety on a fragile droplet (Playwright can hang/crash).
- Cost awareness — an LLM-scored reviewer roughly doubles per-generation model cost.
- A runtime improvement channel distinct from the delivery kaizen loop (different
  targets: content standards/prompts vs CI gates/CLAUDE.md).

## Decision

**Add a `qa_reviewer` subagent that QAs rendered carousels, every generation, as a
best-effort / non-blocking step**, and a **runtime kaizen channel** parallel to the
delivery loop.

**`qa_reviewer` contract (hard requirements):**

- **Non-blocking:** runs **after** the generation completes and the artifact is
  delivered; the report attaches post-generation (side table / async channel),
  **never** on the response critical path.
- **Crash-safe:** any Playwright crash/hang/timeout is **swallowed** — record a
  "QA-unavailable" marker and move on. A QA failure can **never** fail a generation
  (precedent: the `app_factory.py:167` `InMemorySaver` fallback).
- **Side-table reporting:** write the structured report to a dedicated side table
  (e.g. `carousel_qa_reports`, keyed by `project_id`) + the runtime learnings log.
  Do **not** mutate the carousel record's success state.
- **Tools:** Playwright MCP (`browser_navigate`, `browser_snapshot`,
  `browser_take_screenshot`) + a `report` tool writing the structured artifact.
- **Boundary:** strictly separate from `skills/delivery/qa-agent` (that validates
  *code*; this validates *generated artifacts*). Named `qa_reviewer` to avoid
  confusion.
- **Report scope (explicit):** minimum = screenshot + DOM snapshot + rule-checks
  (design-system / anti-patterns / caption-rules). An **LLM-scored** qualitative
  reviewer is **optional** and roughly **doubles per-generation cost** — gate it
  separately from the cheap screenshot/DOM/rule pass.
- **Cadence:** ship "every generation" first to gather a baseline; **reconsider a
  sampled cadence after a baseline week** if cost/latency/volume warrant (a follow-up
  review, not a blocker).

**Runtime kaizen channel (parallel, not merged):**

- On generation completion, emit a structured run summary (brief, phases, revisions,
  the `qa_reviewer` report) to a **separate** `.agent/handoff/runtime-learnings-log.jsonl`
  (keeps product signal distinct from delivery signal).
- A runtime variant of `kaizen-skill` mines that log → proposes improvements to
  **content standards / prompts** (`_shared/*.md`, `agents/prompts/*`), persona
  forbidden-phrases, subagent instructions — **human-approved** before any change.
- **Why parallel, not unified:** delivery kaizen mutates lint rules/CI gates/CLAUDE.md;
  runtime kaizen mutates content standards/prompts. Same shape, different targets;
  sharing the JSONL would pollute both. Reuse the `kaizen-skill` engine, swap the
  input log + emission catalog.

## Consequences

**Good:**

- Every generation gets QA signal without ever risking the user's generation.
- Crash-safety matches the droplet's known fragility.
- A runtime improvement loop closes ADR-003's feedback loop at the *standards* level,
  complementing `FeedbackLearningLoop` (per-correction level).

**Bad / constraints:**

- The optional LLM-scored reviewer ~doubles per-generation cost — must be gated
  separately and justified.
- A second kaizen channel may not accumulate enough signal for a single-user product
  — may start as manual review of QA reports; formalize the loop only if volume
  warrants.
- A new side table (`carousel_qa_reports`) requires a migration (ADR-012).

## Related Decisions

- ADR-003 (Persona-Driven AI Content — feedback loop this extends).
- ADR-007 (deterministic carousel nodes; `qa_reviewer` runs as a post-final-review node).
- ADR-0016 (skill/tool contract; the `report` tool is an adapter).
- ADR-008 (Agentic Delivery — the delivery kaizen loop this parallels).

## Open Questions (for human before proposed → accepted)

- Whether to ship the LLM-scored qualitative reviewer in v1 (cost) or only the cheap
  screenshot/DOM/rule pass.
- Whether a second (runtime) kaizen channel is justified now for a single-user
  product, or deferred to manual QA-report review until volume warrants.

## Tags

#agents #runtime-qa #playwright #kaizen #non-blocking #observability
