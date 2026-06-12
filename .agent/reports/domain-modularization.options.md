# Alter-Ego Domain Modularization Options and Recommended Plan

**Mode:** architect-skill research/options
**Date:** 2026-06-11
**Related report:** `domain-modularization.research.md`
**Recommendation:** Option B, incremental domain-module-first modular monolith
**Skeptical review:** Round 1 `BLOCK` (codex) on 2026-06-11; Round 2 `WARN`
(OpenCode/kimi-k2.6) on 2026-06-12; Round 3 `PROCEED_WITH_CAUTION`
(OpenCode/kimi-k2.6) on 2026-06-12 with no BLOCKER findings; Round 4
(delta, interview amendments) `PROCEED_WITH_CAUTION` (OpenCode/kimi-k2.6)
on 2026-06-12, no BLOCKERs, all findings resolved — see
`domain-modularization.skeptical-review{,-r2,-r3,-r4}.md`
**Codebase verification:** 2026-06-12; core diagnosis confirmed against the
code, with corrections folded in below (see "Codebase Verification Findings")
**Implementation readiness:** Direction approved; Phase 0 may begin.
Phase 2.5 start is conditional on the Phase 0 evidence gates (rollback track
recorded, checkpoint serialization confirmed portable); Phases 4-8 remain
gated by the phase exit criteria below.

## Decision Drivers

The selected architecture must:

1. Allow new modules without broad changes to existing code.
2. Establish clear ownership and ubiquitous language.
3. Introduce ports and patterns where they reduce real coupling.
4. Keep existing URLs, database data, workflows, and frontend behavior working.
5. Avoid a whole-codebase rewrite.
6. Support FastAPI, SQLAlchemy, LangGraph/DeepAgents, Redis, and Next.js.
7. Preserve atomic design while aligning frontend and backend concepts.
8. Make dependency rules mechanically enforceable.
9. Coexist with the active AE-0040 refactor backlog.

## Option Matrix

| Option | Description | Benefits | Costs and risks | Effort | Verdict |
|---|---|---|---|---:|---|
| A. Repair global layers | Keep `domain/application/infrastructure/api/agents`; add more protocols and clean imports. | Lowest immediate churn; familiar layout. | Business ownership remains scattered; every feature still spans global folders; `agents` remains ambiguous; new modules keep coupling to carousel. | 3-6 weeks | Not recommended |
| B. Domain-module-first modular monolith | Introduce bounded-context packages with internal layers, public contracts, ports, adapters, compatibility facades, and gradual route redirection. | Expresses business ownership; preserves one deployment; supports incremental strangler migration; enforceable boundaries; frontend can share language. | Requires context mapping, temporary adapters, import migration, transaction cleanup, and disciplined sequencing. | 12-20 engineer-weeks | **Recommended** |
| C. Split services/microservices | Extract identity, knowledge, workflow, publishing, and agents into deployable services. | Strong runtime isolation and independent scaling. | Distributed transactions, network contracts, deployment overhead, observability burden, data duplication, and much higher migration risk. Current boundaries are not mature enough. | 6-12+ months | Reject now |

## Recommended Architecture

Choose Option B with these constraints:

- One backend deployment and one frontend deployment remain.
- PostgreSQL remains the authoritative store.
- Modules own models and behavior, but may initially share the same database.
- Existing API routes remain compatibility adapters.
- No dual writes without an explicit source-of-truth and reconciliation plan.
- Ports are introduced before physical moves.
- Context boundaries are tightened gradually through CI ratchets.
- Events are used for asynchronous integration, not ordinary local calls.

## Mandatory Amendments From Skeptical Review

The external cold critic identified three blockers. Option B remains the
recommended direction, but implementation must not begin until the following
policies are added to ADR-0009 and validated against the current system.

### 1. Resource authorization ownership

Identity owns authentication, actor identity, roles, sessions, and service
identities. It does not centrally own every resource authorization decision.

Each bounded context owns authorization policies for its resources:

| Context | Example decisions |
|---|---|
| Editorial | View or modify a project, submit review, assign reviewer |
| Carousel Presentation | View draft artifacts, request a rebuild |
| Publishing | Approve release, schedule, publish, unpublish |
| Knowledge | Read, upload, reprocess, or delete a document |
| Conversation | Read or append to a conversation |

Every inbound adapter must supply an `ActorContext` containing the authenticated
actor, roles, request/trace identity, and service identity when applicable.
The tenancy model must be explicitly documented; absence of multi-tenancy must
be an explicit constraint rather than an assumption.

Rules:

- Authorization is deny-by-default.
- HTTP routes, agent tools, workers, and event consumers call the same
  context-owned policy.
- Delayed destructive or publishing actions define whether authorization is
  captured at command acceptance or revalidated at execution.
- Revocation behavior is defined for queued and in-flight work.
- Contract tests cover owner, reviewer, admin, anonymous, service identity,
  revoked access, and cross-resource denial.

### 2. Single writer for the legacy carousel row

While `carousel_projects` remains shared persistence, it cannot be independently
written by editorial, presentation, and publishing modules.

During compatibility phases:

- `legacy.carousel_project` is the sole write owner of `carousel_projects`.
- New modules return decisions, state transitions, or artifact results to a
  legacy coordinator.
- A single legacy Unit of Work applies row changes and owns `lock_version`.
- A field-level ownership map identifies which logical context may propose each
  field change.
- Commands that affect multiple logical contexts are coordinated as one legacy
  aggregate transaction.
- New modules may own separate new tables only when those tables have one
  writer and an explicit consistency relationship to the legacy row.

Independent module write ownership begins only after the relevant fields move
to module-owned persistence or the old aggregate is intentionally retained as
a process manager.

Required artifact before Phase 4:

```text
docs/architecture/carousel-project-field-ownership.md
```

It must map every column, invariant, command owner, concurrency token, and
migration destination.

### 3. Rollback and forward-fix policy

Route rebinding is a valid rollback only for slices that have not changed
persisted semantics or emitted irreversible external effects.

Every phase requires a side-effect and compatibility ledger:

| Concern | Required decision |
|---|---|
| Database writes | Whether old code can read, ignore, or safely preserve them |
| Outbox events | Fence/version behavior during rollback |
| Projections | Rebuild, invalidate, or continue consuming |
| External publication | Compensating action or forward-fix only |
| Artifact builds | Retention and version compatibility |
| Checkpoints | Compatible reader/writer versions |
| Feature flags | Owner, expiry, and safe deployment order |

Before redirecting production traffic:

- Define the rollback window.
- Test rollback with production-shaped data.
- Verify old code against all data written by the new path.
- Define event fencing and relay behavior.
- Define when rollback is prohibited and forward-fix is mandatory.
- Record automated rollback signals and the human decision owner.

## Codebase Verification Findings (2026-06-12)

A repository-wide verification pass checked the research report's claims
against the actual code (backend, frontend, CI, ticket board). The diagnosis
is sound: the Import Linter blanket exemptions, `get_container()` service
location from application code, mixed commit ownership (repositories, routes,
and services), the `CarouselProject` god object, dual blog representations,
the bidirectional `agents`/`application` dependency, missing frontend
boundary rules, and the absence of any outbox were all confirmed in code.
Two findings were stronger than the research stated:

