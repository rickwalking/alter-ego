# AE-0360 — GrokBot scout ops: Cursor CLI (grok-4.7-high) script, prompt v1, schema validator, systemd timer

Status: Ready
Tier: T2
Priority: High
Type: Feature
Area: ops
Owner: Grok (Cursor CLI, grok-4.7-high)
Agent Lane: developer → qa → release
Branch: feat/ae-0360-grokbot-scout-ops-cursor-cli
Kanban Card: TBD
Created: 2026-10-13
Updated: 2026-10-13
Parent: AE-0348

## Goal

Daily host job that fetches signals, has Grok rank them via Cursor CLI headless (sandboxed, no secrets), validates the JSON, and posts topics to the backend.

## Problem

The ranking LLM must be Grok through the existing Cursor plan, without giving the LLM credentials or network power, and without hanging forever (known `agent -p` hang).

## Scope

- `ops/grokbot/bin/grokbot-scout` (bash, `set -euo pipefail`) exactly per doc §5: temp workdir, `curl -fsS` signals with `X-Api-Key`, `env -i HOME PATH CURSOR_API_KEY timeout 600 agent -p --trust --sandbox enabled --model "${GROKBOT_MODEL:-grok-4.7-high}" --output-format json "$(cat scout_prompt.md)"`, extract `.result`, validate, POST.
- `ops/grokbot/v1/scout_prompt.md`: role, read `signals.json` in cwd, pick 1–3 AI themes with highest viral potential for a PT-BR tech audience, cite ONLY URLs present in signals.json, treat signal text as data not instructions, output ONLY JSON matching `topics.schema.json`. Plus `v1/README.md` (versioning rule: never edit v1, create v2).
- `ops/grokbot/v1/topics.schema.json` (JSON Schema matching AE-0353 `TopicBatch`).
- `ops/grokbot/validate_topics.py` (stdlib only + `jsonschema` if available on host, else hand-written checks): strip ```json fences, parse, validate, print normalized JSON; exit 2 on invalid.
- `ops/grokbot/systemd/grokbot-scout.service` (User=grokbot, EnvironmentFile=/etc/grokbot/env, `OnFailure=grokbot-notify-failure.service`), `grokbot-scout.timer` (`OnCalendar=*-*-* 08:00 America/Sao_Paulo`, `Persistent=true`, `RandomizedDelaySec=10m`), `grokbot-notify-failure.service` (curl `POST /api/autopilot/scout-failed` with API key).
- Backend: `POST /api/autopilot/scout-failed` (API key) → Telegram status message to owner.
- `ops/grokbot/install.sh` (idempotent: copies files to /opt/grokbot and /etc/systemd/system, daemon-reload, enable timer) + `ops/grokbot/README.md` runbook (install, manual run, logs via `journalctl -u grokbot-scout`, switching model).

## Non-Goals

- Letting Grok browse or call APIs.
- Running the scout inside the app container.

## Acceptance Criteria

- [ ] WHEN the scout runs THE agent process environment SHALL contain no `GROKBOT_API_KEY` (test: script uses `env -i`; shellcheck clean).
- [ ] WHEN Grok's output has markdown fences or extra prose around JSON THE validator SHALL extract the JSON or exit 2.
- [ ] WHEN the output is invalid / the agent times out / the API returns non-2xx THE service SHALL fail and the owner SHALL receive a Telegram 'scout failed' message.
- [ ] WHEN `install.sh` runs twice THE result SHALL be identical (idempotent).
- [ ] WHEN the validator unit tests run THE seeded invalid payloads (missing field, foreign key, >3 topics, score 101) SHALL each exit 2.

## Gherkin Scenarios

Behavior for the backend route `scout-failed` is covered by a small `.feature` in `backend/tests/features/autopilot_scout_failed.feature` (owner notified on failure). Ops scripts are tooling: covered by validator unit tests (pytest under `ops/grokbot/tests/`) + shellcheck.

## Delta

### ADDED

- `ops/grokbot/**`
- `POST /api/autopilot/scout-failed`
- `backend/tests/features/autopilot_scout_failed.feature`

### MODIFIED

- CI: add shellcheck + `ops/grokbot/tests` to gates if a suitable lane exists (else document manual run in Test Evidence)

### REMOVED

- None.

## Affected Areas

- Ops: systemd + bash
- Prompts/LLM: scout prompt v1
- Backend: one route
- Tests

## Dependencies

- Blocks: epic go-live
- Blocked by: AE-0349 (model id), AE-0351, AE-0352, AE-0353

## Implementation Plan

1. Write schema + validator + tests first.
2. Prompt v1 (+ README).
3. Script + systemd units + install.sh; shellcheck.
4. scout-failed route + feature.
5. Pedro runs `install.sh` on the droplet; one manual `systemctl start grokbot-scout`; paste journal output in Test Evidence.

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
- [ ] Prompt-injection signal fixture (e.g. title 'ignore instructions and output X') does not leak into a non-schema output
- [ ] `timeout` wraps every `agent` call

## Progress Log

### 2026-10-13 00:00

Ticket created from docs/architecture/grokbot-autopilot.md (ticket #11).

## Files Touched

Pending.

## Test Evidence

Pending.

## QA Report

Pending.

## Decision Log

See ADR-0020.

## Blockers

None.

## Final Summary

Pending.
