# Concurrency Contract (Phase 0 draft)

**Status:** Draft (Phase 0 deliverable for the domain modularization plan).
The conflict-response rule (field 4) is **DECIDED, not draft** — see that
section.
**Owner ticket:** AE-0073
**Date:** 2026-06-12
**Plan source:** `.agent/reports/domain-modularization.options.md`,
section "Required Supporting Designs" → "Concurrency contract"
**Validated in:** Phase 2.5 (`lock_version` / expected-version conflict tests),
then incrementally at each phase exit gate per the adversarial test matrix.

This contract specifies the concurrency rules that commands across the
modularized backend must satisfy. It is **normative** for later phases: the
Phase 2.5 `optimistic_lock_service` coverage work and every redirected write
slice in Phases 4-6 are tested against the rules below.

## Cross-links

- ADR-0009 (eventual path, drafted concurrently in AE-0072):
  [`docs/decisions/0009-adopt-domain-modular-monolith.md`](../decisions/0009-adopt-domain-modular-monolith.md)
  — operating-context statement, rollback track, transaction/event policy.
- Domain glossary (ubiquitous language; every term below agrees with it):
  [`docs/architecture/domain-glossary.md`](./domain-glossary.md).
- Adversarial test matrix (where these rules get exercised per phase):
  [`docs/architecture/adversarial-test-matrix.md`](./adversarial-test-matrix.md).
- `lock_version` distribution and `optimistic_lock_service` coverage facts:
  [`docs/architecture/checkpoint-inventory.md`](./checkpoint-inventory.md)
  (AE-0075).
- Interview record (decision 10, conflict policy):
  [`.agent/reports/domain-modularization.interview.md`](../../.agent/reports/domain-modularization.interview.md).

## Language note

All terms used here are taken from the domain glossary; no term conflicts
with it. In particular:

- `EditorialProject` is the project aggregate; `carousel_projects` /
  `CarouselProject` is a **compatibility term only** for the live table and
  `/api/carousels/*` routes (glossary).
- `EditorialWorkflow` is the business workflow lifecycle; bare `Workflow` is
  avoided. "Workflow command" below means a command against an
  `EditorialWorkflow` (phase transition, review, approval, resume).
- `ArtifactBuild` is the versioned render output of a `CarouselPresentation`;
  `build_status` is its lifecycle state.
- `ChannelPublication` is the canonical sense of "Publication";
  `publication_status` is its state, distinct from `review_status` (editorial
  approval). "Stale content" below is content whose `review_status` /
  underlying aggregate version no longer reflects the approved state.
- Read-model freshness applies to `editorial_operations` views, which are
  **event-built read models, never direct joins** (glossary).

## Operating-context scope

Per the interview (decisions 1, 9) and ADR-0009's operating-context
statement: **pre-production, single user, no external consumers**, one
backend deployment, one Redis transport, PostgreSQL as the source of truth.
There is no multi-tenancy. This contract is written so it still holds when
the system gains real users, but the *enforcement rollout* is staged: per the
plan, expected-version enforcement is **test/CI-only during Phase 2.5** and
activates in production behind the first redirected carousel write slice in
Phase 4. This contract defines the target behavior; it does not by itself
authorize a production write-path change.

---

## The seven required fields

### 1. Aggregate or legacy-row expected version

Every mutating command carries the **expected version** of the row/aggregate
it intends to change.

- The concurrency token is the existing **`lock_version`** integer column on
  `carousel_projects` and `blog_posts` (migration 0002, created `NOT NULL`
  with `server_default="1"`, so every row already carries a version — no
  backfill needed).
- `application/services/optimistic_lock_service.py` performs the **atomic
  compare-and-increment**: the command supplies the version it read; the
  service updates the row only if the stored version still matches, then
  increments it. AE-0075 confirmed this service exists and is in active use
  (observed `lock_version` values up to 18 across 39 `carousel_projects`
  rows; `blog_posts` is empty).
- **Coverage today is PARTIAL.** Callers that already enforce it:
  `api/routes/workflow_audit.py`, `api/routes/blog_post.py`, and
  `api/routes/carousels/editorial_workflow_routes_validate.py`. Other write
  paths (workflow workers, remaining carousel routes) **bypass** it.