- The frontend has **two different hooks both named `useBlogPosts()`** —
  `features/blog/hooks/use-carousel-blog.ts` fetches completed carousel
  projects while `use-blog-posts.ts` manages first-class blog posts, and the
  public `/blog` route renders carousel projects. The `CarouselArticle` vs
  `BlogPost` split is mandatory, not cosmetic.
- Background workers (`application/workers/workflow_workers.py`) access the
  database and services with **no authorization at all**, confirming that
  amendment 1's `ActorContext` requirement for non-HTTP entry points
  addresses a real gap, not a hypothetical one.

### Corrections to the plan

1. **Frontend baseline does not reproduce.** The research reports 406 TS/TSX
   files / 41,638 lines and 15,036 lines across the
   create/carousel/publish/blog/workflow features. A 2026-06-12 measurement
   found ~305 non-test files / ~25,700 lines, with those five features
   summing to ~6,100 non-test lines (create 2,093, blog 2,064, publish 1,077,
   workflow 752, carousel 133). The frontend baseline must be re-measured
   with a documented methodology before Phase 7 and the overall estimate are
   re-confirmed. Backend numbers reproduce within drift (367 files; carousel
   services 12,405 lines).
2. **No document/search Gherkin scenarios exist.** The repository has only
   five `.feature` files (three carousel, one blog integration, one anonymous
   chat). The original Phase 2 exit gate assumed a safety net that is not
   there; Phase 2 now includes writing those scenarios as a deliverable.
3. **`lock_version` is a dead column.** It exists on `carousel_projects` and
   `blog_posts` (migration 0002) but no application code enforces it. The
   research's "the ORM adds optimistic locking" overstates reality. Phase 2.5
   must implement expected-version enforcement before it can exercise
   conflict behavior.
4. **The AE-0040 interaction table was stale.** AE-0058 through AE-0067 are
   already DONE and merged; the live blockers are AE-0044/0045/0046 (Intake,
   blocked by AE-0041), which touch the same carousel service files as
   Phases 4-5. The interaction section below has been regenerated from the
   board.
5. **No fresh-migration CI job exists.** The success metric "fresh PostgreSQL
   migration succeeds in CI" is new work; it is now an explicit Phase 1
   deliverable.

### Mandatory amendment 4: operating-context calibration

This is a single-contributor project (confirmed by git history). The
two-engineer track is moot, and several skeptical-review requirements —
production-shaped rollback drills, legacy/new parity metrics with alert
thresholds, automated disable criteria, mixed-version deployment testing —
are calibrated for a team operating a system with production traffic and
in-flight user workflows. The skeptical reviewer had no repository access and
could not make this call.

ADR-0009 must therefore **open with an operating-context statement**: actual
users, traffic, count of in-flight LangGraph checkpoints, and the tenancy
model (expected: single-tenant, stated as an explicit constraint). Then:

- If there is meaningful production usage and live checkpoints, the full
  rollback/parity machinery in amendments 1-3 applies unchanged.
- If the system is effectively pre-production or low-traffic, the
  field-ownership map, deny-by-default authorization, and single-writer rule
  remain mandatory, but rollback drills may be scaled down to database
  backup + fresh-migration test + checkpoint fixture replay, and the
  per-slice parity/alerting requirements may be replaced by trace-correlated
  smoke comparisons. The scaled-down choice must be recorded in ADR-0009 so
  the second cold review can judge it explicitly rather than re-raise it.

### Immediate fix independent of this plan

`workflow_event_service.py` publishes the workflow event to Redis **before**
the audit row is flushed, and commit belongs to the caller. A rollback after
publish leaves the external stream inconsistent with the database. This is a
live correctness bug, not an architecture smell.

**Committed fix (decided 2026-06-12, round-2 review finding 4):** Phase 0
implements the **reorder-only** change — persist and commit the audit row,
then publish to Redis (~1 day, plus a test covering rollback-after-commit
ordering). The durable outbox is **not** built in Phase 0; it remains a
Phase 6 deliverable designed under "Outbox delivery semantics" below. The
reorder fix closes the inconsistency window for the current single-process
deployment; it deliberately does not provide at-least-once delivery or
replay — those properties arrive with the Phase 6 outbox. This keeps
Phase 0 at 3-5 days.

## Interview Decisions (2026-06-12)

A structured implementation interview with the owner (protocol:
grill-with-docs; full record:
`.agent/reports/domain-modularization.interview.md`) settled the open
Human Checkpoint questions and the operating context. These decisions
amend the plan as follows.

### Operating context and track (settles amendment 4)

**Pre-production, single user, no external consumers.** The recorded
track is **scaled-down + migrate-in-place**:

- Tables, columns, and API responses MAY be renamed/reshaped during
  Phases 4-6 via data-preserving Alembic migrations, with the frontend
  updated in the same phase. No external clients exist to break.
- The legacy ACL, permanent sole-writer coordinator, and frozen-schema
  rules shrink to **per-migration-window discipline**, defined precisely
  (round-4 review finding 4): a migration window is the wall-clock span
  from a schema-modifying Alembic revision landing to its phase exit
  gate passing, with a **ceiling of 2 calendar weeks**; during a window
  the affected table has **exactly one writer — the single module
  performing the migration (or the legacy coordinator where one still
  exists); direct writes from a second module to the same table are
  prohibited even inside a window**. This preserves the round-1
  single-writer blocker mitigation in time-boxed form. Every window has
  a reversible path (backup + tested downgrade); no long-lived dual
  representations.
- **Drain-before-migrate (round-4 finding 2):** finish-on-old-code and
  schema migration share an ordering constraint — old code cannot finish
  a workflow against a migrated schema. Therefore, before any
  schema-modifying migration, live checkpoints are drained: finished on
  the pre-migration code, or restarted with documented owner consent
  (restart preferred when finishing would delay the window). This step
  is mandatory, not advisory, and appears in the Phase 4+ exit gates.
- The `carousel_projects` field-ownership map (Phase 2.5 core) is
  retained and **repurposed as the migration map**: every column's
  destination module and migration step, rather than a permanent
  shared-row treaty.
- LangGraph checkpoint policy is **finish-or-restart**: in-flight
  workflows are finished on the old code or restarted with the owner's
  consent; no cross-version checkpoint migration tooling is built.
  AE-0075's serialization escalation is downgraded accordingly — a
  CLASS-PATH-DEPENDENT verdict informs the restart policy instead of
  blocking Phase 2.5.
- Phase 2.5 contingent layer: scaled-down items apply (restore drill,
  fixture replay, smoke comparison); the deferred full-track items move
  to the Phase 4 gate as already specified.

### Modeling decisions (settle the Human Checkpoint)

1. Aggregate name: **EditorialProject**.
2. Blog: **one BlogPost aggregate** (`blog_posts`-backed) with
   `origin: carousel | standalone`; Phase 6 migrates embedded
   `blog_markdown`/translations into `blog_posts` rows and drops the
   embedded columns. `CarouselArticle` is rejected — no second blog
   representation survives. One `useBlogPosts()` hook remains.
3. Persona/Quality: **two contexts** — `persona` and `quality`.
   **Persona owns VoiceScore and enforcement**; quality consumes via
   persona's public contract (dependency direction: quality → persona).
4. Editorial Operations: **full module** owning notification dispatch
   and board/calendar behavior from day one; its views remain
   event-built read models, never direct joins into other contexts'
   tables.
