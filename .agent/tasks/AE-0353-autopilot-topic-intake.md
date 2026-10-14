# AE-0353 — Topic intake POST /api/autopilot/topics: schema, source allowlist, dedupe, daily cap

Status: Review
Tier: T2
Priority: High
Type: Feature
Area: backend
Owner: Grok (Cursor CLI, grok-4.7-high)
Agent Lane: developer → qa → release
Branch: feat/ae-0353-autopilot-topic-intake
Kanban Card: TBD
Created: 2026-10-13
Updated: 2026-10-13
Parent: AE-0348

## Goal

Accept Grok-ranked topics from the scout, distrust them, and queue at most `AUTOPILOT_DAILY_CAP` autopilot runs per day.

## Problem

LLM output is untrusted and may be prompt-injected via scraped signals; it may also invent sources or repeat recent topics.

## Scope

- Request schema `TopicBatch` = 1–3 `TopicProposal` {title ≤120, angle ≤300, why_viral ≤300, audience ≤120, niche ≤80, brief ≤800, sources: 1–8 URLs, score 0–100}; `extra=forbid`.
- Source allowlist: every proposal URL MUST be in the signals bundle served within the last 6 h (persist served URLs set or re-use the 30-min cache + a 6-h served-URL table/Redis set). Proposals with any foreign URL are rejected individually.
- Text sanitisation: strip control chars; reject proposals containing URLs in free-text fields.
- Dedupe: `signal_hash = sha256(normalized title + sorted sources)`; also skip if title similarity (token Jaccard ≥0.6) with any carousel topic created in the last 60 days.
- Pick top-1 by score (configurable `AUTOPILOT_DAILY_CAP`, default 1, timezone America/Sao_Paulo); persist all accepted proposals as `topic_candidates`; create `autopilot_runs(state=queued)` only for picked ones.
- Response: `{accepted:[ids], queued:[run_ids], rejected:[{title, reason}]}`.

## Non-Goals

- Generating the carousel (AE-0354).
- Telegram topic picker (future).

## Acceptance Criteria

- [x] WHEN a proposal cites a URL not served in signals THE intake SHALL reject that proposal with reason `source_not_in_signals`.
- [x] WHEN a proposal duplicates a topic from the last 60 days THE intake SHALL reject it with reason `duplicate_topic`.
- [x] WHEN the daily cap is already reached THE intake SHALL persist candidates but queue no run, reason `daily_cap_reached`.
- [x] WHEN the payload violates the schema THE API SHALL return 422 and persist nothing.
- [x] WHEN the same batch is posted twice THE second call SHALL queue nothing new (idempotent via signal_hash).

## Gherkin Scenarios

```gherkin
Feature: Autopilot topic intake

  Scenario: Best valid topic is queued
    Given the signals bundle served URLs A and B
    When the scout posts topics citing A (score 90) and B (score 70)
    Then both candidates are stored
    And one autopilot run is queued for the score-90 topic

  Scenario: Invented source is rejected
    When the scout posts a topic citing a URL not in the signals bundle
    Then that topic is rejected with reason "source_not_in_signals"

  Scenario: Daily cap
    Given one run was already queued today
    When the scout posts a valid topic
    Then no run is queued and the reason is "daily_cap_reached"

  Scenario: Replay is idempotent
    Given a batch was already accepted
    When the same batch is posted again
    Then no new run is queued
```

## Delta

### ADDED

- `backend/src/rag_backend/modules/autopilot/application/topic_intake.py`
- `POST /api/autopilot/topics`
- `backend/tests/features/autopilot_topic_intake.feature`

### MODIFIED

- None.

### REMOVED

- None.

## Affected Areas

- Backend
- API
- Database (writes)
- Tests

## Dependencies

- Blocks: AE-0354, AE-0360
- Blocked by: AE-0350, AE-0351, AE-0352

## Implementation Plan

1. Feature first.
2. Pydantic schemas.
3. Allowlist + dedupe + cap as pure functions with unit tests.
4. Service + route; integration test with DB.

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
- [ ] Prompt-injection payload test (instructions inside brief) — must be stored as inert text only

## Progress Log

### 2026-10-13 00:00

Ticket created from docs/architecture/grokbot-autopilot.md (ticket #4).

### 2026-10-13 22:30

Implemented topic intake on `feat/ae-0353-autopilot-topic-intake`. The first full `gate-capture.sh backend` failed the route snapshot because `POST /api/autopilot/topics` was new. After the snapshot update, the capture is green (20 pass, 0 fail, 0 skip).

## Files Touched

- `backend/src/rag_backend/modules/autopilot/application/topic_intake.py` — batch accept, persist, queue
- `backend/src/rag_backend/modules/autopilot/domain/intake.py` — allowlist, dedupe, cap plan
- `backend/src/rag_backend/modules/autopilot/domain/topic_text.py` — strip, hash, Jaccard, Sao Paulo day
- `backend/src/rag_backend/modules/autopilot/infrastructure/intake_store.py` — served URLs, candidates, runs
- `backend/src/rag_backend/modules/autopilot/api/schemas.py` — `TopicBatch` / response
- `backend/src/rag_backend/modules/autopilot/api/router.py` — `POST /topics` and served-URL record on `GET /signals`
- `backend/alembic/versions/f2a3b4c5d6e7_autopilot_served_signal_urls.py` — allowlist table
- `backend/tests/features/autopilot_topic_intake.feature`
- `backend/tests/unit/autopilot/test_topic_intake_plan.py`
- `backend/tests/integration/test_autopilot_topic_intake.py`
- `backend/tests/snapshots/openapi_routes.json`

## Test Evidence

`bash scripts/ci/gate-capture.sh backend` exit 0 at `6a8a2a46`. Pytest 3102 passed / 2 skipped. Diff coverage 96%. Mutation score 79.91%.

GATES_JSON: {"pass":20,"fail":0,"skip":0,"results":[{"gate":"backend:format","status":"PASS"},{"gate":"backend:lint","status":"PASS"},{"gate":"backend:lint-diff","status":"PASS"},{"gate":"backend:blanket-ignore","status":"PASS"},{"gate":"backend:strict-diff","status":"PASS"},{"gate":"backend:type","status":"PASS"},{"gate":"backend:imports","status":"PASS"},{"gate":"backend:arch-ratchet","status":"PASS"},{"gate":"backend:docstrings","status":"PASS"},{"gate":"backend:dead-code","status":"PASS"},{"gate":"backend:inline-prompts","status":"PASS"},{"gate":"backend:redis-factory","status":"PASS"},{"gate":"backend:bandit","status":"PASS"},{"gate":"backend:pip-audit","status":"PASS"},{"gate":"backend:integrity","status":"PASS"},{"gate":"backend:test","status":"PASS"},{"gate":"backend:diff-cover","status":"PASS"},{"gate":"backend:migrations","status":"PASS"},{"gate":"backend:schema-drift","status":"PASS"},{"gate":"backend:mutation","status":"PASS"}]}

## QA Report

Pending.

## Decision Log

See ADR-0020.

## Blockers

None.

## Final Summary

Pending.
