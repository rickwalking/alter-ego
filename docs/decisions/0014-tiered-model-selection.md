# ADR-0014: Tiered Model Selection — DeepSeek for research/scoring, Claude for the voice surface

## Status

Proposed

> Supersedes the "ADR-019" label used informally in the restructure epic
> (`docs/plans/agent-architecture-restructure-epic.md` RES-2) and arch-plan §13 —
> renumbered to 0014 to follow the live ADR sequence.

## Context

The carousel/blog pipeline currently runs every phase on Claude Sonnet (one model
seam: `agents/carousel_editorial_orchestrator.py` ← `container.llm_service().chat_model`).
Several phases are token-heavy and **low-voice** (research/source synthesis,
rubric scoring) — paying Claude rates there is poor cost efficiency. DeepSeek
(`deepseek-chat`-class) is materially cheaper and adequate for extraction/scoring,
but **must never touch the voice surface** (content draft, caption, LinkedIn,
persona enforce/gate), where a quality regression fails the ≥70 persona gate =
product failure.

A model-selection mechanism that silently degrades is dangerous: the skeptical pass
(`.agent/reports/agent-architecture.skeptical-corrections.md` §4) flagged that using
`.with_fallbacks([claude])` as the **tier boundary** makes cost + quality
**unmonitorable** (you pay DeepSeek *and* Claude on every degradation) and yields a
**circular quality signal** (Claude grading Claude). The decision below rejects that
pattern explicitly.

### Verified constraint

`agents/source_synthesis_agent.py` parses model output as JSON and **hard-fails**
on malformed output: `extract_json(raw)` at `:57`, then `raise ValueError(ERR_INVALID_JSON)`
at `:59` and `raise TypeError(ERR_INVALID_JSON)` at `:61` — there is **no graceful
degrade**. DeepSeek's JSON/structured-output fidelity through any chosen endpoint is
therefore a hard correctness dependency: a phase cannot be committed to DeepSeek
without an integration test proving JSON (and tool-calling, where used) survives the
endpoint.

## Decision Drivers

- Cost reduction on low-voice, token-heavy phases.
- **Zero voice regression** — Claude stays on every voice-bearing phase.
- **Observable** cost + quality — the tier mechanism must be visible, not silent.
- JSON/structured-output correctness through whatever endpoint is chosen
  (`source_synthesis_agent.py:57-61` hard-fails `ERR_INVALID_JSON`).
- Persona quality bar (≥70) is the non-negotiable gate.

## Considered Options

### Option A — Deterministic phase→model map, chosen BEFORE invocation (RECOMMENDED)

A static map (phase/agent → primary model) resolved at orchestrator construction.
The model is **selected before the call** and **logged** with a Langfuse
`model_provider` + primary/fallback tag. DeepSeek failures take an **explicit,
counted error/escalation path** (logged, observable) — not an invisible fallback.