5. Conflict policy (feeds AE-0073, now decided not draft): expected
   version on mutating endpoints, **HTTP 409 with machine-readable
   body + UI refresh prompt**, idempotency keys on workflow commands.
6. AE-0074 addendum: the unused `stream_entry_id` column is **dropped**
   via migration as part of the reorder fix.

The Proposed Contexts table earlier in this document is amended by
these decisions: read `persona_quality` as two rows (`persona`,
`quality`) and `editorial_operations` as a full supporting module.

### Calendar reforecast (with scope-delta math, round-4 finding 3)

Owner bandwidth is **~5-10 hours/week** (review, decisions, testing on
top of agent-driven implementation). Tickets run in **one serial lane**,
PRs stay small, and CI gates substitute for review depth.

The interview decisions change scope in both directions; the line items
(rough engineer-weeks, ew):

| Delta | Effect |
|---|---:|
| Migrate-in-place: legacy ACL, route facades, long-lived compatibility repositories, Phase 8 compatibility removal shrink | −2 to −3 ew |
| Finish-or-restart: cross-version checkpoint replay deleted from Phase 2.5 | −0.5 to −1 ew |
| Persona/Quality split: second module bootstrap, public API, contract tests, boundary rules, dependency-direction test | +0.5 to +1 ew |
| Editorial Operations as full module: notification dispatch handlers/adapters, board/calendar rules as owned behavior (was: read views, ~2-3 days) | +1 to +2 ew |
| Net | approximately −1 to +0 ew |

Both deviations (split and full module) are deliberate owner decisions,
recorded as **must-haves**; the cost is priced here rather than reverted.
Revised totals: **11-21 engineer-weeks**, calendar **realistically 8-14
months** at 5-10 h/week (the previous 6-12 month figure assumed the
round-3 scope without the additions; the offsets keep the floor near 8).

**Mid-point go/no-go (round-4 residual risk 3):** at the Phase 3 exit
gate or month 6, whichever comes first, the owner runs an explicit
continue/re-scope/stop review against this table and records the
decision in the AE-0070 epic log. A nights-and-weekends project of this
length needs a scheduled exit ramp, not an implicit one.

### Review-trail note

These amendments postdate the round-3 `PROCEED_WITH_CAUTION` verdict and
were delta-reviewed in **round 4 (2026-06-12, OpenCode/kimi-k2.6):
`PROCEED_WITH_CAUTION`, no BLOCKERs** — see
`domain-modularization.skeptical-review-r4.md`. All four round-4
findings are resolved in this revision (replay deletion, drain rule,
migration-window definition, scope-delta pricing); the decision log
below records dispositions. ADR-0009 (AE-0072) transcribes every
decision above.

### Round-4 skeptical review decision log (2026-06-12, verdict PROCEED_WITH_CAUTION)

| Finding | Severity | Disposition | Closure criterion |
|---|---|---|---|
| Phase 2.5 checkpoint replay valueless under finish-or-restart | WARN | Accepted; replay deleted, checkpoint capture is inventory-only with per-workflow finish cost; idempotency proven via direct command tests | Phase 2.5 deliverables and exit gate updated |
| Finish-on-old-code vs schema migration ordering gap | WARN | Accepted; mandatory drain-before-migrate step added (restart preferred, documented consent), Phase 4+ exit-gate criterion and rollout rule 10 | Drain rule present in track definition, Phase 4 gate, rollout rules |
| Persona/quality split + editorial_operations module scope unpriced | WARN | Accepted; line-item delta table published, totals revised to 11-21 ew / 8-14 months, deviations recorded as must-haves, mid-point go/no-go added | Scope-delta table and go/no-go milestone in calendar section |
| "Migration window" / one-writer underspecified | INFO | Accepted; window defined (revision-to-gate, 2-calendar-week ceiling, exactly one writer per table, second-module writes prohibited) | Definition in track bullets; ADR-0009 transcribes |

## Required Supporting Designs

Each supporting design is owned by a specific phase with a timebox
(round-2 review finding 3 — designs must not float unassigned):

| Design | Drafted in | Validated in | Timebox |
|---|---|---|---|
| Outbox delivery semantics | Phase 0 (ADR section, decision only) | Phase 6 (implementation) | 2 days draft; implementation inside Phase 6 |
| Workflow checkpoint compatibility | Phase 0 (preliminary inventory) | Phase 2.5 (fixture replay) | 1 day inventory; replay inside Phase 2.5 core |
| Concurrency contract | Phase 0 (draft) | Phase 2.5 (`lock_version` tests) | 1 day draft |
| Operational equivalence | Phase 0 (track choice via amendment 4) | Per redirect slice, Phases 3-6 | Defined per slice before its redirect |
| Adversarial test matrix | Phase 0 (matrix skeleton) | Incrementally at each phase exit gate | Per-phase rows only; never a standalone multi-week effort |

Known input for the checkpoint inventory (2026-06-12 verification): the
checkpointer backend is configurable in `api/app.py` (postgres, sqlite,
memory, disabled) and the serialized `CarouselWorkflowState` carries **no
version field** — the compatibility strategy must add explicit versioning
rather than assume it exists.

Phase-gate re-read rule: before each phase exit, re-read the decision-log
closure criteria for every finding whose closure lands in that phase and
record confirmed/at-risk in the decision log. **If testing or design scope
threatens the calendar, the phase is delayed — the testing is not descoped.**

### Outbox delivery semantics

ADR-0009 or a linked ADR must define:

- PostgreSQL outbox as the durable delivery source.
- Stable event IDs and aggregate sequence numbers.
- At-least-once delivery expectations.
- Persistent consumer deduplication.
- Relay concurrency and ordering rules.
- Retry limits, poison-event quarantine, and operational replay.
- Retention and schema compatibility.
- Redis publication as transport, not proof of durable consumption.

### Workflow checkpoint compatibility

Before changing carousel workflow packages:

- Inventory persisted checkpoint backends and workflow versions.
- Capture sanitized production-shaped checkpoint fixtures.
- Version workflow definitions and serialized state.
- Test old checkpoint resume on new code.
- Test mixed-version deployment and rollback.
- Define behavior for unsupported checkpoints: migrate, finish on legacy code,
  or restart with explicit user consent.
- Fence idempotent external side effects during replay.

### Concurrency contract

Commands must specify:

- Aggregate or legacy-row expected version.
- Idempotency key for retried operations.
- Which operations require serialization.
- Conflict response and client retry behavior.
- Artifact build deduplication.
- Projection freshness requirement.
- Whether publication is allowed from stale content.

### Operational equivalence

Each redirected slice needs:

- Legacy/new path correlation using one trace ID.
- Success, error, and latency parity metrics.
- Domain-specific semantic comparison.
- Alert thresholds and automated disable criteria.
- Deployment order for mixed versions.
- Feature-flag owner and removal deadline.

### Adversarial test matrix

Phase exit gates must include:

- Authorization bypass attempts.
- Duplicate commands and duplicate events.
- Concurrent updates and expected-version conflicts.
- Transaction cancellation between state and outbox writes.
- Event replay, poison events, and relay restart.
- Partial AI, rendering, storage, vector, and publishing vendor failure.
- Stale read models.
- Rolling deployment and rollback.
- Resume of checkpoints written by prior versions.
- Exactly-once business effects under at-least-once execution.

