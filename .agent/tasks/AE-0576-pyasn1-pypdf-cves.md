# AE-0576 — Bump pyasn1 and pypdf for CVE-2026-119194..119197 / CVE-2026-119206..119209

Status: Done
Tier: T1
Priority: High
Type: Chore
Area: Backend
Owner: Pedro
Agent Lane: developer → qa → release
Branch: fix/ae-0576-pyasn1-pypdf-cves
Kanban Card: TBD
Created: 2026-10-30
Updated: 2026-10-30

## Goal

Restore `backend:pip-audit` to green: new advisories flag the locked pyasn1 and pypdf, so every backend PR and the
next main run fail the gate.

## Problem

- pyasn1 0.6.4 (transitive, via pyasn1-modules): CVE-2026-119194, CVE-2026-119195, CVE-2026-119196 and
  CVE-2026-119197, CPU time quadratic in the input when decoding crafted BER/CER/DER data. Fixed in 0.6.5.
- pypdf 6.21.2 (direct): CVE-2026-119206, CVE-2026-119207, CVE-2026-119208 and CVE-2026-119209, a crafted PDF causes
  large runtime or memory use. Fixed in 6.21.3.

## Scope

- Raise `pypdf>=6.16.1` to `pypdf>=6.21.3` in `backend/pyproject.toml` with a trailing note naming the CVEs.
- Add a transitive floor `pyasn1>=0.6.5` next to the existing transitive floors, same trailing-note style.
- `uv lock --upgrade-package pypdf --upgrade-package pyasn1`; review that only those two packages move.
- Run pip-audit without an ignore and the PDF build/health unit tests that exercise pypdf.

## Non-Goals

- No vulnerability ignores, application-code changes, schema or API changes, or unrelated upgrades.

## Acceptance Criteria

- [x] AC1 The floor is `pypdf>=6.21.3` with a note naming CVE-2026-119206..119209, and the lock resolves pypdf 6.21.3+
  (6.21.4) without unrelated upgrades.
- [x] AC2 The floor is `pyasn1>=0.6.5` with a note naming CVE-2026-119194..119197, and the lock resolves pyasn1 0.6.5.
- [x] AC3 `backend:pip-audit` passes with no findings and no new ignore or suppression.
- [x] AC4 The PDF slide builder, artifact build and artifact health unit tests pass on the upgraded pypdf.
- [x] AC5 Every PR workflow is green; mutation remains CI-only.

## No-`.feature` classification (dependency/CI ticket)

- (a) No public or user-visible behaviour change: a patch-level security repair of one direct and one transitive
  dependency, no application code touched.
- (b) Seeded-violation evidence: no gate or rule is added; the existing pip-audit gate fails on the vulnerable
  versions and is the regression sensor (it failed on 2026-10-30 on the AE-0541 branch).
- (c) Affected gates: `backend:pip-audit`, `backend:test`.
- (d) Reviewer/QA sign-off on this classification: in the PR review.

## Repro Steps

1. On `main` at a82f9ca2, run `bash scripts/ci/gates.sh backend:pip-audit`.
2. It reports 8 known vulnerabilities in pyasn1 0.6.4 and pypdf 6.21.2.

## Affected Areas

- `backend/pyproject.toml`, `backend/uv.lock`.

## Dependencies

- None. Blocks every backend PR until merged (e.g. AE-0541 #310).

## Progress Log

- 2026-10-30: floors raised, lock moves only pyasn1 0.6.4 -> 0.6.5 and pypdf 6.21.2 -> 6.21.4; pip-audit PASS;
  72 PDF unit tests pass.

## Files Touched

- `backend/pyproject.toml`
- `backend/uv.lock`

## Test Evidence

- `bash scripts/ci/gates.sh backend:pip-audit` → PASS (no findings).
- `uv run pytest tests/unit/application/test_pdf_slide_builder.py tests/unit/application/test_artifact_build_service.py tests/unit/application/test_artifact_health.py tests/unit/application/test_artifact_health_pre_promotion.py` → 72 passed.
- Full backend gate run: `.agent/reports/AE-0576.dev-summary.md`.

## Decision Log

- 2026-10-30: same pattern as AE-0566 (floor + lock, no ignore). The pypdf fix release resolved to 6.21.4, the latest
  6.21.x patch.

## Final Summary

Merged to `main` in PR #311 (31d0ab9e, 2026-10-31). pip-audit green again on every branch; evidence in `.agent/reports/AE-0576.dev-summary.md`.
