# AE-0496 — Backend: bump black and opentelemetry past newly published CVEs (pip-audit gate)

Status: In Development
Tier: T1
Priority: High
Type: Bug
Area: Backend
Owner: Claude — found while shipping the /chat fixes (AE-0486 follow-up)
Branch: fix/ae-0486-deps-cve
Created: 2026-10-22
Updated: 2026-10-22

## Goal

`backend:pip-audit` passes again, so backend pull requests can go green.

## Problem

Two advisories published on 2026-10-22 made the blocking pip-audit gate fail on every backend PR:
CVE-2026-114134 (black 26.3.1, fixed in 26.10.1) and CVE-2026-114603 (opentelemetry-api 1.41.1, fixed in 1.45.1).

## Scope

- `black>=26.10.1` in `backend/pyproject.toml`; `uv lock --upgrade-package black --upgrade-package
  opentelemetry-api` (the opentelemetry family moves together to 1.45.1 / 0.66b1).

- Regenerate `docs/architecture/openapi.json`: main went red on the new `backend:openapi-fresh` gate because the
  conversation-ownership change (AE-0486) dropped the documented 403 responses and landed after the gate. The
  regenerated artifact only removes those 403 entries.

## Non-Goals

- Any other dependency change.

## Acceptance Criteria

- [x] `backend:pip-audit` passes.
- [x] All other backend gates pass on the bump (mutation in CI).
- [x] `backend:openapi-fresh` passes (artifact regenerated).

## Repro Steps

1. `bash scripts/ci/gates.sh backend:pip-audit` on main → 2 known vulnerabilities. On this branch → PASS.

## Affected Areas

- [x] Backend
- [ ] Frontend
- [ ] Tests

## Dependencies

None.

## Progress Log

### 2026-10-22 19:00

Bumped and locked. This is a CI and config change with no user-visible behavior change, so per CLAUDE.md
(AE-0153) unit tests and gates stand in for a `.feature`; the failing gate itself is the seeded check. Local
backend gates all PASS. In the full test run, `test_image_bridge_waiter.py::test_three_requests_with_a_cap_of_two`
(timing) and one `TestCreateSlug` setup errored under load; both pass when re-run alone. They are unrelated to the
bump.

## Files Touched

- backend/pyproject.toml, backend/uv.lock
- docs/architecture/openapi.json (regenerated)

## Test Evidence

pip-audit, format, lint, type, lint-diff, blanket-ignore, strict-diff, imports, arch-ratchet, docstrings, dead-code,
inline-prompts, gherkin-refs, comments, blog-v1-dead-code, redis-factory, autopilot-env, healthcheck-loopback,
bandit, integrity, duplication, migrations, schema-drift, diff-cover: PASS. test: 6581 passed; the 2 load flakes
above pass when re-run alone.

## QA Report

Pending (CI).

## Blockers

None.