## Proposed Contexts

| Module | Classification | Initial ownership |
|---|---|---|
| `editorial` | Core | EditorialProject, brief, source material, workflow, review, assignment, revision, approval |
| `carousel_presentation` | Core | CarouselPresentation, slides, layout, design, images, validation, rendering, artifact builds |
| `persona_quality` | Core differentiator | PersonaProfile, corrections, VoiceScore, QualityRubric, evaluation |
| `publishing` | Supporting | BlogPost, CarouselArticle projection, publication visibility, scheduling, Instagram, LinkedIn, captions, SEO |
| `knowledge` | Supporting | KnowledgeDocument, ingestion, chunks, indexing, retrieval, search |
| `conversation` | Supporting | Conversation, Message, chat streaming, citations, assistant interaction |
| `editorial_operations` | Supporting/read side | Board, calendar, notifications, audit, analytics |
| `identity` | Generic | User, Role, Session, credentials, authentication, authorization |
| `platform` | Technical | Database engine, settings, Redis transport, logging, tracing, cache, vendors, file storage |

## Target Backend Tree

```text
backend/src/rag_backend/
  bootstrap/
    app.py
    lifecycle.py
    routes.py
    container.py

  modules/
    editorial/
      domain/
        project.py
        workflow.py
        review.py
        events.py
      application/
        commands/
        queries/
        handlers/
        dto.py
      ports/
        repositories.py
        quality.py
        knowledge.py
        events.py
      adapters/
        inbound/http/
        inbound/agents/
        outbound/persistence/
        outbound/workflow/
      contracts/
        events.py
        queries.py
      public.py
      bootstrap.py

    carousel_presentation/
      domain/
        presentation.py
        slide.py
        policy.py
        build.py
      application/
        commands/
        queries/
        handlers/
        strategies/
      ports/
        image_generator.py
        artifact_store.py
        renderer.py
      adapters/
        inbound/http/
        outbound/persistence/
        outbound/images/
        outbound/playwright/
      contracts/
      public.py
      bootstrap.py

    persona_quality/
    publishing/
    knowledge/
    conversation/
    editorial_operations/
    identity/

  platform/
    config/
    database/
    events/
    observability/
    cache/
    ai/
    storage/

  legacy/
    carousel_project/
```

## Target Frontend Tree

Use either `modules/` or retain `features/`; use the same bounded-context names:

```text
frontend/src/
  app/                           # routing and composition only

  modules/
    editorial/
      api/
      contracts/
      workspace/
      workflow/
      sources/
    carousel-presentation/
      api/
      contracts/
      preview/
      review/
      refinement/
    persona-quality/
    publishing/
      blog/
      distribution/
      scheduling/
    knowledge/
    conversation/
    editorial-operations/
    identity/

  components/
    atoms/
    molecules/
    organisms/
    layout/
    providers/

  platform/
    api/
    query/
    i18n/
    telemetry/
```

Atomic design remains a presentation taxonomy. It should not compete with
domain ownership:

- Generic `NeonButton` stays in atoms.
- Generic `NeonCard` stays in molecules.
- `PersonaCard` belongs to `persona-quality`.
- `BlogPostCard` belongs to `publishing/blog`.
- A route-aware workflow board belongs to `editorial-operations`.

## Module Contract Rules

Each module exposes only:

```text
<module>/public.py
<module>/contracts/
```

Allowed:

```python
from rag_backend.modules.knowledge.public import SearchKnowledge
from rag_backend.modules.editorial.contracts.events import ProjectApproved
```

Forbidden:

```python
from rag_backend.modules.knowledge.adapters.outbound.persistence import ...
from rag_backend.modules.editorial.domain.project import EditorialProject
```

The second form is forbidden outside the owning module unless explicitly
declared as part of a shared contract.

## Composition Root

Move global wiring to `rag_backend/bootstrap`.

Responsibilities:

- Construct module bootstraps.
- Bind ports to concrete adapters.
- Register FastAPI routers.
- Start/stop database, workers, telemetry, and checkpointers.
- Supply settings and request-scoped units of work.

Application and agent code must never call the global container.

Each module may expose:

```python
def bootstrap_module(platform: PlatformServices) -> ModuleRuntime: ...
```

The global composition root combines returned routers, handlers, workers, and
event subscriptions.

### Dependency injection mechanism (decided 2026-06-12)

Wiring is **manual constructor injection** — no DI framework. This matches
the existing hand-rolled container idiom and avoids adding a framework
dependency mid-migration:

- `bootstrap_module(platform: PlatformServices)` receives platform services
  and constructs the module's adapters and handlers explicitly.
- The request-scoped Unit of Work is created by an inbound dependency
  provider (FastAPI `Depends` at the HTTP edge; explicit construction in
  workers and agent adapters) and passed to handlers as a constructor or
  call argument — never resolved from a global.
- Test doubles are swapped by constructing the module bootstrap with fake
  ports; no container patching.

Re-evaluation trigger: if, after the fifth migrated module, composition-root
wiring becomes a maintenance burden (measured by bootstrap line count and
duplication), evaluate `dependency-injector` or similar via a lightweight
ADR. Until that trigger fires, introducing a framework is out of scope. This
decision is recorded in ADR-0009 so it is explicit and reversible.

## Transaction and Event Policy

### Unit of Work

- One application command owns one unit of work.
- Repository adapters flush but do not commit.
- The handler commits on success and rolls back on failure.
- Query handlers use read-only sessions or projections.

### Cross-context events

- Persist state and outbox event in one PostgreSQL transaction.
- Dispatch outbox records to Redis after commit.
- Consumers are idempotent.
- Integration event schemas live in `contracts/events.py`.
- Internal domain events remain private to the module.

Do not require events for simple synchronous in-process queries.

## Legacy Carousel Anti-Corruption Layer

The first compatibility layer should translate the existing aggregate without
changing storage:

```text
carousel_projects row
  -> EditorialProjectSnapshot
  -> CarouselPresentationSnapshot
  -> DistributionPackageSnapshot
```

Initial rules:

1. `carousel_projects` remains the write authority.
2. New modules read through a compatibility repository.
3. Existing `/api/carousels/*` routes call new application handlers.
4. Existing response schemas remain stable.
5. New domain language is used internally.
6. A later migration may split tables after behavior and ownership stabilize.

Special handling is required for:

- LangGraph checkpoint thread IDs and node/state compatibility
- `blog_markdown` versus first-class `blog_posts`
- `is_public` versus editorial approval
- Artifact paths and build versions
- Existing SSE event names
- Owner/reviewer access checks

## Phased Migration Plan

### Phase 0: Establish language and constraints

**Duration:** 1-2 weeks (was 3-5 days; grew to absorb the supporting-design
drafts and decisions added by the round-2 review — see the timebox table in
"Required Supporting Designs")

Deliverables:

- Run a focused event-storming/context-mapping workshop.
- Accept or revise the proposed bounded contexts.
- Produce a glossary shared by backend, frontend, tests, and docs.
- Draft ADR-0009, opening with the operating-context statement
  (amendment 4) that calibrates rollback and parity requirements, and
  **recording the rollback track choice** (full vs scaled-down) that
  parameterizes the Phase 2.5 exit gate.
- Record the DI wiring decision (manual constructor injection; see
  "Dependency injection mechanism") in ADR-0009.
