# AE-0630 — Bump dnspython and opentelemetry for CVE-2026-128089 / CVE-2026-126360

Status: In Development
Tier: T1
Priority: High
Type: Chore
Area: Backend
Owner: Pedro
Agent Lane: developer → qa → release
Branch: fix/ae-0630-dnspython-opentelemetry-cves
Kanban Card: TBD
Created: 2026-11-20
Updated: 2026-11-20

## Goal

Get `backend:pip-audit` passing again. New advisories flag the locked dnspython and opentelemetry-api, so the gate fails
locally and will fail on every backend PR and on main once CI's advisory data catches up.

## Problem

- dnspython 2.9.0 (transitive): CVE-2026-128089. A crafted zone file with a WKS record whose service number is out of
  range causes huge memory and CPU use. Fixed in 2.9.2.
- opentelemetry-api 1.45.1 (transitive): CVE-2026-126360. A crafted `traceparent` triggers quadratic regex
  backtracking in `TraceContextTextMapPropagator.extract()` (ReDoS). Fixed in 1.45.2.

## Scope

- Raise the transitive floor `dnspython>=2.9.0` to `dnspython>=2.9.2` in `backend/pyproject.toml` and name the new
  CVE in its trailing note.
- Add a transitive floor `opentelemetry-api>=1.45.2` with a note naming CVE-2026-126360.
- `uv lock --upgrade-package` for dnspython and the opentelemetry family, which is released in lockstep. Check that
  only those packages move, by patch releases.
- Run pip-audit with no ignore, plus the tracing unit tests.

## Non-Goals

- No vulnerability ignores, no application-code, schema or API changes, and no unrelated upgrades.

## Acceptance Criteria

- [x] AC1 The floor is `dnspython>=2.9.2` with a note naming CVE-2026-128089, and the lock resolves dnspython 2.9.2.
- [x] AC2 The floor is `opentelemetry-api>=1.45.2` with a note naming CVE-2026-126360. The lock resolves the
  opentelemetry 1.45.x packages to 1.45.2 and the 0.66 betas to 0.66b2, with no other package moving.
- [x] AC3 `backend:pip-audit` passes with no findings and no new ignore or suppression.
- [x] AC4 The hermetic tracing and Langfuse auth-check unit tests pass on the upgraded opentelemetry.
- [ ] AC5 Every PR workflow is green; mutation remains CI-only.

## No-`.feature` classification (dependency/CI ticket)

- (a) No public or user-visible behaviour change: a patch-level security repair of transitive dependencies; no
  application code touched.
- (b) Seeded-violation evidence: no gate or rule is added. The existing pip-audit gate fails on the vulnerable versions
  and is the regression sensor; it failed on 2026-11-20 on the AE-0626..0629 branch (PR #370).
- (c) Affected gates: `backend:pip-audit`, `backend:test`.
- (d) Reviewer/QA sign-off on this classification: in the PR review.

## Repro Steps

1. On `main` at 82df31c0a, run `bash scripts/ci/gates.sh backend:pip-audit`.
2. It reports 2 known vulnerabilities, in dnspython 2.9.0 and opentelemetry-api 1.45.1.

## Affected Areas

- `backend/pyproject.toml`, `backend/uv.lock`.

## Dependencies

- None. Blocks the AE-0626..0629 move to Review (PR #370), whose QA gate record carries the pip-audit failure.

## Progress Log

- 2026-11-20: Raised the floors. The lock moves dnspython 2.9.0 -> 2.9.2, six opentelemetry packages 1.45.1 -> 1.45.2
  and three 0.66b1 -> 0.66b2. pip-audit PASS; 1174 unit tests pass (tracing, Langfuse auth check, autopilot); type and
  imports gates PASS.

## Files Touched

- `backend/pyproject.toml`
- `backend/uv.lock`

## Test Evidence

- `bash scripts/ci/gates.sh backend:pip-audit` → PASS ("No known vulnerabilities found").
- `uv run pytest tests/unit/test_hermetic_tracing_ae0608.py tests/unit/bootstrap/test_langfuse_auth_check_ae0561.py tests/unit/modules/autopilot` → 1174 passed.
- `gates.sh backend:type`, `backend:imports` → PASS.

## Decision Log

- 2026-11-20: Same pattern as AE-0566 and AE-0576 (floor + lock, no ignore). The opentelemetry packages pin each
  other exactly, so the whole family moves to the same patch release.