- **Pros:** cost + quality fully attributable per phase; no circular quality signal;
  the fallback rate is observable (a high rate means DeepSeek isn't earning its place);
  the voice/cheap boundary is enforced by *where the model is injected*, auditable in
  the map itself.
- **Cons:** a DeepSeek hard-failure surfaces as an explicit error/escalation that must
  be handled (vs silently masked) — this is the intended trade-off.

### Option B — `.with_fallbacks([claude])` as the tier boundary (REJECTED)

DeepSeek primary, Claude as a LangChain runtime fallback that fires on DeepSeek error.

- **Why rejected:** cost becomes unmonitorable (DeepSeek + Claude billed on every
  degradation); the quality signal is circular (Claude silently grading/repairing
  Claude); the actual DeepSeek failure rate is invisible, so you can't tell whether
  the cheap tier is even working. This is the exact anti-pattern the skeptical pass
  called out. **A separate, explicit, logged escalation path on DeepSeek failure is
  fine — it is just not the invisible tier mechanism.**

### Option C — Single model everywhere (status quo)

Keep Claude on all phases.

- **Why rejected:** leaves the cost savings on low-voice phases unrealized; the whole
  point of the tier.

## Decision

**Adopt Option A — a deterministic phase→model map chosen before invocation,**
carried in the harness config (ADR-0015 `DeepAgentConfig` per-role model map). The
carousel exposes exactly one model seam, so per-phase selection is additive wiring,
not a topology change.

**Phase placement:**

| Phase / agent | Model | Status |
|---|---|---|
| `SourceSynthesisAgent` (research / extraction) | **DeepSeek** | **COMMITTED pilot** — token-heavy, low-voice |
| `QualityAgent` (rubric / scoring) | **DeepSeek** | **Candidate** — pilot only AFTER its prompt is on the registry (Phase 1), so a cheap model is never baked onto an off-registry prompt |
| `ContentDraftAgent` (slide copy) | **Claude Sonnet** | KEEP — voice surface |
| caption / LinkedIn export | **Claude Sonnet** | KEEP — voice + platform rules |
| Persona enforce + persona **gate** | **Claude Sonnet** | KEEP — never offload the thing that guards voice |

**Hard rules:**

1. **Reject `.with_fallbacks([claude])` as the tier boundary** (Option B). DeepSeek
   failure takes an explicit, logged, *counted* escalation path; the tier itself is
   the deterministic map.
2. **Langfuse tagging is mandatory** — every call tagged `model_provider` +
   primary/fallback flag, so cost attribution and the real fallback rate are
   observable.
3. **A/B quality-parity check vs the ≥70 persona gate MUST precede committing any
   phase to DeepSeek** in prod. Run a documented A/B (DeepSeek vs Claude on that
   phase against the persona/quality bar); commit only if parity holds.
4. **Mandatory JSON/tool-calling integration test through the chosen endpoint**
   before committing a phase — `source_synthesis_agent.py:57-61` hard-fails
   `ERR_INVALID_JSON` with no graceful degrade. Pin `deepseek-chat`-class models
   (the reasoner has no tool-calling/structured-output).

**Sourcing:**

- **Pilot / dev:** opencode **Zen "Go"** gateway — `https://opencode.ai/zen/go/v1`,
  models `deepseek-v4-flash` (research) / `deepseek-v4-pro` (scoring), via
  `ChatOpenAI(base_url=…)` (user holds the subscription). Langfuse tracing unaffected.
  (Model IDs are post-cutoff — re-confirm at implementation.)
- **Production sourcing = OPEN DECISION.** opencode Zen (pending **ToS / SLA /
  data-residency** review for routing user content through a third-party gateway)
  **vs** direct DeepSeek API (`https://api.deepseek.com`). Not mandated here.

## Consequences

**Good:**

- Cost dropped on low-voice phases with the voice surface fully protected.
- Cost + quality + fallback rate are observable per phase (Langfuse tags), so the
  cheap tier is held accountable.
- No circular quality signal; the boundary is auditable in the phase→model map.

**Bad / constraints:**

- DeepSeek hard-failures surface as explicit errors/escalations to handle (intended).
- Each phase committed to DeepSeek owes an A/B parity run + a JSON/tool-calling
  integration test — added pre-commit work per phase.
- Production sourcing remains an open governance decision (Zen ToS/SLA/residency vs
  direct API) that must close before any prod promotion.

## Related Decisions

- ADR-0015: Deep Agents harness (carries the per-role model map in `DeepAgentConfig`).
- ADR-003: Persona-Driven AI Content (the ≥70 voice gate this ADR protects).
- ADR-007: Consolidate Carousel Pipelines under DeepAgents (the single model seam).

## Open Questions (for human before proposed → accepted)

- **Production DeepSeek sourcing:** opencode Zen (ToS/SLA/data-residency review
  pending) vs direct `api.deepseek.com`. Must close before promoting any pilot phase
  to prod.

## Tags

#agents #models #deepseek #cost #observability #langfuse #persona
