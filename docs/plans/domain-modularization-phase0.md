# Domain Modularization — Phase 0 Epic Plan

**Epic ticket:** AE-0070
**Source plan:** `.agent/reports/domain-modularization.options.md` (Option B,
round-3 skeptical review `PROCEED_WITH_CAUTION`, 2026-06-12)
**Authorized scope:** Phase 0 only — language, constraints, and evidence.
Phases 1-8 remain gated by the plan's phase exit criteria; Phase 2.5 start
additionally requires the rollback-track choice and checkpoint-serialization
confirmation produced here.

## Ticket breakdown

| Ticket | Title | Tier | Budget | Blocked by |
|---|---|---|---:|---|
| AE-0070 | Phase 0 epic — language, constraints, evidence | T3 | — | — |
| AE-0071 | Context map and ubiquitous glossary | T2 | 2d | — |
| AE-0072 | Draft ADR-0009: domain modular monolith | T2 | 2d | AE-0071, AE-0075 |
| AE-0073 | Concurrency contract draft + adversarial test matrix skeleton | T2 | 1d | — (related: AE-0072) |
| AE-0074 | Fix workflow event ordering (persist before publish) | T2 | 1d | — |
| AE-0075 | Checkpoint and lock_version inventory | T2 | 1.5d | — |
| AE-0076 | Freeze SSE event-name inventory + CI contract test | T2 | 1d | — |
| AE-0077 | Re-measure frontend baseline, re-publish estimate | T2 | 0.5d | — |
| AE-0078 | Record import-violation and public-contract baseline | T2 | 0.5d | — |

Total budget: ~9.5 working days against the plan's 1-2 week Phase 0 box.
This table satisfies the plan's "publish a deliverable-level time budget on
day one" requirement. Items that do not fit move to a named Phase 0b ticket
rather than silently extending Phase 0.

## Pacing (2026-06-12 interview)

Owner bandwidth is ~5-10h/week. Run **one serial lane** (the "parallel-
safe" groupings below mean order-independent, not simultaneous), keep
PRs small, and let CI gates carry the review load. The ~9.5-day budget
therefore spans roughly 4-8 calendar weeks, not two. Interview decisions
binding this epic: migrate-in-place track, EditorialProject, one
BlogPost aggregate, persona/quality split, editorial_operations as
module, drop `stream_entry_id`, 409 conflict policy — see
`.agent/reports/domain-modularization.interview.md`.

## Execution waves (decided 2026-06-12)

Tickets execute in waves; within a wave the lane is serial (pacing
decision), and a wave closes only when every ticket in it is Done with
CI green and the board re-rendered.

| Wave | Tickets | Theme |
|---|---|---|
| 1 — Fix & Measure | AE-0074 → AE-0077 → AE-0078 → AE-0075 | Live bug fix + cheap evidence that unblocks the ADR |
| 2 — Language & Law | AE-0071 → AE-0072 → AE-0073 → AE-0076 | Glossary, ADR-0009, contracts; closes Phase 0 (epic AE-0070) |
| 3 — Debt core | AE-0041 → AE-0042 (verifies AE-0057) → AE-0043 → AE-0049 | Architecture-neutral cleanup + CI hardening |
| 4 — Debt patterns | AE-0044 → AE-0045 → AE-0046 → AE-0050 | Target-shaped refactors (editorial adapter, presentation) |
| 5 — Frontend & tests | AE-0006 → AE-0047 → AE-0068 | Strategy tests, co-location, spinner consolidation |
| — | AE-0008, AE-0009 | Product work; slot into any wave gap by priority |

Phase 1 scaffolding tickets are written only after Wave 2 closes
(ADR-0009 exists) and are gated by the plan's phase rules.

## Risks

- **AE-0072 is the critical path.** The rollback-track choice recorded in
  ADR-0009 is the Phase 2.5 start precondition. If the operating-context
  facts are ambiguous, decide explicitly and record the reasoning rather
  than stalling.
- **AE-0075 can re-escalate.** If checkpoint payloads prove
  class-path-dependent (pickled), the plan's escalation rule blocks
  Phase 2.5 until a serialization migration plan exists. This is a planned
  outcome, not a failure.
- **AE-0074 touches live event behavior.** SSE consumers must see identical
  payloads; only ordering relative to the database transaction changes.
- **Single contributor.** No ticket here depends on AE-0040-epic files
  except AE-0074, whose overlap is via emit() call sites (e.g.,
  `application/services/carousel/editorial_workflow_events.py`), not
  `workflow_event_service.py` itself (which lives in
  `application/services/`); coordinate with AE-0044/0045/0046 if those
  start in parallel — they remain Intake today.
- **AE-0074 carries a known design wrinkle**: the audit row stores the
  Redis `stream_entry_id`, which is why publish currently precedes
  persistence. The 1-day budget assumes the NULL-or-post-commit-update
  decision is quick; overflow routes to Phase 0b.

## Impact summary

- Backend: AE-0074 (code), AE-0075/AE-0076 (tests/fixtures), AE-0078 (report)
- Frontend: AE-0076 (literal verification), AE-0077 (measurement)
- Docs: AE-0071, AE-0072, AE-0073, AE-0075, AE-0077, AE-0078
- Migrations: none (explicitly out of scope for Phase 0)
- Prompts/LLM: none
- CI: AE-0076 adds a contract test; no gate behavior changes elsewhere

## Tech-debt waves (adapted 2026-06-12)

The open AE-0040-family tickets were adapted to this architecture (each
carries a "Modularization Alignment" section). They run **before**
structure changes:

- **Wave A** (parallel with Phase 0): AE-0041, AE-0042 (absorbs
  AE-0057), AE-0043, AE-0006, AE-0047 (spinner → AE-0068), AE-0068,
  AE-0049. Architecture-neutral cleanup plus CI hardening.
- **Wave B** (after AE-0041): AE-0044 (shaped for the editorial inbound
  HTTP adapter), AE-0045/AE-0046 (shaped for carousel_presentation),
  AE-0050 (deprecation windows close before Phase 4).
- AE-0008 and AE-0009 are product work, not debt — schedulable anytime,
  with DI-injection and additive-schema rules noted in their tickets.
- Hard rule: Waves A/B merge before any Phase 4-5 file movement.

## Out of scope (next waves, gated)

- Phase 1 scaffolding tickets (bootstrap/, modules/, Import Linter ratchets)
- Phase 2 Knowledge pilot tickets (includes writing document/search Gherkin)
- Phase 2.5 spike tickets (field ownership map, compatibility adapter,
  `lock_version` enforcement) — blocked on AE-0072's track choice and
  AE-0075's serialization confirmation

## Handoff

To `/architect-skill validate` for pre-dev ticket validation. Tickets stay
`Intake` until validation returns PASS; then they move to `Ready`.
