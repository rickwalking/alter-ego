# ADR-009: Adopt Domain Modular Monolith

## Status

Proposed

## Context

Alter-Ego's backend is organized by global technical layers
(`domain/application/infrastructure/api/agents`). Business ownership is
scattered across these layers, the `CarouselProject` row behaves as a god
object, blog content has two representations, and dependency rules are not
mechanically enforced (Import Linter carries blanket exemptions; application
code reaches into a global service-locator container). The
`domain-modularization` research and options reports
(`.agent/reports/domain-modularization.options.md`,
`.agent/reports/domain-modularization.research.md`) evaluated three
directions and recommended **Option B: an incremental, domain-module-first
modular monolith** — bounded-context packages with internal layers, public
contracts, ports, adapters, compatibility facades, and gradual route
redirection, kept in one backend deployment and one frontend deployment.

That direction was hardened across four skeptical-review rounds
(round 1 `BLOCK` → round 4 `PROCEED_WITH_CAUTION`, no BLOCKERs) and a
codebase-verification pass, then settled by a structured owner interview
(`.agent/reports/domain-modularization.interview.md`, 2026-06-12). The
review produced **four mandatory amendments** and several supporting-design
decisions (DI mechanism, outbox semantics, migration-window definition) that
had no ADR home. Phase 2.5 of the migration cannot start until the rollback
track is recorded, and the DI and outbox decisions must be explicit so
Phase 1 scaffolding cannot silently lock in alternatives.

This ADR records those decisions normatively. It does **not** re-derive the
plan; the plan remains in the options report and the ubiquitous language in
`docs/architecture/domain-glossary.md` (AE-0071). The concurrency contract
and adversarial test matrix are owned by AE-0073 and are **referenced, not
duplicated** here.

The terms used below — `EditorialProject`, `EditorialWorkflow`,
`CarouselPresentation`, `ArtifactBuild`, `BlogPost`, `ChannelPublication`,
`VoiceScore`, `phase_status`, `review_status`, `publication_status`,
`build_status`, `SourceMaterial`, `ResearchSource` — resolve against
`docs/architecture/domain-glossary.md`. `carousel_projects`,
`CarouselProject`, `blog_markdown`, and `/api/carousels/*` are compatibility
terms per that glossary.

## Decision

Adopt Option B, the domain-module-first modular monolith, governed by the
normative sections below. Each section uses SHALL/MUST language and is
binding on the phased migration in the options report.

### 1. Operating context

> This is the first content section by design (round-4 amendment 4):
> rollback and parity requirements are calibrated by it.

The operating context SHALL be treated as: **pre-production, single user, no
external consumers, single-tenant**. This is an explicit architectural
constraint, not an assumption (interview decisions 1 and 9). Concretely:

- The only clients of the API, events, and database are the in-repo Next.js
  frontend and in-process workers (interview decision 9). No external
  consumer exists that a breaking change could break.
- The system is single-tenant. Multi-tenancy is **out of scope** and is
  recorded here as a deliberate constraint, so that authorization and
  data-ownership decisions are not over-engineered for tenancy that does not
  exist.
- Persisted workflow state is bounded and inventoried. Per the AE-0075
  checkpoint inventory (`docs/architecture/checkpoint-inventory.md`,
  2026-06-12): **6,918 checkpoints** (all `msgpack`,
  `JsonPlusSerializer`, serialization verdict **PORTABLE** — `rag_backend`
  appears in 0/6,918 checkpoint blobs), **39 carousel projects**, and the
  **`blog_posts` table is empty**. Of the 39 projects, roughly 23 carry any
  finish cost (one or two approval clicks each); a full drain is realistically
  under an hour of owner time.

Because the system is effectively pre-production, the full
rollback/parity machinery (production-shaped rollback drills, legacy/new
parity metrics with alert thresholds, automated disable criteria,
mixed-version deployment testing) is NOT required. The **scaled-down track**
of Section 2 applies instead. The field-ownership map, deny-by-default
authorization (Section 5), and single-writer rule (Section 6) remain
mandatory regardless of track.

