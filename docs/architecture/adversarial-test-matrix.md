# Adversarial Test Matrix (Phase 0 skeleton)

**Status:** Skeleton (Phase 0 deliverable for the domain modularization plan).
Cells declare *whether* a category applies to a phase; the actual tests are
written by each phase's exit-gate work. **No test code lives here.**
**Owner ticket:** AE-0073
**Date:** 2026-06-12
**Plan source:** `.agent/reports/domain-modularization.options.md`,
section "Required Supporting Designs" → "Adversarial test matrix".
**Validated in:** incrementally at each phase exit gate (the plan: "Per-phase
rows only; never a standalone multi-week effort").

## Purpose and how to read it

- **Rows** are the plan's **ten adversarial categories**, quoted **verbatim**
  from the "Adversarial test matrix" section so coverage is mechanically
  checkable against the plan.
- **Columns** are the migration **phases that own real risk surface**:
  Phase 2 through Phase 8, **including Phase 2.5**. (Phase 0 = these drafts;
  Phase 1 = scaffolding only, no behavior moves — neither introduces an
  adversarial surface, so they are not columns.)
- Each cell is **`required`** or **`n/a`**. Every `n/a` carries a one-line
  reason. A `required` cell is a commitment that the phase's exit gate
  includes that adversarial test before the phase is declared done.

## Cross-links

- ADR-0009 (eventual path, drafted concurrently in AE-0072):
  [`docs/decisions/0009-adopt-domain-modular-monolith.md`](../decisions/0009-adopt-domain-modular-monolith.md).
- Domain glossary (all terms below agree with it):
  [`docs/architecture/domain-glossary.md`](./domain-glossary.md).
- Concurrency contract (rows 1-3, 5, 7, 10 reference its rules):
  [`docs/architecture/concurrency-contract.md`](./concurrency-contract.md).
- Checkpoint inventory (row 9 facts; serialization PORTABLE):
  [`docs/architecture/checkpoint-inventory.md`](./checkpoint-inventory.md).

## Phase legend (columns)

| Column | Phase | Risk surface introduced |
|---|---|---|
| P2 | Phase 2 — Pilot the Knowledge module | First module extraction (HTTP, persistence, vendor adapters, UoW) |
| P2.5 | Phase 2.5 — Carousel risk spike | Read-only compat adapter; `optimistic_lock_service` coverage + conflict tests (test/CI-only); checkpoint inventory; idempotency proofs |
| P3 | Phase 3 — Identity and Conversation boundaries | Auth/admin rules into identity; conversation streaming use cases |
| P4 | Phase 4 — EditorialProject facade over CarouselProject | Legacy carousel ACL; **first redirected carousel write path** + production `lock_version` activation; checkpoint drain before schema migration |
| P5 | Phase 5 — Extract Carousel Presentation | Slides/rendering/`ArtifactBuild`/image gen behind ports; vendor adapters |
| P6 | Phase 6 — Separate Publishing, Blog, Distribution | `ChannelPublication`, scheduling, public read models, **transactional outbox** for release events |
| P7 | Phase 7 — Align the frontend | Feature reorg under context names; OpenAPI/schema drift checks (no new backend behavior) |
| P8 | Phase 8 — Remove legacy layers and adapters | Delete compat imports/facades; rollback proof for cutover |

---

## Matrix

Legend: **R** = `required` · **n/a** = not applicable (reason in the row's
notes).

| # | Adversarial category (verbatim plan text) | P2 | P2.5 | P3 | P4 | P5 | P6 | P7 | P8 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Authorization bypass attempts. | R | R | R | R | R | R | n/a | n/a |
| 2 | Duplicate commands and duplicate events. | R | R | R | R | R | R | n/a | R |
| 3 | Concurrent updates and expected-version conflicts. | R | R | n/a | R | R | R | n/a | n/a |
| 4 | Transaction cancellation between state and outbox writes. | n/a | n/a | n/a | n/a | n/a | R | n/a | n/a |
| 5 | Event replay, poison events, and relay restart. | n/a | n/a | n/a | n/a | n/a | R | n/a | n/a |
| 6 | Partial AI, rendering, storage, vector, and publishing vendor failure. | R | n/a | R | n/a | R | R | n/a | n/a |
| 7 | Stale read models. | n/a | n/a | R | R | n/a | R | n/a | n/a |
| 8 | Rolling deployment and rollback. | R | R | R | R | R | R | R | R |
| 9 | Resume of checkpoints written by prior versions. | n/a | R | n/a | R | R | n/a | n/a | n/a |
| 10 | Exactly-once business effects under at-least-once execution. | n/a | R | n/a | R | R | R | n/a | n/a |

---

## `n/a` justifications (one line each)

### Row 1 — "Authorization bypass attempts."

- **P7 n/a** — frontend alignment moves no authorization decision; backend
  policies unchanged. (Frontend never owns authorization.)
- **P8 n/a** — legacy removal deletes already-superseded code paths; no
  authorization surface is added, and removed paths were covered when added.

### Row 2 — "Duplicate commands and duplicate events."

- **P7 n/a** — no new commands/events; frontend reorg only.

### Row 3 — "Concurrent updates and expected-version conflicts."

- **P3 n/a** — identity/conversation extraction preserves cookies, tokens,
  and stream payloads; it introduces no shared-row mutating concurrency
  beyond what already exists (no new `lock_version`-guarded write path).
- **P7 n/a** — no backend write behavior changes.
- **P8 n/a** — removal phase adds no concurrent write path.

### Row 4 — "Transaction cancellation between state and outbox writes."

- **P2, P2.5, P3, P4, P5 n/a** — the **transactional outbox does not exist
  until Phase 6** (Phase 0 ships the reorder-only fix; the durable outbox is
  a Phase 6 deliverable). There is no state/outbox write pair to cancel
  between before then.
- **P7 n/a** — frontend; no transactions.
- **P8 n/a** — outbox already validated in P6; removal adds no new
  state/outbox boundary.

### Row 5 — "Event replay, poison events, and relay restart."

- **P2, P2.5, P3, P4, P5 n/a** — durable event delivery / relay is a
  **Phase 6 outbox** capability; no relay to replay or restart exists earlier
  (Redis is transport, not durable consumption, per ADR-0009).
- **P7 n/a** — frontend.
- **P8 n/a** — relay semantics validated in P6; nothing removed in P8
  reintroduces them.

### Row 6 — "Partial AI, rendering, storage, vector, and publishing vendor failure."

- **P2.5 n/a** — the spike builds a **read-only** compatibility adapter and
  runs `lock_version`/idempotency tests; **no production vendor call path is
  introduced or redirected** (no write redirection rule).
- **P4 n/a** — Phase 4 is the EditorialProject **facade/ACL over workflow
  state**; vendor (image/render/vector) call paths are not moved until
  Phase 5 (presentation) — those failures are tested where the adapters land.
- **P7 n/a** — frontend reorg; vendor adapters unchanged.
- **P8 n/a** — removal phase; vendor adapters already validated where
  introduced.

### Row 7 — "Stale read models."

- **P2 n/a** — knowledge pilot exposes document/search behind handlers; it
  does not introduce an `editorial_operations` event-built read model.
- **P2.5 n/a** — read-only snapshot adapter is computed on demand from
  production-shaped rows, not an eventually-consistent projection that can
  lag.
- **P5 n/a** — presentation extraction owns `ArtifactBuild`/rendering, not
  the board/calendar/public read models.
- **P7 n/a** — frontend consumes projections but builds none.
- **P8 n/a** — removal adds no projection.

### Row 8 — "Rolling deployment and rollback."

- No `n/a`: **every phase** is independently deployable and revertible
  (rollout rule 3) and must prove its rollback/forward-fix path at its exit
  gate. This is `required` across P2-P8 including P2.5 (P2.5 ships the
  database restore drill + checkpoint fixture replay on the scaled-down
  track).

### Row 9 — "Resume of checkpoints written by prior versions."

- **P2 n/a** — knowledge module does not touch LangGraph carousel workflow
  checkpoints.
- **P3 n/a** — identity/conversation extraction keeps checkpoint identifiers
  and schemas untouched.
- **P6 n/a** — publishing/distribution and outbox do not change the carousel
  workflow checkpoint format.
- **P7 n/a** — frontend; no checkpoints.
- **P8 n/a** — no checkpoint format change in the removal phase.
- **Note (P2.5, P4, P5 = R):** the policy is **finish-or-restart**
  (interview decision 2) and serialization is **PORTABLE** (AE-0075), so
  "resume" here means the inventory + drain-before-migrate proof (P2.5
  inventory; P4/P5 drain live checkpoints before any schema-modifying
  migration) rather than cross-version replay tooling, which is deleted from
  scope.

### Row 10 — "Exactly-once business effects under at-least-once execution."

- **P2 n/a** — knowledge pilot has no at-least-once delivery surface (no
  outbox/relay yet) and no duplicate-effecting command worth proving here.
- **P3 n/a** — identity/conversation extraction introduces no
  duplicate-prone business effect under at-least-once execution.
- **P7 n/a** — frontend; no business effects.
- **P8 n/a** — exactly-once effects validated where the commands/outbox were
  introduced (P2.5, P4, P5, P6); removal adds none.

---

## Coverage check (mechanical)

- **10 categories** present as rows, each quoting the plan's "Adversarial
  test matrix" bullet **verbatim**.
- **8 phase columns**: P2, **P2.5**, P3, P4, P5, P6, P7, P8 — Phases 2
  through 8 including Phase 2.5.
- **80 cells**, each marked `R` (`required`) or `n/a`; every `n/a` has a
  one-line reason above.

## Out of scope (ticket Non-Goals)

- No test implementation — cells are filled by each phase's exit-gate work.
- No `lock_version` enforcement code (that is Phase 2.5).