- Draft the outbox delivery semantics ADR section (decision only;
  implementation stays in Phase 6).
- Draft the concurrency contract and the adversarial test matrix skeleton.
- Produce the preliminary checkpoint inventory (backends in use, count of
  live checkpoints, absence of state versioning) and **determine the
  checkpoint serialization format**. Preliminary signal (2026-06-12):
  `CarouselWorkflowState` is a `TypedDict` and no custom serde is
  configured, so LangGraph's default `JsonPlusSerializer` applies —
  portable for primitive values. Phase 0 must confirm with a real captured
  checkpoint that no class-path-dependent (pickled) values are stored.
  **Escalation rule (round-3 review):** if any checkpoint payload proves
  class-path-dependent, Phase 2.5 must not start until a serialization
  migration plan exists, because package renames would invalidate every
  persisted checkpoint.
- Freeze the SSE event name inventory. **Location correction
  (2026-06-12, ticket validation):** the names live in three backend
  modules — carousel SSE names in
  `application/services/carousel/editorial_workflow_sse_constants.py`
  (note: application layer), chat SSE names in
  `domain/constants/chat_stream.py`, and Redis event types in
  `domain/constants/workflow_events.py` — and the frontend mirrors them
  in its own `EDITORIAL_WORKFLOW_SSE_EVENTS` constants map rather than
  raw literals. Phase 0 records the full list, declares the strings
  frozen across all migration phases, and adds contract tests comparing
  both constant sets to one committed inventory so CI fails if any value
  drifts (round-3 review finding 3; AE-0076).
- Publish a deliverable-level time budget for this phase on day one;
  items that do not fit the 2-week box move to a named Phase 0b rather
  than silently extending Phase 0 (Phase 2.5 cannot start before the track
  choice lands, so Phase 0 slippage is plan-level slippage).
- Fix the workflow event ordering bug in `workflow_event_service.py`
  (reorder-only: persist + commit before Redis publish; outbox stays in
  Phase 6) — immediate fix, independent of modularization.
- Re-measure the frontend baseline with a documented methodology and
  re-publish the overall estimate with a confidence range.
- Record current import violations and public contracts.
- Define migration invariants and rollback criteria.

Exit gate:

- Context map accepted.
- `Carousel`, `EditorialProject`, `BlogPost`, `Publication`, `Workflow`,
  `Source`, and status terms have unambiguous definitions.

### Phase 1: Add architecture scaffolding without moving behavior

**Duration:** 4-7 days

Deliverables:

- Add `bootstrap/`, `modules/`, `platform/`, and `legacy/` package roots.
- Move only composition-root responsibilities, not business logic.
- Add module public API conventions.
- Add exact Import Linter contracts.
- Replace wildcard exemptions with a generated baseline exception list.
- Add frontend module boundary lint rules (none exist today; current ESLint
  only blocks feature/component imports of `app/**`, not cross-feature
  imports).
- Add a fresh-database `alembic upgrade head` migration job to CI (does not
  exist today).
- Add CI architecture reports and violation ratchets.

Exit gate:

- Existing tests pass.
- Existing routes are unchanged.
- New code cannot create additional global-layer violations.

### Phase 2: Pilot the Knowledge module

**Duration:** 1-2 weeks

Why first:

- The concept is comparatively cohesive.
- Repository, processor, vector, and retrieval protocols already exist.
- It exercises HTTP, persistence, vendor adapters, ports, and tests without
  touching the largest workflow.

Deliverables:

- Write document/search Gherkin scenarios **first** — none exist today (the
  repository's five `.feature` files cover carousel, blog integration, and
  anonymous chat only). These scenarios are the behavioral safety net for
  the rest of this phase.
- Define `KnowledgeDocument`, commands, queries, and repository/search ports.
- Repair full-field ORM mappings.
- Introduce a request-scoped Unit of Work.
- Move document routes behind application handlers one endpoint at a time.
- Keep `/api/documents` and `/api/search` unchanged.
- Add fake and PostgreSQL repository contract tests.
- Redirect conversation search through the knowledge public facade.

Exit gate:

- No knowledge application code imports SQLAlchemy, FastAPI, Pinecone, or the
  global container.
- The document/search Gherkin scenarios written at phase start pass.
- The module template is documented and reusable.

### Phase 2.5: Carousel risk spike

**Duration:** 1-2 weeks for the core layer; up to 3-4 weeks total if the
full operational track applies. **Precondition:** the rollback track (full
vs scaled-down, amendment 4) is recorded in ADR-0009 during Phase 0 —
Phase 2.5 must not start with an ambiguous exit gate.

This spike is mandatory because the Knowledge pilot does not exercise the
highest-risk characteristics of the legacy carousel aggregate. Round-2
review findings 1 and 2 split it into a track-independent core and a
track-contingent layer.

Core deliverables (mandatory regardless of track):

- Complete the `carousel_projects` field-level ownership map.
- Introduce no production write redirection.
- Build a read-only compatibility adapter that produces editorial,
  presentation, and publishing snapshots from production-shaped rows.
- Capture sanitized workflow checkpoints **for inventory purposes only**
  (round-4 review finding 1): confirm serialization format, count live
  checkpoints with an owner-estimated finish cost per workflow, and
  document the state fields. The former cross-package replay requirement
  is deleted — under the finish-or-restart policy the old-to-new resume
  path never executes in production, so a replay test proves nothing the
  inventory does not.
- Implement expected-version enforcement for the legacy `lock_version`
  column (it exists since migration 0002 but no application code checks it
  today), then exercise conflict behavior against it. This is new scope, not
  a test of an existing mechanism.
  **Rollout strategy (round-3 review finding 1):** enforcement is
  **test/CI-only during Phase 2.5** — no production write path changes
  behavior, preserving the "no production write redirection" rule.
  Production activation ships with the first redirected carousel write path
  in Phase 4, behind that slice's feature flag. No backfill migration is
  needed: migration 0002 created the column `NOT NULL` with
  `server_default="1"`, so every production row already carries a version;
  the Phase 0 inventory records the value distribution for the conflict-test
  fixtures.
- Prove duplicate artifact-build and resume commands have one business
  effect via **direct command tests** with idempotency keys per the
  AE-0073 contract (not via checkpoint replay — round-4 finding 1).

Contingent deliverables (selected by the ADR-0009 track):

- **Full track** (production traffic / live checkpoints): authorization
  policy contract tests through HTTP, agent-tool, and worker entry points;
  rollback drill with compatibility data, events, projections, and
  checkpoints.
- **Scaled-down track** (pre-production / low traffic): database restore
  drill, checkpoint fixture replay, and a trace-correlated smoke comparison.
  The full-track items move to the Phase 4 exit gate (they must exist before
  the first carousel write redirection, not before the spike concludes) —
  this deferral does not reintroduce the round-1 blockers because no write
  path is redirected in Phases 2.5-3.

The 1-2 week core estimate is **aspirational; 3 weeks is the committed
ceiling** (round-3 review finding 2). The expected long pole is the
field-level ownership map (every column traced to its write sites); if it
alone consumes a full week, the remaining core items still fit the ceiling
because the compatibility adapter and conflict tests build directly on its
output.