### 2. Rollback track choice: scaled-down + migrate-in-place

The recorded rollback track SHALL be **scaled-down + migrate-in-place**
(not `full`). This is the explicit, recorded choice required before Phase 2.5
may start. Its consequences:

- Tables, columns, and API responses MAY be renamed or reshaped during
  Phases 4-6 via **data-preserving Alembic migrations**, with the frontend
  updated **in the same phase**. No external clients exist to break.
- The permanent legacy ACL, permanent sole-writer coordinator, and
  frozen-schema rules SHALL shrink to **per-migration-window discipline**
  (Section 3).
- The LangGraph checkpoint policy SHALL be **finish-or-restart**: in-flight
  workflows are finished on the old code or restarted with the owner's
  documented consent. No cross-version checkpoint migration tooling SHALL be
  built. (AE-0075's serialization verdict is PORTABLE, so this policy stands
  on convenience grounds, not necessity.)
- The `carousel_projects` field-ownership map (Phase 2.5 core) SHALL be
  retained and repurposed as the **migration map** — every column's
  destination module and migration step — rather than a permanent
  shared-row treaty.

**Phase 2.5 exit-gate parameterization.** Because the track is scaled-down,
the Phase 2.5 exit gate's contingent layer is the scaled-down set: a
**database restore drill**, a **checkpoint fixture replay**, and a
**trace-correlated smoke comparison**. The full-track contingent items
(three-entry-point authorization contract tests through HTTP, agent-tool,
and worker entry points; the full rollback drill over compatibility data,
events, projections, and checkpoints) SHALL move to the **Phase 4 exit
gate** and SHALL be complete before any carousel write path is redirected.
Deferring them does not reintroduce the round-1 single-writer blocker
because no write path is redirected in Phases 2.5-3.

### 3. Migration-window definition

A **migration window** SHALL be defined as the wall-clock span from a
schema-modifying Alembic revision landing to its phase exit gate passing,
with a **ceiling of 2 calendar weeks**. Within a window:

- The affected table SHALL have **exactly one writer** — the single module
  performing the migration, or the legacy coordinator where one still
  exists.
- **Direct writes from a second module to the same table SHALL be
  prohibited, even inside the window.** This preserves the round-1
  single-writer blocker mitigation in time-boxed form.
- Every window SHALL have a reversible path: a backup plus a tested
  downgrade. No long-lived dual representations of the same data SHALL
  exist.

**Drain-before-migrate (mandatory).** Old code cannot finish a workflow
against a migrated schema. Therefore, **before any schema-modifying
migration**, every live checkpoint from the Phase 2.5 inventory SHALL be
either finished on the pre-migration code or restarted with documented owner
consent (restart preferred when finishing would delay the window). No schema
migration SHALL run while a checkpoint references the old shape. This step is
mandatory, not advisory, and appears in the Phase 4+ exit gates.

### 4. Scope-delta record

The interview produced two deliberate deviations from the recommended
defaults; both are recorded as **must-haves**, priced rather than reverted:

1. **Persona/Quality split** — `persona` and `quality` are **two** bounded
   contexts, not one `persona_quality` context. Persona owns `VoiceScore`
   and `PersonaAgent.enforce()`; quality consumes via persona's public
   contract (dependency direction: quality → persona) (interview
   decisions 5 and 6).
2. **`editorial_operations` as a full module** — it owns notification
   dispatch and board/calendar behavior from day one; its views remain
   event-built read models, never direct joins into other contexts' tables
   (interview decision 7).

Scope-delta line items (rough engineer-weeks, ew):

| Delta | Effect |
|---|---:|
| Migrate-in-place: legacy ACL, route facades, long-lived compatibility repositories, Phase 8 compatibility removal shrink | −2 to −3 ew |
| Finish-or-restart: cross-version checkpoint replay deleted from Phase 2.5 | −0.5 to −1 ew |
| Persona/Quality split: second module bootstrap, public API, contract tests, boundary rules, dependency-direction test | +0.5 to +1 ew |
| Editorial Operations as full module: notification dispatch handlers/adapters, board/calendar rules as owned behavior (was: read views, ~2-3 days) | +1 to +2 ew |
| Net | approximately −1 to +0 ew |