- **Contract requirement:** while `carousel_projects` remains the legacy
  shared row, the expected version is the **legacy-row** `lock_version`, and
  the single legacy writer (the legacy coordinator) owns its increment. As
  fields migrate to module-owned tables (Phases 4-6), each module-owned
  aggregate carries its **own** expected version, enforced by the same
  compare-and-increment discipline on the new table.
- **Non-goal here:** extending coverage to all write paths is **Phase 2.5**
  work, not this document. This contract states the target; the enforcement
  code is out of scope (ticket Non-Goals).

### 2. Idempotency key for retried operations

Retried operations must produce **exactly one** business effect.

- **Workflow commands carry an idempotency key** (interview decision 10).
  A workflow command is a command against an `EditorialWorkflow` — phase
  transition, review submission, approval, or **resume**.
- The key is **client-supplied and stable across retries** of the same
  logical operation: a retry reuses the same key; a genuinely new operation
  uses a new key.
- The handler deduplicates on the key: a command whose key was already
  applied returns the **original result** rather than re-executing the
  effect. This is what makes "duplicate commands" safe under at-least-once
  execution (matrix rows 2 and 10).
- Idempotency keys and expected versions are **complementary**: the
  expected version rejects a write made against stale data (a *conflict*);
  the idempotency key absorbs a *retry* of an already-applied write
  (a *duplicate*). A retried command therefore carries both its idempotency
  key and the version it originally observed.

### 3. Which operations require serialization

Operations that mutate shared state must be **serialized** so concurrent
attempts cannot interleave into a lost update or a split decision.

Serialization is required for:

- **Any write to the legacy `carousel_projects` row.** During compatibility
  phases this row has **exactly one writer** (the legacy coordinator / the
  single migrating module per the migration-window rule); the
  compare-and-increment on `lock_version` serializes concurrent attempts —
  the second attempt fails the version check rather than overwriting.
- **`EditorialWorkflow` phase transitions** for one `EditorialProject`: two
  commands trying to advance/approve the same project's workflow must
  serialize on that project's expected version.
- **`ArtifactBuild` creation** for the same `CarouselPresentation` — see
  field 5 (deduplication is the serialization mechanism for builds).
- **`ChannelPublication` state changes** (publish / schedule / unpublish)
  for the same content.

Operations that **do not** require serialization: independent reads, queries
against read-only sessions/projections, and commands against **disjoint**
aggregates (different projects, different presentations).

### 4. Conflict response and client retry behavior — DECIDED

This rule is **decided, not draft** (interview decision 10, 2026-06-12:
"409 + UI refresh prompt + idempotency keys on workflow commands").

**EARS requirement:**

> **WHEN** a command carries a stale expected version
> **THE API SHALL** return **409** with a machine-readable conflict body.

**Conflict body shape** (machine-readable error payload):

```json
{
  "error": "version_conflict",
  "resource": "EditorialProject",
  "resource_id": "<uuid>",
  "expected_version": 7,
  "actual_version": 9,
  "message": "This item changed since you loaded it. Refresh to see the latest version."
}
```

- `error` is a **stable machine-readable code** (`version_conflict`) the
  client matches on — not a human string.
- `resource` uses the **glossary** aggregate name (e.g. `EditorialProject`,
  `BlogPost`, `ChannelPublication`); while a write still targets the legacy
  row, `resource` MAY be reported as the legacy `CarouselProject`
  compatibility name until that field migrates.
- `expected_version` echoes what the client sent; `actual_version` is the
  current stored `lock_version`, so the client can detect how far behind it
  is.

**Client retry behavior (UI refresh prompt):**

- The client SHALL **not blindly auto-retry** a 409 — a stale write must not
  be replayed against newer data, or it would clobber the change it
  conflicted with.
- The client SHALL surface a **refresh prompt** ("refresh prompt" is the
  canonical UX term, per glossary), re-fetch the current state, and let the
  user re-apply their intent against the fresh version (which carries the new
  expected version).