Overrun circuit-breaker: if the core layer exceeds **3 weeks**, work pauses
for an explicit checkpoint decision — continue, re-scope, or re-sequence —
recorded in the decision log. Silent absorption of the delay is not an
option. Recovery rules (round-3 review finding 4):

- **Continue** → the total estimate is revised by the measured delta and
  re-published; later phases are not silently compressed.
- **Re-scope** → the only droppable core item is the duplicate-command
  idempotency proofs, because Phase 4's adversarial test matrix re-exercises
  them against real write redirection; if dropped, they are named in the
  Phase 4 exit gate. The field ownership map, compatibility adapter,
  checkpoint replay, and `lock_version` enforcement are non-droppable.
- **Re-sequence** → the moved deliverable is named in the receiving phase's
  exit gate, mirroring the scaled-down-track deferral mechanism.

Exit gate (parametric on the ADR-0009 track):

- Core: field ownership map approved; compatibility adapter snapshots match
  production-shaped rows; checkpoint inventory complete (format verdict,
  live count, per-workflow finish cost); `lock_version` conflict and
  duplicate-command tests pass; legacy code safely reads or ignores every
  artifact produced by the spike.
- Full track adds: three-entry-point authorization evidence and the full
  rollback drill.
- Scaled-down track adds: restore drill, fixture replay, and smoke
  comparison, with the deferred full-track items scheduled as named Phase 4
  exit-gate criteria.
- No write path is redirected until a cold review returns WARN or
  PROCEED_WITH_CAUTION against the evidence for the recorded track.

### Phase 3: Extract Identity and Conversation boundaries

**Duration:** 1-2 weeks

Deliverables:

- Move auth/admin business rules into identity application handlers.
- Keep role checks in shared identity contracts, not route modules.
- Move conversation/message streaming use cases into the conversation module.
- Define a consumer-owned `KnowledgeSearchPort`.
- Make chat agent construction an adapter behind conversation/application
  contracts.
- Preserve existing cookies, tokens, URLs, and stream payloads.

Exit gate:

- API routes are thin adapters.
- Conversation does not import concrete Postgres repositories.
- Identity persistence is not accessed directly by unrelated routes.

### Phase 4: Introduce EditorialProject facade over CarouselProject

**Duration:** 1-2 weeks

Deliverables:

- Define `EditorialProject`, `EditorialWorkflow`, and workflow status language.
- Implement the legacy carousel ACL.
- Route workflow start/state/resume through editorial handlers.
- Keep LangGraph checkpoint identifiers and schemas stable.
- Move source material, assignments, review decisions, and optimistic locking
  behind editorial ports.
- Separate approval from public release at the contract level.

Exit gate:

- Existing carousel workflow API and SSE behavior remain unchanged.
- Editorial handlers do not import carousel ORM models directly.
- The compatibility adapter is the only module translating legacy project
  persistence into editorial concepts.
- If the scaled-down track was recorded in ADR-0009, the deferred
  full-track evidence (three-entry-point authorization contract tests and
  the full rollback drill) is complete before any carousel write path is
  redirected.
- **Checkpoint drain (round-4 findings 1-2):** before any schema-modifying
  migration in this phase, every live checkpoint from the Phase 2.5
  inventory was either finished on the pre-migration code or restarted
  with documented owner consent. No schema migration runs while a
  checkpoint references the old shape.

### Phase 5: Extract Carousel Presentation

**Duration:** 2-3 weeks

Deliverables:

- Move slides, presentation policy, layout strategies, validation, rendering,
  image generation, artifact builds, and export behind presentation contracts.
- Convert concrete agents/vendors into adapters implementing ports.
- Preserve presentation response schemas and artifact URLs.
- Keep existing strategy and builder tasks aligned with the new module.
- Establish format-extension contracts for future formats.

Suggested extension point:

```python
class ContentFormatProducer(Protocol):
    format_name: str

    async def produce(self, command: ProduceFormat) -> ProducedArtifact: ...
```

Do not add a generic format framework until a second format needs the same
contract. Initially, keep this as a presentation-specific boundary.

Exit gate:

- Carousel means presentation only.
- Editorial workflow invokes presentation through a port/public facade.
- Presentation does not own blog, publishing, persona, or workflow state.

### Phase 6: Separate Publishing, Blog, and Distribution

**Duration:** 1-2 weeks

Deliverables:

- Select the authoritative model for carousel-derived articles versus
  first-class `BlogPost`.
- Move public visibility and scheduling into publishing.
- Move captions, Instagram, LinkedIn, SEO, and channel delivery into
  publishing/distribution.
- Build public blog, calendar, board, and analytics from read models.
- Add transactional outbox for release events.

Exit gate:

- Editorial approval never automatically publishes.
- `BlogPost` and `CarouselArticle` are unambiguous.
- Public routes read publication projections, not editorial aggregates.

### Phase 7: Align the frontend

**Duration:** 1-2 weeks, partially parallel with phases 4-6

Deliverables:

- Reorganize features by accepted context names.
- Move workspace code under editorial.
- Move presentation review/refinement under carousel presentation.
- Consolidate persona/personas.
- Move business-specific components out of global atomic folders.
- Co-locate API/Zod/query contracts per module.
- Add OpenAPI/schema drift checking.
- Keep App Router URLs unchanged.

Exit gate:

- Backend and frontend use the same glossary.
- Route pages are thin composition components.
- Feature internals cannot cross-import without a public contract.

### Phase 8: Remove legacy layers and adapters

**Duration:** 1-2 weeks after production observation

Deliverables:

- Remove unused compatibility imports and re-exports.
- Remove global application/domain/infrastructure files only after ownership
  has moved.
- Split persistence tables only if independent ownership provides measurable
  value.
- Remove stale handwritten API contract sections.
- Delete exact Import Linter exceptions as violations reach zero.

Exit gate:

- No production import uses legacy module paths.
- Migration and rollback are proven.
- Architecture rules pass without broad ignores.

## Effort Estimate

### One senior engineer

| Scope | Estimate |
|---|---:|
| Language, authorization, ADR, guardrails, and scaffolding | 2-3 weeks |
| Knowledge pilot | 1-2 weeks |
| Carousel risk spike (core 1-2; up to 4 on the full track) | 1-4 weeks |
| Identity and conversation | 1-2 weeks |
| Editorial facade and workflow | 1-2 weeks |
| Carousel presentation extraction | 2-3 weeks |
| Publishing and frontend alignment | 2-3 weeks |
| Coexistence verification and rollback drills | 1-2 weeks |
| Legacy cleanup | 1-2 weeks |
| Total | 12-22 engineer-weeks |

The total is **preliminary, ±25%**, until the Phase 0 frontend baseline
re-measurement is published; the estimate is then re-issued with a
confidence range (round-2 review finding 6).

> **Superseded by baseline 2026-06 (AE-0077):** the re-measurement
> (`.agent/reports/modularization-baseline-2026-06.md`,
> `scripts/metrics/baseline_loc.sh`) found frontend production code is
> 300 files / 25,403 lines (the research's 41,638 figure included tests
> and stories — a classification omission, not a measurement error) and
> the five plan-named features total 6,119 production lines. Phase 7's
> 1-2 week sizing is confirmed. **Revised estimate: 11-21
> engineer-weeks, confidence ±15%.** The ±25% bracket above is retained
> as round-2 review-closure evidence.