Revised totals: **11-21 engineer-weeks**; calendar realistically **8-14
months** at the owner's ~5-10 h/week pace, one serial ticket lane, small
PRs, CI gates substituting for review depth (interview decision 11).

**Phase-3 / month-6 go/no-go.** At the Phase 3 exit gate or month 6,
whichever comes first, the owner SHALL run an explicit
continue / re-scope / stop review against this table and record the decision
in the AE-0070 epic log. A project of this length requires a scheduled exit
ramp, not an implicit one.

### 5. Resource authorization ownership (amendment 1)

Authorization SHALL be **context-owned and deny-by-default**.

- `identity` owns authentication, actor identity, roles, sessions, and
  service identities. It SHALL NOT centrally own every resource
  authorization decision.
- Each bounded context SHALL own the authorization policies for its own
  resources (e.g., editorial owns view/modify/submit-review/assign;
  carousel_presentation owns view-draft/request-rebuild; publishing owns
  approve/schedule/publish/unpublish; knowledge owns
  read/upload/reprocess/delete; conversation owns read/append).
- Every inbound adapter SHALL supply an **`ActorContext`** containing the
  authenticated actor, roles, request/trace identity, and service identity
  where applicable. This requirement applies to **all** inbound adapters —
  HTTP routes, **agent tools**, **workers**, and event consumers — not just
  HTTP. (The codebase verification confirmed
  `application/workers/workflow_workers.py` currently runs with no
  authorization at all; this is a real gap, not hypothetical.)
- HTTP routes, agent tools, workers, and event consumers SHALL call the
  **same context-owned policy**.
- Delayed destructive or publishing actions SHALL define whether
  authorization is captured at command acceptance or revalidated at
  execution, and SHALL define revocation behavior for queued and in-flight
  work.
- The single-tenant model (Section 1) is the documented tenancy constraint
  satisfying this amendment's "tenancy must be explicit" requirement.

Contract-test coverage (owner, reviewer, admin, anonymous, service identity,
revoked access, cross-resource denial) is specified by AE-0073 and is
referenced here, not duplicated.

### 6. Single writer for `carousel_projects` (amendment 2)

While `carousel_projects` remains shared persistence, it SHALL NOT be
independently written by the editorial, presentation, and publishing
modules. During compatibility phases:

- `legacy.carousel_project` SHALL be the **sole write owner** of
  `carousel_projects`.
- New modules SHALL return decisions, state transitions, or artifact results
  to the legacy coordinator rather than writing the row themselves.
- A **single legacy Unit of Work** SHALL apply row changes and SHALL own
  `lock_version`.
- A **field-level ownership map** SHALL identify which logical context may
  propose each field change, every invariant, command owner, concurrency
  token, and migration destination. The map is the required artifact before
  Phase 4 (`docs/architecture/carousel-project-field-ownership.md`).
- Commands affecting multiple logical contexts SHALL be coordinated as one
  legacy aggregate transaction.
- New modules MAY own separate new tables only when those tables have one
  writer and an explicit consistency relationship to the legacy row.

Independent module write ownership SHALL begin only after the relevant fields
move to module-owned persistence or the old aggregate is intentionally
retained as a process manager. `lock_version` enforcement
(`application/services/optimistic_lock_service.py`, partial coverage today
per AE-0075) SHALL be extended to all write paths; activation behavior is
governed by the AE-0073 concurrency contract and the re-escalation gate in
Section 11.

### 7. Rollback and forward-fix policy (amendment 3)

Route or composition rebinding SHALL be treated as a valid rollback **only**
for slices that have not changed persisted semantics or emitted irreversible
external effects. After that point, the phase-specific ledger governs
compensating actions or forward-fix.

Every phase SHALL carry a **side-effect and compatibility ledger** recording
a decision for each concern:

| Concern | Required decision |
|---|---|
| Database writes | Whether old code can read, ignore, or safely preserve them |
| Outbox events | Fence/version behavior during rollback |
| Projections | Rebuild, invalidate, or continue consuming |
| External publication | Compensating action or forward-fix only |
| Artifact builds | Retention and version compatibility |
| Checkpoints | Compatible reader/writer versions |
| Feature flags | Owner, expiry, and safe deployment order |

A rollback plan that assumes old code can interpret new rows, events,
projections, artifacts, or checkpoints **without an executable
compatibility test** SHALL be considered invalid. For the recorded
scaled-down track, "test rollback with production-shaped data" is satisfied
by the database restore drill plus checkpoint fixture replay (Section 2),
not by a full production-traffic rollback drill.

### 8. Outbox delivery semantics (decision only; implementation Phase 6)

This section records the **decision only**. The outbox SHALL NOT be
implemented before Phase 6.

- The durable delivery source SHALL be a **PostgreSQL outbox**. PostgreSQL
  is the source of truth.
- **Redis is the transport, not proof of durable consumption.** Publishing
  to Redis SHALL NOT be treated as evidence that an event was durably
  consumed.
- Delivery SHALL be **at-least-once**, with **persistent consumer
  deduplication** (consumers are idempotent).
- The design SHALL specify stable event IDs and aggregate sequence numbers,
  relay concurrency and ordering rules, retry limits, poison-event
  quarantine, operational replay, and retention/schema compatibility.
- State and outbox event SHALL be persisted in **one** PostgreSQL
  transaction; outbox records dispatch to Redis **after** commit.

**Phase 0 ships only the AE-0074 reorder fix**: `workflow_event_service.py`
SHALL persist and commit the audit row **before** publishing to Redis,
closing the inconsistency window for the current single-process deployment.
The reorder fix deliberately does **not** provide at-least-once delivery or
replay — those properties arrive only with the Phase 6 outbox. (AE-0074 also
drops the unused `stream_entry_id` column.)

### 9. Dependency injection mechanism

Wiring SHALL be **manual constructor injection** — no DI framework. This
matches the existing hand-rolled container idiom and avoids adding a
framework dependency mid-migration.

- `bootstrap_module(platform: PlatformServices)` SHALL receive platform
  services and construct the module's adapters and handlers explicitly.
- The request-scoped Unit of Work SHALL be created by an inbound dependency
  provider (FastAPI `Depends` at the HTTP edge; explicit construction in
  workers and agent adapters) and passed to handlers as a constructor or
  call argument — never resolved from a global container.
- Test doubles SHALL be swapped by constructing the module bootstrap with
  fake ports; no container patching.

**Re-evaluation trigger (recorded so it is explicit and reversible):**

> if, after the fifth migrated module, composition-root wiring becomes a
> maintenance burden (measured by bootstrap line count and duplication),
> evaluate `dependency-injector` or similar via a lightweight ADR. Until
> that trigger fires, introducing a framework is out of scope.

### 10. Migration invariants and rollback criteria

