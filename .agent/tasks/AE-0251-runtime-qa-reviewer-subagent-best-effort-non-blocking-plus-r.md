# AE-0251 — Runtime qa_reviewer subagent (best-effort, non-blocking) plus runtime kaizen channel

Status: Intake
Tier: T2
Priority: High
Type: Feature
Area: backend
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: TBD
Kanban Card: TBD
Created: 2026-06-18
Updated: 2026-06-18

## Goal

Add a runtime `qa_reviewer` subagent that drives Playwright to QA a rendered carousel
after generation — **best-effort and non-blocking**, writing its report to a side table
and never failing the user's generation — plus a runtime kaizen channel
(`runtime-learnings-log.jsonl`) that mines those reports into human-approved standards
improvements.

## Problem

There is **no runtime/product QA** of generated carousels: `quality_agent.py` scores
*text* only, and Playwright is used only for export geometry, not QA navigation
(arch-plan §7.1). The human chose "QA every generation", but the skeptical pass required
it be **best-effort / non-blocking**: droplet Chromium crashes have precedent (the
`InMemorySaver` fallback at `app_factory.py:167` exists for exactly this fragility), so
a Playwright crash/timeout must NOT fail the user's generation. Separately, the
delivery-side improvement loop (`/handoff` → `learnings-log.jsonl` → `/kaizen-skill`)
has **no runtime/product equivalent** — runtime QA signal has nowhere to accumulate.

Evidence: arch-plan §7.2/§7.3 (best-effort/non-blocking contract; side table) + §6.2
(runtime kaizen channel); ADR-0017; skeptical-corrections.md §5.

## Scope

- A `qa_reviewer` subagent / final deterministic node that, after the carousel renders,
  drives Playwright MCP (`browser_navigate`, `browser_snapshot`,
  `browser_take_screenshot`) to inspect each slide and produce a structured report:
  design-system/anti-pattern/caption-rule checks (cheap pass) + optional LLM-scored
  qualitative review (gated separately — roughly doubles per-gen cost).
- A `carousel_qa_reports` side table keyed by `project_id` for the report.
- A `report` tool that writes the structured QA artifact + appends a run summary to
  `.agent/handoff/runtime-learnings-log.jsonl` (separate from the delivery
  `learnings-log.jsonl`).
- A thin `kaizen-skill` runtime variant that mines `runtime-learnings-log.jsonl` →
  proposes prompt/skill/persona-standard improvements (human-approved).

## Non-Goals

- The QA report MUST NOT be on the critical path — it attaches **post-generation**; do
  not block or fail the user's generation on QA outcome.
- Do not merge runtime and delivery learnings logs (separate files keep signal distinct,
  arch-plan §6.2).
- Do not auto-apply any kaizen proposal — human approval is required (ADR-0017).
- Do not reuse the delivery `qa-agent` (that validates *code*; this validates *generated
  artifacts*) — name it `qa_reviewer`/`impeccable` to avoid confusion.
- The LLM-scored qualitative pass is optional and separately gated (cost).

## Acceptance Criteria

- [ ] `qa_reviewer` runs **after** the artifact is delivered to the user; the QA report
      is written to the `carousel_qa_reports` side table keyed by `project_id` and never
      mutates the carousel record's success state.
- [ ] **Crash-safe:** a Playwright crash/hang/timeout is swallowed — the QA node records
      a "QA-unavailable" marker and the generation succeeds regardless. A test injects a
      Playwright failure and asserts the generation still succeeds.
- [ ] The cheap pass (screenshot + DOM snapshot + design-system/anti-pattern/caption
      rule checks) always runs; the LLM-scored qualitative pass is behind a separate
      flag (cost-gated).
- [ ] A run summary (brief, phases, revisions, QA report) is appended to
      `runtime-learnings-log.jsonl` (separate from the delivery log).
- [ ] A runtime `kaizen` variant mines that log and emits **human-approved** proposals
      (no auto-apply); proven by a unit test of the mine→propose path.
- [ ] Backend `pytest`/`mypy`/`ruff` green.

## Gherkin Scenarios

> Behavior-changing (new runtime QA + a new persistence side table + a learnings
> channel), so a `.feature` IS required — happy + edge + failure (the non-blocking
> guarantee is the load-bearing failure scenario).

