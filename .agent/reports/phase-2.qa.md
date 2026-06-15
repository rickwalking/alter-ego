# Phase 2 QA Report — Knowledge module pilot (batch)

**Scope:** AE-0088..0095 (8 tickets). **Verdict:** ✅ PASS (converged — round 1 WARN → fix → round 2 PASS).

## Provenance
| Field | Value |
|-------|-------|
| Tool | run_external_qa.sh — round 1 OpenCode, round 2 OpenCode (Quality-Guardian protocol; gates.sh + check-integrity.sh reproduced) |
| Commits | ecf653d (A: 0088/0089/0090), 3b77f45 (B: 0091), 933f5c6 (C: 0092/0094), e6abffa (D: 0093), 1d00454 (E: 0095), 40f0c99 (integrity fixes+scripts), 722f449 (dep CVEs) |
| Round 1 | WARN — only pre-existing pip-audit CVEs (pypdf/pip) + DB-skip + justified apparatus edits; 0 code findings |
| Round 2 | PASS — 0 critical/warning/minor (pip-audit remediated; 2 info) |
| Gates | gates.sh backend: 13 PASS / 0 FAIL / 4 SKIP (test/diff-cover/migrations need Postgres → CI decides) |
| Integrity | check-integrity.sh: 0 net-new blockers (apparatus-edit warnings justified by AE-0095) |
| Date | 2026-06-15 |

## ⚠️ Integrity incident (handled)
During Wave C a `_integrity_selftest` actor swept the uncommitted work onto a throwaway branch
bundled with deliberate gate-gaming (eval-probe, skip-flaky test, diff_cover fail_under 75→50,
mypy _probe ignore, rogue scripts). Recovery: only the legitimate AE-0092/0094 work was restored;
**every gaming change was rejected** and re-verified against the un-gamed gates. The QA-guardian
scripts (gates.sh/check-integrity.sh) were restored cleanly as real infra (owner decision).

## Per-dimension
| Dimension | Status | Evidence |
|-----------|--------|----------|
| Gate reproduction | ✅ PASS | 13/13 runnable gates PASS; 4 DB/slow SKIP (CI decides) |
| Integrity / anti-gaming | ✅ PASS | 0 net-new blockers; no suppressions/skips/lowered thresholds in the diff |
| Byte-identical APIs | ✅ PASS | /api/documents + /api/search snapshot diff = 0 (AE-0088); no snapshot edited |
| Exit gate | ✅ PASS | knowledge-application-isolation + knowledge-public-facade contracts KEPT (lint-imports 10/0) |
| Acceptance criteria | ✅ PASS | 8 tickets, all ACs met |
| Tests / types | ✅ PASS | mypy 424; full suite 1757 passed, 2 skipped (pre-existing) |

## Notable
- get_container ratcheted 26→18, api→infra 98→90 (knowledge cleanup). UoW single commit owner. ORM full-field (scope/is_public) + additive migration empty-diff. Repo contract suite (fake+Postgres). Pre-existing pypdf/pip CVEs remediated (722f449).

## Disposition
AE-0088..0095 → **Review**. Phase 2 (Knowledge module pilot) complete; reusable template proven for Phases 3-8.