Each migration slice SHALL satisfy the following **nine** rollout/rollback
rules (from the plan's "Rollout and Rollback" section):

1. Preserve existing transport contracts.
2. Keep one write authority.
3. Be independently deployable and revertible.
4. Add behavior tests before redirecting traffic.
5. Emit observability showing legacy versus new path usage.
6. Support a feature flag or composition switch when the slice is risky.
7. Carry a side-effect and compatibility ledger (Section 7).
8. Declare whether rollback or forward-fix is the supported recovery
   action.
9. Include a before/after diff of the frozen SSE event-name inventory when
   the slice touches any streaming route — event names are string-frozen
   for the entire migration.

(The plan additionally carries a tenth rollout rule — drain live checkpoints
before any schema-modifying slice and respect the 2-calendar-week
migration-window ceiling with exactly one writer per affected table — which
this ADR states normatively in Section 3.)

The concurrency contract and the adversarial test matrix that these slices
must pass are owned by **AE-0073** and are referenced, not duplicated.

### 11. Conditional Phase 2.5 re-escalation gates

Two conditional re-escalations named by the round-3 review are encoded as
Phase 0 evidence gates. **Phase 2.5 SHALL NOT start**, and the corresponding
plan section SHALL be revised first, if either fires:

1. **Checkpoint payloads prove class-path-dependent.** If any persisted
   checkpoint payload proves class-path-dependent (pickled) rather than
   portable, a serialization migration plan SHALL exist before Phase 2.5,
   because package renames would invalidate every persisted checkpoint.
   (AE-0075's current verdict is PORTABLE, so this gate is currently
   closed; it re-opens only if new evidence contradicts that verdict.)
2. **The `lock_version` activation strategy changes.** The recorded strategy
   is test/CI-only enforcement during Phase 2.5, with production activation
   shipping behind the first redirected carousel write path in Phase 4. If
   that activation strategy changes, Phase 2.5 SHALL NOT start until the
   corresponding plan section is revised.

## Consequences

**Good:**

- Business ownership is expressed by bounded-context modules; new modules can
  be added without editing unrelated domains.
- Boundaries become mechanically enforceable (Import Linter contracts,
  frontend boundary lint, fresh-migration CI).
- Single deployment is preserved; no distributed-transaction or service-mesh
  burden is incurred.
- The scaled-down track removes risk machinery that the pre-production
  context does not need, keeping the calendar realistic for a single
  contributor.
- Authorization gaps (workers, agent tools) and the carousel god-object are
  addressed deliberately rather than incidentally.

**Bad / costs:**

- Compatibility facades, the field-ownership map, and per-window discipline
  add real work during Phases 4-6.
- Manual constructor injection trades some boilerplate for the absence of a
  framework; the re-evaluation trigger exists precisely because that trade
  may not hold past five modules.
- The outbox decision is recorded but unbuilt until Phase 6; until then only
  the reorder fix protects event/database ordering, and only for the
  single-process deployment.

## Alternatives Considered

| Alternative | Why rejected |
|---|---|
| A. Repair global layers (more protocols, cleaner imports) | Business ownership stays scattered; every feature still spans global folders; `agents` stays ambiguous; new modules keep coupling to carousel. |
| C. Split into microservices | Distributed transactions, network contracts, deployment and observability burden, data duplication; current boundaries are not mature enough. Reject now. |
| `full` rollback track | Calibrated for production traffic and live user workflows that do not exist; would impose rollback drills, parity alerting, and mixed-version testing with no payoff for a pre-production single-user system. |
| DI framework (`dependency-injector`) up front | Adds a framework dependency mid-migration against the existing hand-rolled idiom; deferred behind the Section 9 re-evaluation trigger. |
| Build the durable outbox in Phase 0 | Out of proportion to the immediate ordering bug; the reorder fix closes the window for the single-process deployment, and the outbox is sequenced into Phase 6. |

## Related Decisions

- [ADR-002: Use LangGraph for Workflow Engine](0002-use-langgraph-for-workflow-engine.md)
- [ADR-004: Adopt Event-Driven Architecture](0004-adopt-event-driven-architecture.md)
- [ADR-007: Consolidate Carousel Pipelines Under DeepAgents](0007-consolidate-carousel-pipelines-under-deepagents.md)
- [ADR-008: Agentic Delivery Workflow](0008-agentic-delivery-workflow.md)
- [Domain Glossary and Context Map](../architecture/domain-glossary.md) (AE-0071)
- [Checkpoint and lock_version Inventory](../architecture/checkpoint-inventory.md) (AE-0075)
- Options and recommended plan:
  [`.agent/reports/domain-modularization.options.md`](../../.agent/reports/domain-modularization.options.md)
- Implementation interview record:
  [`.agent/reports/domain-modularization.interview.md`](../../.agent/reports/domain-modularization.interview.md)
- Concurrency contract and adversarial test matrix: **AE-0073** (referenced,
  not duplicated)

## Tags

#architecture #modular-monolith #ddd #bounded-contexts #migration #authorization #outbox #di
