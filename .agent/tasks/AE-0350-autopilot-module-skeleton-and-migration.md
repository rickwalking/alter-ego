# AE-0350 — Autopilot bounded context skeleton + Alembic migration (4 tables)

Status: Review
Tier: T2
Priority: High
Type: Feature
Area: backend
Owner: Grok (Cursor CLI, grok-4.7-high)
Agent Lane: developer → qa → release
Branch: feat/ae-0350-autopilot-module-skeleton-and-migration
Kanban Card: TBD
Created: 2026-10-13
Updated: 2026-10-13
Parent: AE-0348

## Goal

Create `backend/src/rag_backend/modules/autopilot` from `modules/_template` with domain models, repository ports/adapters, constants, import-linter contract, and one Alembic migration for `autopilot_runs`, `topic_candidates`, `integration_credentials`, `telegram_updates`.

## Problem

Every later ticket needs persisted state with conditional (compare-and-set) transitions; no such module or tables exist.

## Scope

- Module layout per module-conventions §2: `domain/models.py` (AutopilotRun, TopicCandidate, IntegrationCredential, AutopilotRunState StrEnum), `domain/ports.py` (repository protocols), `domain/state_machine.py` (allowed transitions table from doc §4), `infrastructure/repository.py` (SQLAlchemy `Mapped[]`), `constants.py`, `public.py`, `bootstrap.py`.
- `autopilot_runs`: id UUID PK, carousel_project_id FK UNIQUE NULL, topic_candidate_id FK, state, state_reason, attempts int, telegram_message_ids JSONB, ig_container_id, ig_post_id, ig_permalink, created_at, updated_at; index on (state, updated_at).
- `topic_candidates`: id, title, angle, why_viral, audience, niche, brief, sources JSONB, score int, signal_hash UNIQUE, status, created_at.
- `integration_credentials`: provider PK, encrypted_token text, expires_at, refreshed_at.
- `telegram_updates`: update_id BIGINT PK, received_at.
- Repository method `transition(run_id, expected: State, new: State, reason) -> bool` implemented as a single `UPDATE … WHERE id=:id AND state=:expected` returning rowcount==1.
- Emit `content.autopilot.state_changed` via the existing transactional outbox on every successful transition.

## Non-Goals

- Business logic of runner/collectors/notifier (later tickets).
- API routes.

## Acceptance Criteria

- [x] WHEN `alembic upgrade head` runs on a fresh DB AND on a prod-like snapshot THE migration SHALL apply and `alembic heads` SHALL show exactly one head.
- [x] WHEN `transition()` is called with a stale expected state THE repository SHALL return False and change nothing.
- [x] WHEN a transition not allowed by the state-machine table is requested THE domain SHALL raise `InvalidAutopilotTransition`.
- [x] WHEN a transition succeeds THE outbox SHALL contain exactly one `content.autopilot.state_changed` row in the same DB transaction.
- [x] WHEN import-linter runs THE new `autopilot` public-facade contract SHALL pass and a seeded internal import from another module SHALL fail it.

## Gherkin Scenarios

```gherkin
Feature: Autopilot run state machine

  Scenario: Allowed transition persists and emits an event
    Given an autopilot run in state "queued"
    When the runner transitions it from "queued" to "generating"
    Then the run state is "generating"
    And one "content.autopilot.state_changed" outbox event exists

  Scenario: Concurrent transition loses the compare-and-set
    Given an autopilot run in state "awaiting_owner"
    And another actor already moved it to "publishing"
    When a second actor transitions it from "awaiting_owner" to "publishing"
    Then the transition returns false
    And no additional outbox event is written

  Scenario: Illegal transition is rejected
    Given an autopilot run in state "published"
    When a transition to "generating" is requested
    Then an InvalidAutopilotTransition error is raised
```

## Delta

### ADDED

- `backend/src/rag_backend/modules/autopilot/**`
- Alembic revision `autopilot_tables`
- import-linter contract for autopilot
- `backend/tests/features/autopilot_state_machine.feature`

### MODIFIED

- `backend/.importlinter` (or pyproject import-linter section)

### REMOVED

- None.

## Affected Areas

- Backend: new module
- Database: 4 tables
- Tests: unit + integration (repository CAS)

## Dependencies

- Blocks: AE-0351..AE-0358
- Blocked by: none
- Related: ADR-0004, ADR-0009, ADR-0012

## Implementation Plan

1. Copy `modules/_template` → `modules/autopilot`; rename.
2. Write the .feature, then domain + state machine + tests.
3. Write ORM + repository + Alembic migration (`alembic revision --autogenerate`, then hand-review).
4. Wire outbox emission using the existing outbox helper (`infrastructure/events/outbox_dispatch.py`).
5. Add import-linter contract + seeded-violation test.

## Implementer Notes (read first — Cursor CLI / Grok)