- **Tie to idempotency keys:** a 409 is distinct from a transport retry. If
  the client retries a workflow command because of a *network/transport*
  failure (not a 409), it reuses the **same idempotency key** (field 2) so
  the server deduplicates rather than double-applying. A 409 means the data
  moved on; a transport retry means the request may or may not have landed.
  The two are handled differently: refresh-and-reapply for 409, same-key
  replay for transport retries.

### 5. Artifact build deduplication

Duplicate `ArtifactBuild` requests for the same `CarouselPresentation` must
yield **one** build, not N concurrent renders.

- A build is keyed by **(`CarouselPresentation` identity, presentation
  content version)**. A request for a build whose key already exists and is
  `build_status` *building* or *succeeded* **joins/returns the existing
  build** rather than starting a new one.
- This is the build-specific application of the idempotency rule (field 2):
  the idempotency key for a build command is derived from the presentation
  version, so a retried "rebuild" command does not fan out into multiple
  renders.
- A build is re-run only when the presentation content version changes (a
  genuinely new build key) or a prior build reached `build_status` *failed*
  and is explicitly retried.
- This rule is exercised by matrix rows 2 (duplicate commands) and 10
  (exactly-once business effects) against `ArtifactBuild`.

### 6. Projection freshness requirement

Read models (`editorial_operations` board/calendar/notifications/analytics
views, the public blog projection) are **eventually consistent**, built from
other contexts' events — never from direct cross-context table joins
(glossary).

- A read model MAY lag the authoritative aggregate. Consumers of read models
  MUST treat them as **possibly stale** and MUST NOT make a serialization
  or authorization decision solely from a projection.
- A **decision that requires current truth** (e.g. approving, publishing,
  or advancing a workflow) reads the **authoritative aggregate with its
  expected version**, not a projection.
- Projections are **idempotent on rebuild**: replaying an event already
  applied does not double-count (matrix rows 5 and 7).
- Freshness expectation for the single-user pre-production context:
  read models are refreshed on the triggering event; there is no defined
  staleness SLA yet because there is no concurrent multi-user load. A
  staleness budget is added per slice if/when real traffic arrives
  (ADR-0009 operating-context statement governs this).

### 7. Whether publication is allowed from stale content

**Publication from stale content is NOT allowed.**

- `review_status` (editorial approval) is **separate** from
  `publication_status` (glossary): approval does not auto-publish (Phase 6
  exit gate), and **publishing re-validates against the authoritative,
  current aggregate version**.
- A **publish command** (a `ChannelPublication` state change) carries the
  expected version of the content it publishes. **WHEN** that version is
  stale, the command returns **409** per field 4 — the same conflict rule
  applies to publication, not just editorial edits.
- Therefore a `ChannelPublication` can only be created/advanced from content
  whose expected version still matches: stale content is refreshed and
  re-approved before it can be published. Public routes read **publication
  projections**, not editorial aggregates (Phase 6), but the *act* of
  publishing is gated on the authoritative version.
- This closes the "stale read model → published anyway" gap (matrix rows 7
  and 3 against the publishing context).

---

## Summary table

| # | Field | Rule (one line) | Validated by matrix rows |
|---|---|---|---|
| 1 | Expected version | `lock_version` compare-and-increment via `optimistic_lock_service`; legacy-row version now, module-owned version after migration | 3 |
| 2 | Idempotency key | Client-supplied stable key on workflow commands; handler dedups → one effect | 2, 10 |
| 3 | Serialization | Required for legacy-row writes, workflow transitions, builds, publication state | 3, 4 |
| 4 | Conflict response (DECIDED) | 409 + machine-readable body; client shows refresh prompt, no blind auto-retry | 3 |
| 5 | Build deduplication | One `ArtifactBuild` per (presentation, content version); retries join existing | 2, 10 |
| 6 | Projection freshness | Read models eventually consistent, idempotent on rebuild; decisions read authoritative aggregate | 5, 7 |
| 7 | Stale-content publication | Not allowed; publish re-validates expected version, 409 if stale | 3, 7 |

## Out of scope (ticket Non-Goals)

- No test implementation (the matrix cells are filled by each phase's exit
  gate).
- No `lock_version` enforcement code — extending
  `optimistic_lock_service` coverage to all write paths is **Phase 2.5**.