```gherkin
Feature: Best-effort runtime QA never fails a generation

  Scenario: QA runs after a successful generation and reports to the side table
    Given a carousel has been rendered and delivered to the user
    When the qa_reviewer subagent runs
    Then a structured QA report is written to carousel_qa_reports for that project_id
    And the carousel's success state is unchanged

  Scenario: A Playwright crash does not fail the generation
    Given the qa_reviewer's Playwright session crashes or times out
    When the QA node runs after generation
    Then the failure is swallowed and a QA-unavailable marker is recorded
    And the user's generation still succeeds

  Scenario: Runtime kaizen proposes improvements for human approval
    Given runtime-learnings-log.jsonl has accumulated QA reports
    When the runtime kaizen variant mines the log
    Then it emits proposed prompt/skill/persona improvements
    And no change is auto-applied without human approval
```

## Delta

### ADDED

- `qa_reviewer` subagent/node + Playwright MCP report flow.
- `carousel_qa_reports` side table + migration.
- `runtime-learnings-log.jsonl` + a runtime `kaizen` variant.

### MODIFIED

- The carousel completion path to trigger the best-effort QA node post-delivery.

### REMOVED

- None.

## Affected Areas

- Backend: `qa_reviewer` subagent/node, report tool, runtime kaizen variant.
- Frontend: none (report is internal; optional surfacing later).
- Database: **new `carousel_qa_reports` side table** (Alembic migration; prod uses
  migrations on deploy per ADR-012).
- API: none required (side-table read could be added later).
- Tests: crash-safe `.feature` + mine→propose unit test.
- Docs: ADR-0017 reference.
- Prompts/LLM: qualitative reviewer prompt (registry-loaded; cost-gated).
- Observability: Langfuse tags for the QA pass.
- Deployment: Playwright on the droplet — the crash-safe contract is mandatory.

## Dependencies

- Provisional epic id: **RES-12** (Phase 6).
- Gating ADR: **ADR-0017 (best-effort runtime product-QA subagent + runtime kaizen
  channel)**.
- Blocked by: **AE-0249 (RES-10)** (subagent pattern + Playwright tool wrapping) and
  **AE-0250 (RES-11)** (façade packages host the subagent).
- Blocks: none (terminal node of the runtime loop).
- Related: AE-0163 (don't introduce a blocking/failing write path), the delivery
  `/kaizen-skill`.

## Implementation Plan

1. Add the `carousel_qa_reports` side table + Alembic migration.
2. Implement the `qa_reviewer` node: cheap pass (screenshot/DOM/rule-checks) always;
   LLM pass flag-gated. Wrap the whole node in a crash-safe guard (swallow → marker).
3. Trigger it post-delivery (off the critical path); write the report + append the run
   summary to `runtime-learnings-log.jsonl`.
4. Add the runtime `kaizen` variant (mine→propose, human-approved); test the path.
5. Run gates.

## QA Checklist

- [ ] Security reviewed (Playwright nav of generated content; no untrusted code exec)
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested (Playwright crash swallowed; generation still succeeds)
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-06-18 21:30

Created from the agent-architecture-restructure epic (RES-12). Every-generation but
best-effort/non-blocking; side-table report; crash-safe; runtime kaizen channel separate
from delivery.

## Files Touched

Pending.

## Test Evidence

Pending.

## QA Report

Pending.

## Decision Log

- **Best-effort / non-blocking is the load-bearing contract.** The human chose
  every-generation; the safety comes from the post-delivery + crash-safe + side-table
  design, not from skipping generations (arch-plan §7.3). A QA failure can NEVER fail a
  generation — proven by the injected-crash scenario.
- **Separate runtime learnings log + human-approved kaizen.** Delivery kaizen mutates
  CI/lint/CLAUDE.md; runtime kaizen mutates content standards/prompts — sharing the JSONL
  would pollute both (arch-plan §6.2). No auto-apply (ADR-0017).
- **Side table, not the carousel record** — never mutate generation success state.

## Test Classification (CLAUDE.md AE-0153 / AE-0180)

- **Behavior-changing — new runtime QA + a new side table + a learnings channel.**
  **`.feature` REQUIRED** (happy: report written; failure: crash swallowed, generation
  succeeds; kaizen: human-approved proposals).
- The crash-safe failure scenario is the most important test — it proves the
  non-blocking guarantee.
- **Affected gates:** backend `pytest`/`mypy`/`ruff` + migration checks.

## Blockers

None (sequenced after AE-0249 + AE-0250).

## Final Summary

Pending.