Approximate effort composition across the total: design/ADR/guardrails
~25%, testing and verification ~35%, behavior moves ~30%, cleanup ~10%.
Testing is deliberately the largest share and is protected by the
phase-gate rule: if testing scope threatens the calendar, the phase is
delayed, not the testing descoped (round-2 review finding 3).

### Calendar reality (single contributor)

Git history confirms a single contributor. The two-engineer track below is
retained only for the case where a second engineer joins; it is not the
planning basis. At 12-20 engineer-weeks, the realistic calendar duration is
**approximately 3-5 months of one person's time**, competing with feature
work and the AE-0040 backlog. Two consequences:

- The estimate must be re-confirmed after the frontend baseline is
  re-measured (correction 1) and after Phase 2.5 produces measured evidence.
- If the operating-context statement (amendment 4) supports the scaled-down
  rollback/parity track, Phases 2.5 and the per-slice operational
  equivalence work shrink materially; the estimate should be revised then.

### Two engineers (contingent)

After Phase 1, backend context extraction and frontend contract alignment can
partially run in parallel. Expected duration is approximately 7-11 calendar
weeks. Confidence is low until production-shaped data, checkpoint inventory,
and authorization scope are measured. The estimate assumes:

- A second engineer actually joins the project
- Disjoint file ownership
- No concurrent large carousel refactor outside the plan
- Stable product behavior
- Strong CI and migration tests

## Interaction with Existing AE-0040 Work

Regenerated from the live board on 2026-06-12. Do not discard the current
refactor tasks; sequence around them.

**Update (2026-06-12, later):** every open tech-debt ticket now carries a
"Modularization Alignment" section adapting it to this plan (wave
sequencing, module destination, no-global-helpers rule, dedupes:
AE-0057 → absorbed by AE-0042; AE-0047 spinner scope → AE-0068, which
became a consolidation of two pre-existing spinner implementations). The
wave order lives in the AE-0040 epic ticket: Wave A (neutral cleanup,
parallel with Phase 0) → Wave B (AE-0044/0045/0046 + AE-0050, after
AE-0041) → only then Phase 4-5 file movement.

### Board state (2026-06-12)

- **Already DONE and merged:** AE-0058 through AE-0067, AE-0069 (the original
  "redirect AE-0057-0064 into carousel presentation" guidance is obsolete
  for these).
- **In REVIEW:** 21 tickets; **ready to merge:** AE-0035, AE-0036.
- **Live blockers in Intake:** AE-0044 (builder for
  `build_workflow_state_response`), AE-0045 (strategy/chain for presentation
  logic), AE-0046 (`ContentSlideCopy` validation) — all blocked by AE-0041
  (magic strings/early returns) and all touching the same carousel service
  files Phases 4-5 will carve up.
- **Still in Intake:** AE-0057 (null safety in `artifact_manifest.py`),
  AE-0068 (frontend Spinner).

### Sequencing rule

Drain the REVIEW and ready-to-merge queues and finish
AE-0041 → AE-0044/0045/0046 **before any Phase 4-5 file movement**, or
explicitly re-scope those three tickets as Phase 5 work items so the same
carousel files are not refactored twice.

### Complete before or during Phase 1

- CI and type-safety hardening
- Removal of blanket ignores
- Small null-safety fixes (AE-0057)
- Small complexity reductions

### Redirect into target modules

- AE-0044 builder work belongs to the inbound HTTP adapter or editorial
  response mapping.
- AE-0045 strategy/chain work belongs to carousel presentation.
- AE-0046 validation work belongs to carousel presentation domain.
- AE-0068 should follow the accepted frontend context names.

### Avoid

- Large physical file moves in the same carousel files while current tickets
  are changing their internals.
- Creating new generic global helpers that the modularization will immediately
  relocate.

## Rollout and Rollback

Each migration slice must:

1. Preserve existing transport contracts.
2. Keep one write authority.
3. Be independently deployable and revertible.
4. Add behavior tests before redirecting traffic.
5. Emit observability showing legacy versus new path usage.
6. Support a feature flag or composition switch when the slice is risky.
7. Carry a side-effect and compatibility ledger.
8. Declare whether rollback or forward-fix is the supported recovery action.
9. Include a before/after diff of the frozen SSE event-name inventory when
   the slice touches any streaming route — event names are string-frozen
   for the entire migration.
10. Drain live checkpoints (finish on pre-migration code, or restart with
    documented consent) before any schema-modifying slice, and respect
    the 2-calendar-week migration-window ceiling with exactly one writer
    per affected table throughout the window.

Route/composition rebinding is permitted only before persisted semantics or
irreversible effects diverge. After that point, the phase-specific ledger
governs compensating actions or forward-fix. A rollback plan that assumes old
code can interpret new rows, events, projections, artifacts, or checkpoints
without an executable compatibility test is invalid.

## Success Metrics

### Architecture

- Zero new global-layer dependency violations.
- Import Linter wildcard ignores removed.
- No application imports of SQLAlchemy, FastAPI, agents, or vendor SDKs.
- No module-internal imports from other modules.
- No container/service-locator access from application code.

### Delivery

- A new bounded module can be added without editing unrelated domain modules.
- A new carousel layout strategy changes only carousel presentation.
- A new publishing channel changes only publishing/distribution and bootstrap.
- A new AI provider changes an outbound adapter, not application behavior.

### Language

- Backend, frontend, API schemas, tests, events, and docs use the same glossary.
- `Carousel`, `BlogPost`, `Workflow`, `Project`, `Source`, `Status`, `Approve`,
  and `Publish` are unambiguous.

### Quality

- Fresh PostgreSQL migration succeeds in CI.
- Domain/ORM full-field round trips are covered.
- Existing Gherkin scenarios continue to pass.
- Frontend transport schemas are checked against OpenAPI.

## Human Checkpoint

Before implementation, explicitly decide:

1. Is the broader aggregate called `EditorialProject`, `ContentProject`, or
   `Campaign`?
2. Is carousel-derived long-form content a `CarouselArticle`, a `BlogPost`, or
   only a publishing projection?
3. Are Persona and Quality one bounded context or two closely related modules?
4. Should Editorial Operations be a module or only a set of read projections?
5. Which existing blog representation is authoritative?
6. What is the actual operating context — users, traffic, in-flight
   LangGraph checkpoints, tenancy? This decides whether the full or
   scaled-down rollback/parity track applies (amendment 4).

Recommended defaults:

- `EditorialProject`
- `CarouselArticle` for carousel-derived public long-form content
- One `persona_quality` context initially
- Editorial Operations as read-side projections initially
- First-class `BlogPost` is authoritative for independent blog publishing;
  carousel embedded markdown remains a compatibility projection until migrated

## Skeptical Review Decision Log

| Finding | Disposition | Closure criterion |
|---|---|---|
| Rollback is not credible | Accepted; plan amended | Phase side-effect ledgers and production-shaped rollback drill pass |
| Authorization ownership underspecified | Accepted; plan amended | Context-owned deny-by-default policies and all inbound-adapter contract tests pass |
| Shared-table ownership conflict | Accepted; plan amended | Sole legacy writer, field ownership map, and concurrency policy are approved |
| Event semantics incomplete | Accepted | Outbox delivery design and replay/dead-letter runbook are approved |
| LangGraph compatibility incomplete | Accepted | Old/new/mixed-version checkpoint resume suite passes |
| Concurrency policy incomplete | Accepted | Expected-version, idempotency, serialization, and freshness contracts pass tests |
| Knowledge pilot tests wrong risks | Accepted; Phase 2.5 added | Carousel risk spike passes before write redirection |
| Operational controls incomplete | Accepted | Per-slice SLI, parity, alert, flag, and deployment-order definitions exist |
| Estimates omit coexistence cost | Accepted; estimate revised | Re-estimate after Phase 2.5 using measured evidence |
| Adversarial tests missing | Accepted | Security, failure-injection, replay, concurrency, and rollback matrix passes |

