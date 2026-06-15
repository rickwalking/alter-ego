# Phase 4 — EditorialProject facade over CarouselProject (epic plan)

**Planner output.** Source: `.agent/reports/domain-modularization.options.md` §"Phase 4" (lines 959-989),
preconditions (108-120) and the sequencing rule (1150-1180). Builds on merged Phases 0-3
(`modules/knowledge`, `modules/identity`, `modules/conversation` are live): reuses the AE-0081 module
conventions, `modules/_template`, the `platform/database` Unit of Work, the QA-guardian gates, and the
AE-0103 import-contract + baseline-ratchet pattern. **Precondition: Phase 3 (PR #17) merged.**

## Goal

Introduce an `editorial` bounded context — `EditorialProject` / `EditorialWorkflow` + workflow status
language — behind a public facade, with a **legacy carousel ACL** (anti-corruption layer) as the single
translator between the legacy `carousel_projects` persistence and editorial concepts. Route workflow
start/state/resume through editorial handlers; move source material, assignments, review decisions, and
optimistic locking behind editorial ports; separate approval from public release at the contract level.
**Behavior-preserving**: the carousel workflow API + SSE (event names/framing/keep-alive/`Last-Event-ID`),
artifact URLs, response schemas, LangGraph checkpoint identifiers + schemas, and `lock_version`
optimistic-lock semantics stay byte-identical. **NO renames** (later phases).

## Scope decision (user-confirmed 2026-06-15)

Phase 2.5 (carousel field-ownership + legacy single-writer) was skipped. Its prerequisites are **folded
into Phase 4 as its first tickets** (AE-0105 field-ownership map, AE-0107 single write owner) — they are
mandatory before any editorial write redirection.

## Reality vs. spec (2026-06-15 code scan)

- **Carousel surface is large**: 8 route files under `api/routes/carousels/` (~21 endpoints) + ~73 service
  files under `application/services/carousel/`. Phase 4 owns ONLY the **workflow** slice
  (`editorial_workflow*.py` routes/services + the `carousel_projects` row + workflow status/checkpoints).
  Presentation/CRUD/media/publishing/strategies/creator-assets stay put (Phase 5+).
- **`carousel_projects` is the god row** (`infrastructure/database/models/carousel.py`): ~40 columns incl.
  `lock_version` (optimistic lock for resume), `current_phase`/`phase_status`/`workflow_status`, plus
  presentation/blog/distribution columns owned by later phases. **Five distinct writers today**
  (carousel_repository, crud.py, admin.py, editorial_workflow.py routes, editorial_workflow_service +
  resume_runner + artifact_build_service) — AE-0107 consolidates the **workflow-owned** fields behind a
  single owner; presentation/CRUD writers are documented and left to Phase 5.
- **LangGraph checkpoints**: `AsyncPostgresSaver`, `thread_id = project_id`, interrupt gates at each phase
  (`carousel_workflow_nodes.py`). These IDs + the `CarouselWorkflowState` schema MUST stay stable.
- **Status language** already centralized in `domain/constants/carousel_workflow.py` (phases, phase status,
  review actions, interrupt types) — editorial reuses/re-exports it; no new strings.
- **Sequencing tickets AE-0041/0044/0045/0046 are PASS QA / in Review** (not merged). AE-0044 already
  refactored `editorial_workflow_routes_response.py` (the Phase-4 response mapper) with a golden snapshot;
  Phase 4 builds on that file, does not re-refactor it. AE-0045/0046 touch presentation (Phase 5).
  **Guardrail: these four must merge before AE-0110 redirects workflow routes** (or be treated as the
  current state of those files).

## Ticket breakdown

| ID | Title | Tier | Area | Blocked by |
|----|-------|------|------|------------|
| **AE-0104** | Phase 4 epic: EditorialProject facade over CarouselProject | T3 | Cross-cutting | — (tracks 0105-0112) |
| **AE-0105** | `carousel-project-field-ownership.md` — column/invariant/owner/concurrency map | T2 | Docs/Arch | — |
| **AE-0106** | Carousel workflow Gherkin safety net + API/SSE byte-identical snapshots | T2 | Tests | — |
| **AE-0107** | `legacy.carousel_project` single write owner for workflow-owned fields | T2 | Backend | AE-0105, AE-0106 |
| **AE-0108** | `modules/editorial/` skeleton + facade + EditorialProject/EditorialWorkflow + status language + re-exported ports | T2 | Backend | — |
| **AE-0109** | Legacy carousel ACL (compatibility adapter: legacy persistence ↔ editorial concepts) | T2 | Backend | AE-0105, AE-0108 |
| **AE-0110** | Workflow start/state/resume routes behind editorial handlers (byte-identical API + SSE; checkpoints stable) | T2 | Backend | AE-0106, AE-0107, AE-0108, AE-0109 |
| **AE-0111** | Move source material, assignments, review decisions, optimistic locking behind editorial ports; split approval from public release | T2 | Backend | AE-0110 |
| **AE-0112** | Editorial import contracts + exit gate + baseline ratchet + checkpoint-drain rule + docs | T2 | Backend/CI | AE-0110, AE-0111 |

## Suggested order (waves)

- **Wave A (parallel):** AE-0105 (field-ownership map), AE-0106 (safety net), AE-0108 (editorial skeleton + domain + status language).
- **Wave B (parallel):** AE-0107 (single write owner — needs 0105/0106), AE-0109 (legacy ACL — needs 0105/0108).
- **Wave C:** AE-0110 (workflow routes behind editorial handlers — needs 0106/0107/0108/0109). *Gate: AE-0041/0044/0045/0046 merged.*
- **Wave D:** AE-0111 (source/assignments/review/optimistic-lock behind ports; approval≠release — needs 0110).
- **Wave E:** AE-0112 (import contracts + exit gate + ratchet — needs 0110/0111).

## Risks & guardrails

- **Workflow API + SSE byte-identical.** Mitigation: AE-0106 snapshots the workflow state response + SSE
  stream (deterministic mock workflow/agent: event types/order + `id:`/`data:` framing + keep-alive +
  `Last-Event-ID`); AE-0110 gated on diff=0. Build on AE-0044's existing response golden snapshot.
- **LangGraph checkpoint stability.** Keep `thread_id = project_id`, the `CarouselWorkflowState` schema,
  and interrupt payload shapes unchanged; editorial handlers wrap the existing engine, never replace it.
- **`lock_version` optimistic-lock semantics.** AE-0107/0111 preserve the resume lock-version bump exactly
  (concurrent-resume test stays green); no concurrency-token change.
- **Checkpoint drain before schema migration** (round-4 finding). Any schema-modifying migration in this
  phase requires every live checkpoint from inventory to be finished on pre-migration code or restarted
  with documented owner consent — encoded in AE-0112 + the epic exit gate. Phase 4 is structured to need
  **no schema migration** (additive-only if any); if a migration becomes necessary, the drain rule applies.
- **Five writers / double-refactor.** AE-0107 consolidates only the workflow-owned fields; presentation/
  CRUD writers are documented (AE-0105) and deferred. AE-0044/0045/0046 already refactored their files —
  Phase 4 builds on them (must merge first; do not re-refactor).
- **god-row shared persistence.** `carousel_projects` stays one table; editorial does not own
  presentation/blog/distribution columns yet — the ACL exposes only workflow concepts. No renames.

## Epic exit gate (from the plan)

- Existing carousel workflow API + SSE behavior byte-identical (AE-0106 snapshots diff=0).
- Editorial handlers do NOT import carousel ORM models directly.
- The compatibility adapter (ACL) is the ONLY module translating legacy project persistence into editorial concepts.
- LangGraph checkpoint identifiers + schemas unchanged; `lock_version` semantics preserved.
- Checkpoint drain satisfied before any schema-modifying migration (none planned; rule encoded if needed).
- `gates.sh` + `check-integrity` green; `editorial-application-isolation` + `editorial-public-facade`
  import contracts KEPT; AE-0082 baseline ratcheted down (or held); module-conventions §11 documents editorial.

## Handoff

→ `/architect-skill` validate loop (confirm AE-0105-0112 Ready), then execute Waves A→E with the
developer-skill + QA-guardian loop, exactly as in Phases 2-3. Gate Wave C on AE-0041/0044/0045/0046 merge.
