# Phase 1 — Architecture Scaffolding Without Moving Behavior (epic plan)

**Planner output** (planner-skill). Source plan:
`.agent/reports/domain-modularization.options.md` §"Phase 1". Gate: the
migrate-in-place delta review cleared Phase 1 to start
(`.agent/reports/domain-modularization.delta-review.md`,
PROCEED_WITH_CAUTION; the 4 residual WARNs are pre-Phase-4, see
`docs/architecture/phase-0-risk-register.md`). **Precondition: PR #14 (Phase 0) merged.**

## Goal

Establish the target module architecture as *structure only* — package roots,
public-API conventions, enforced import boundaries, and CI guards — with **zero
behavior change**: no business logic moves, no schema changes, no route changes,
no write redirection. Phase 1 makes the boundaries that Phases 2-8 fill.

## Why now / why safe

Phase 0 produced the language, ADRs, baselines (AE-0078 import/contract
baseline, AE-0077 LOC baseline) and evidence gates. Phase 1 only adds scaffolding
and ratchets, so none of the migrate-in-place risks (rollback, drain, outbox,
authz-at-execution) apply yet — they are Phase 4+ obligations.

## Ticket breakdown (vertical slices, one ≈ one branch)

| ID | Title | Tier | Area | Blocked by |
|----|-------|------|------|------------|
| **AE-0079** | Phase 1 epic: architecture scaffolding | T3 | Cross-cutting | — (tracks 0080-0085) |
| **AE-0080** | Package roots + composition-root scaffolding (`bootstrap/`, `modules/`, `platform/`, `legacy/`) | T2 | Backend | — |
| **AE-0081** | Module public-API conventions + reusable module template | T2 | Docs/Backend | — |
| **AE-0082** | Import Linter exact contracts + generated baseline exception list (replace wildcards) | T2 | Backend | AE-0080 (+ AE-0078 baseline) |
| **AE-0083** | Frontend module-boundary lint rules | T2 | Frontend | — |
| **AE-0084** | Fresh-database `alembic upgrade head` CI job | T2 | CI/DevOps | — |
| **AE-0085** | CI architecture reports + violation ratchets | T2 | CI/DevOps | AE-0082 |

## Suggested order (waves)

- **Wave A (parallel, disjoint files):** AE-0080 (backend roots), AE-0081 (docs/conventions), AE-0083 (frontend lint), AE-0084 (alembic CI job).
- **Wave B:** AE-0082 (needs the package roots from AE-0080 + the AE-0078 baseline).
- **Wave C:** AE-0085 (ratchets/reports consume the AE-0082 contracts + baseline).

## Risks & guardrails

- **Hidden behavior change while "only moving composition root."** Mitigation: AE-0080 moves wiring only; full test suite + unchanged-routes assertion in every exit gate.
- **Import-contract churn invalidating the AE-0078 baseline.** Mitigation: AE-0082 *generates* the exception list from the recorded baseline; ratchet only forbids *new* violations (AE-0085).
- **Frontend boundary rules breaking existing cross-feature imports.** Mitigation: AE-0083 baselines current violations as warnings, blocks only new ones (mirrors backend ratchet philosophy).
- **Fresh-DB migration job exposing latent Alembic drift.** Acceptable/desired — it surfaces real issues; fix-forward within AE-0084.
- **Scope creep into Phase 2 (moving real logic).** Hard non-goal across all tickets; enforced by "routes unchanged + behavior identical" exit gates.

## Epic exit gate

- Existing backend + frontend tests pass; routes byte-identical.
- New code **cannot** add global-layer import violations (backend ratchet + frontend boundary rules live).
- Import Linter wildcard exemptions replaced by a generated baseline exception list.
- Fresh-DB `alembic upgrade head` CI job green.
- CI emits architecture reports; ratchets wired into the existing gates (no new workflow sprawl).

## Handoff

→ `/architect-skill` (validate loop: promote AE-0080-0085 to Ready, then execute as Waves A→B→C with the developer-skill + external QA loop, as in Phase 0).