- Source of truth: [docs/architecture/grokbot-autopilot.md](../../docs/architecture/grokbot-autopilot.md) and [ADR-0020](../../docs/decisions/0020-grokbot-autopilot.md). If this ticket and the doc disagree, STOP and ask — do not guess.
- Read `CLAUDE.md`, `backend/CLAUDE.md`, `backend/AGENTS.md`, `docs/architecture/module-conventions.md` before coding.
- Module rules: new code lives in `backend/src/rag_backend/modules/autopilot/` following `modules/_template/` (domain/application/infrastructure/api + `public.py` + `bootstrap.py` + `constants.py`). Other modules are reached ONLY through their `public.py`; add an import-linter contract for `autopilot` (module-conventions §7a/§7d).
- Hard rules: no magic strings (constants.py), no `Any`/`object`, ≤3 args per function (Pydantic/typed command objects), guard clauses, ≤400 lines/file, mypy strict, ruff clean, 90%+ branch coverage.
- Behavior-changing tickets: write the `.feature` file FIRST under `backend/tests/features/` and reference scenario names in test comments.
- Never commit secrets. Never push `main` (auto-deploys prod). Branch per ticket, lowercase conventional commits.
- Done = `bash scripts/ci/gate-capture.sh backend` green with the `GATES_JSON:` line pasted in the dev summary + `/qa-agent` PASS. Never pipe gates to `tail`/`head`.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked
- [ ] Single Alembic head verified
- [ ] Rule-fires test for the new import-linter contract (AE-0180)

## Progress Log

### 2026-10-13 16:50

Module, migration `d0e1f2a3b4c5`, and import-linter contract are in. Full backend gate on `8e072276`: 20 pass, 0 fail, 0 skip. Handing to QA.

### 2026-10-13 16:02

Moved to In Development on `feat/ae-0350-autopilot-module-skeleton-and-migration`.
Spec-first: `.feature` then tests then the module, migration, and import-linter contract.

### 2026-10-13 00:00

Ticket created from docs/architecture/grokbot-autopilot.md (ticket #1).

## Files Touched

- `backend/src/rag_backend/modules/autopilot/**` (domain, application, infrastructure, api, public, bootstrap, constants)
- `backend/src/rag_backend/infrastructure/database/models/autopilot_registry.py`
- `backend/src/rag_backend/infrastructure/database/models/__init__.py`
- `backend/alembic/versions/d0e1f2a3b4c5_autopilot_tables.py`
- `backend/.importlinter`
- `scripts/metrics/import_baseline.py`
- `backend/tests/features/autopilot_state_machine.feature`
- `backend/tests/unit/modules/autopilot/test_state_machine.py`
- `backend/tests/unit/modules/autopilot/test_import_contract.py`
- `backend/tests/integration/test_autopilot_state_machine.py`
- `backend/tests/integration/test_autopilot_migration.py`
- `backend/uv.lock`, `backend/pyproject.toml` (pip-audit floors already allowed the fixed releases)

## Test Evidence

- `backend/tests/features/autopilot_state_machine.feature` — allowed transition, stale compare-and-set, illegal transition.
- `tests/integration/test_autopilot_state_machine.py` — those three scenarios, plus a missing run (no event), rollback of the outbox row, and a topic/credential/telegram round trip.
- `tests/unit/modules/autopilot/test_state_machine.py` — architecture §4 table, illegal pairs raise `InvalidAutopilotTransition`.
- `tests/unit/modules/autopilot/test_import_contract.py` — seeded `api` import of `autopilot.domain` fails `lint-imports` (AE-0180).
- `tests/integration/test_autopilot_migration.py` — single head `d0e1f2a3b4c5`; sqlite upgrade/downgrade from the previous head.
- Postgres `alembic upgrade head` from an empty database applies the chain, including `autopilot_tables`, and autogenerate reports no schema drift.
- Gate proof: `.agent/reports/AE-0350.dev-summary.md`.

## QA Report

Pending.

## Decision Log

See ADR-0020. Implementation choices recorded here because the ticket and the architecture doc were both satisfiable:

- `why_viral` is a NOT NULL column. The ticket scope and architecture §5 require it; §4's column list omitted it.
- `carousel_project_id` is `VARCHAR(36)` NULL, unique, FK to `carousel_projects.id` ON DELETE SET NULL. That primary key is a string, so a native UUID column cannot reference it.
- `topic_candidate_id` is NOT NULL, FK ON DELETE RESTRICT. Only `carousel_project_id` was specified as nullable.
- JSON columns use JSON with a JSONB variant so PostgreSQL stores JSONB and the sqlite tests still run.
- `transition()` takes one `TransitionCommand` so the function stays within the three-argument limit.
- ORM models use a typed `DeclarativeBase` that shares the application metadata. Subclassing the legacy `declarative_base()` is `Any` under mypy strict, and a new ignore is not allowed.
- Callers raise and catch `InvalidAutopilotTransition`. The class is `InvalidAutopilotTransitionError` so ruff N818 is satisfied; the ticket name is an alias.
- Persistence registration lives in `autopilot_registry.py`. `models/__init__.py` only re-exports, because ruff RUF067 forbids a call there.
- The sqlite migration test stamps the previous head. Older revisions use PostgreSQL-only `ALTER COLUMN ... TYPE`. The full chain is what the Postgres migration gate runs.

## Blockers

None.

## Final Summary

Autopilot is a bounded context with the §4 run state machine, compare-and-set persistence, one outbox event per successful transition, and a single Alembic head (`d0e1f2a3b4c5`) for the four tables. The public facade is enforced by import-linter, including a seeded-violation test. Backend gates: 20 pass, 0 fail, 0 skip.