No finding was waived. The external `BLOCK` verdict remains active until the
closure criteria are validated and the amended plan receives a second blind
review.

### Codebase verification decision log (2026-06-12)

| Finding | Disposition | Closure criterion |
|---|---|---|
| Frontend baseline does not reproduce | Accepted; Phase 0 re-measure added | Re-measured baseline with documented methodology; estimate re-confirmed |
| Document/search Gherkin scenarios do not exist | Accepted; Phase 2 deliverable added | Scenarios written and passing before knowledge route redirection |
| `lock_version` unenforced | Accepted; Phase 2.5 scope corrected | Expected-version enforcement implemented and conflict tests pass |
| AE-0040 table stale | Accepted; section regenerated | Sequencing rule applied before Phase 4-5 file movement |
| No fresh-migration CI job | Accepted; Phase 1 deliverable added | `alembic upgrade head` job green in CI |
| Process weight uncalibrated for single contributor | Accepted; amendment 4 added | ADR-0009 opens with operating-context statement; track choice recorded |
| Redis publish precedes persistence (live bug) | Accepted; Phase 0 immediate fix | Event ordering fixed and covered by a test, independent of module work |

### Round-2 skeptical review decision log (2026-06-12, verdict WARN)

Reviewer: OpenCode (kimi-k2.6), blind packet, no repository access. Full
text: `domain-modularization.skeptical-review-r2.md`.

| Finding | Severity | Disposition | Closure criterion |
|---|---|---|---|
| Phase 2.5 scope 2-4x estimate, no circuit-breaker | BLOCKER | Accepted; Phase 2.5 split into core/contingent layers with a 3-week circuit-breaker | Core/contingent split and overrun decision rule present in Phase 2.5 |
| Circular dependency: amendment 4 track vs Phase 2.5 exit gate | BLOCKER | Accepted; track recorded in ADR-0009 during Phase 0 is now a Phase 2.5 precondition; exit gate made parametric; scaled-down deferrals named in Phase 4 gate | Track recorded before Phase 2.5 starts; parametric exit gate in plan |
| Accepted-but-deferred findings can be silently descoped | WARN | Accepted; supporting designs assigned to phases with timeboxes; phase-gate re-read rule and no-descope rule added; effort composition published | Timebox table, re-read rule, and effort breakdown present |
| Outbox vs reorder fix ambiguity in Phase 0 | WARN | Accepted; committed to reorder-only in Phase 0, outbox is Phase 6 scope | Commitment recorded in "Immediate fix" section and Phase 0 deliverables |
| No DI mechanism specified | WARN | Accepted; manual constructor injection decided, with explicit re-evaluation trigger, recorded in ADR-0009 | "Dependency injection mechanism" section present |
| Frontend estimate confidence near zero | INFO | Accepted; estimate bracketed ±25% pending Phase 0 re-measurement and re-publication with confidence range | Bracket note in effort estimate; re-publication is a Phase 0 deliverable |

No round-2 finding was waived. Both BLOCKERs are resolved by plan
amendment; the round-3 review verified the resolutions.

### Round-3 skeptical review decision log (2026-06-12, verdict PROCEED_WITH_CAUTION)

Reviewer: OpenCode (kimi-k2.6), blind packet, no repository access. Full
text: `domain-modularization.skeptical-review-r3.md`. The review confirmed
both round-2 BLOCKER resolutions and found **no BLOCKER-level issues**.
Its four WARNs and missing-evidence items are resolved below; two were
settled with repository facts the blind reviewer could not see.

| Finding | Severity | Disposition | Closure criterion |
|---|---|---|---|
| `lock_version` enforcement vs "no write redirection" tension | WARN | Accepted; rollout strategy added: test/CI-only in Phase 2.5, production activation with Phase 4's flagged slice. Repository fact: column is `NOT NULL server_default="1"` (migration 0002), so the all-NULL scenario is impossible and no backfill is needed | Rollout strategy paragraph in Phase 2.5 core deliverables |
| Phase 2.5 core estimate optimistic | WARN | Accepted; 1-2 weeks labeled aspirational with 3-week committed ceiling; long-pole identified | Honesty note in Phase 2.5 |
| No SSE event-name migration strategy | WARN | Accepted; names are shared constants on both sides (location corrected 2026-06-12 — see the dated note in the Phase 0 deliverables; the original `domain/constants/carousel_workflow` claim was wrong); Phase 0 freezes the inventory, adds a CI contract test, and every streaming slice diffs the inventory | Phase 0 deliverable + rollout rule 9 |
| Circuit-breaker lacks recovery options | WARN | Accepted; recovery rules added (continue → re-published estimate; re-scope → only duplicate-command proofs droppable, named in Phase 4 gate; re-sequence → named in receiving gate) | Recovery rules under the circuit-breaker |
| Checkpoint serialization format unknown | Missing evidence | Partially settled: `CarouselWorkflowState` is a `TypedDict` with default `JsonPlusSerializer`; Phase 0 confirms with a captured checkpoint; escalation rule blocks Phase 2.5 if payloads prove pickled | Phase 0 checkpoint-inventory deliverable |
| Phase 0 twelve-item scope may not fit | Missing evidence | Accepted; day-one deliverable time budget with named Phase 0b overflow | Phase 0 budget deliverable |

## Final Recommendation

Approve Option B as the architectural direction, but do not authorize
production modularization yet.

The only currently authorized activities are evidence gathering and plan
hardening:

1. Accept or revise the context map and glossary.
2. Draft ADR-0009 with the operating-context statement (amendment 4) and the
   mandatory authorization, shared-writer, rollback, event, checkpoint, and
   concurrency policies.
3. Inventory production-shaped schema, checkpoints, authorization paths, and
   operational constraints.
4. Fix the workflow event ordering bug (reorder-only) and re-measure the
   frontend baseline (both independent of modularization approval).
5. Validate the amended plan.
6. Run the round-3 blind skeptical review confirming the round-2 BLOCKER
   resolutions.

Review history: round 1 `BLOCK` → amendments → round 2 `WARN` (two new
BLOCKERs) → amendments → round 3 `PROCEED_WITH_CAUTION` with **no BLOCKER
findings**, confirming both round-2 resolutions. The cold-critic protocol
requires at least three material concerns per round by design, so
convergence is defined as a non-BLOCK verdict with zero BLOCKER findings —
achieved in round 3, with all round-3 WARNs resolved by clarification in
this revision.

The plan's review gate is therefore satisfied. **Phase 0 is authorized.**
Two conditional re-escalations named by round 3 are encoded as Phase 0
evidence gates: if checkpoint payloads prove class-path-dependent, or the
`lock_version` activation strategy changes, Phase 2.5 must not start until
the corresponding plan section is revised.
