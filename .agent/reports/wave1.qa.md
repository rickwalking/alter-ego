# QA Validation Report — Wave-Level (AE-0077, AE-0078, AE-0075)

**Date:** 2026-06-12 | **Mode:** Wave-level (measurement/documentation tickets) | **AE-0074:** Excluded (separately QA'd)

## Overall Score: 90/100 (Grade A-)

### Per-Dimension Results

| Dimension | Status | Score | Details |
|---|---|---|---|
| Security | ✅ PASS | 100/100 | Fixture sanitization verified; no sensitive data found |
| Accuracy/Reproducibility | 🟠 WARN | 75/100 | 1 warning (known-limitation undocumented), 1 info (LOC drift) |
| Code Quality | ✅ PASS | 95/100 | Ruff clean on Python; shell script robust; minor style note |
| Acceptance Criteria | ✅ PASS | 100/100 | 22/22 ACs verified across all three tickets |
| Orphan/Unfinished Code | ✅ PASS | 95/100 | All artifacts accounted for; no dangling files |

---

### 🟠 Warning Findings

1. **Missing known-limitations documentation in import scanner** — `scripts/metrics/import_baseline.py` includes `TYPE_CHECKING` guarded imports in its violation counts (e.g., `carousel_workflow_engine.py:33` imports `phase_artifact_runner` behind `if TYPE_CHECKING:`). These are not true runtime coupling, yet the scanner counts them identically to top-level imports. The report (`import-violations-baseline.md`) does not document this as a known limitation or caveat, which could mislead Phase 1 ratchet planning (TYPE_CHECKING imports are zero-cost at runtime and may not need remediation). **Fix:** Add a `Known limitations` section to the report header noting that TYPE_CHECKING and lazy/function-level imports are included — the same signal as Import Linter without wildcards, but worth calling out.

### 🟡 Suggestion Findings

1. **`baseline_loc.sh` uses `;;` in case patterns (`kind=story ;;`)** — While valid bash, multiple statements on one line with `;;` produces a clean exit code but could break POSIX-only shells. The script explicitly targets bash via `#!/usr/bin/env bash`, so this is a style note, not a defect.

### ⚪ Info Findings

1. **Backend test LOC drift (168→169 files, 30,027→30,103 lines)** — The committed baseline at 80d90e8 shows 168 test files/30,027 lines. My fresh re-run shows 169/30,103. Root cause: AE-0075 committed `test_checkpoint_fixture_portability.py` (+1 file, +76 lines) after the baseline was captured. This is **expected drift** — the baseline is a tree snapshot at commit time; the script is confirmed deterministic (two runs on same tree produce byte-identical output). Not a finding, just context.
2. **`carousel_checkpoint.meta.json` not programmatically loaded by tests** — The `.meta.json` companion file is human-readable documentation only, not referenced in any test. This is intentional and appropriate for a metadata sidecar.

---

### 🔴 Blocker Findings

None.

---

### Acceptance Criteria Verification Summary

**AE-0077 (6/6 ACs):**
- [x] `modularization-baseline-2026-06.md` exists with traceable numbers — verified
- [x] Running commands twice yields identical output — verified: `diff -q` of two runs is silent
- [x] Production/test/story counted separately — confirmed in report output
- [x] Per-feature totals exist for all `features/*` children — 12 features listed
- [x] Options report cites new baseline with superseded note — confirmed: `.agent/reports/domain-modularization.options.md` line 1102-1110
- [x] Research report correction callouts link to baseline — confirmed via grep

**AE-0078 (8/8 ACs):**
- [x] Report exists with one section per category — 4 violation + 2 pattern sections
- [x] Every section has total count and file-level listing — verified in report
- [x] `get_container()` sites outside allowed code individually listed — 26 sites at file:line
- [x] `.commit()` in repository adapters individually listed — 9 sites
- [x] Running commands twice yields identical results — verified: all counts match
- [x] Wildcard-hidden vs target-forbidden distinction visible — explicit section labels
- [x] Machine-readable appendix present — confirmed: 200+ module pairs in ````text block
- [x] CI behavior unchanged — no `.importlinter` or workflow modifications

**AE-0075 (8/8 ACs):**
- [x] `checkpoint-inventory.md` exists with backend counts, capture date, finish costs — verified
- [x] Sanitized fixture under `backend/tests/fixtures/checkpoints/` — bin + meta.json present
- [x] Fixture deserializes without project imports — pytest: 3/3 passed, including subprocess isolation test
- [x] Report has explicit "Serialization: PORTABLE" verdict — confirmed line 8
- [x] `lock_version` distribution recorded for both tables — SQL and 39-row carousel distribution
- [x] No unsanitized user content — manual string dump: 126 printable strings, only generic field names + "Test"/"Devs" (dev workflow placeholders)
- [x] Portability test enforces no-project-imports mechanically — subprocess with `sys.modules` assertion (line 47-55)
- [x] Fixture provenance documented — report lines 89-94

---

### Top 3 Risks

1. **Import scanner overcounts via TYPE_CHECKING imports (AE-0078)** — If Phase 1 uses the baseline exception list as-is, it will include ~6 import pairs that are TYPE_CHECKING-only, inflating the perceived violation count. The 2-5% overcount is small but unexpected.
2. **Baseline LOC drift is invisible (AE-0077)** — The baseline is a tree snapshot from commit time. If developers run the script on HEAD months later, they get different test counts and may incorrectly conclude the script is non-deterministic. A README comment or `git stash` instruction would help.
3. **Fixture `.meta.json` has no integrity tie to the `.bin`** — If someone swaps the fixture without updating the meta file, there's no automated check. Low risk in a pre-production single-user project.

---

### Recommended Next Steps

- **High:** Add a "Known limitations" section to `import-violations-baseline.md` documenting that TYPE_CHECKING guarded imports are included in the counts.
- **Low:** Consider adding `-e '^if TYPE_CHECKING:'` skipping logic to `import_baseline.py` if Phase 1 wants true-runtime-only coupling metrics.
- **Low:** Add a comment to `baseline_loc.sh` noting that it reports the current tree state and is designed for reproducible snapshots, not live monitoring.

---

**QA_VERDICT: WARN**

---

## QA Round 2 — Fix Verification Report

**Target:** Commit `716dba5` (Wave 1 findings)

---

### Finding 1 — `import-violations-baseline.md` lacked a Known-limitations section about `TYPE_CHECKING` imports

**RESOLVED** — The report now includes a **"Known limitations (QA wave-1 finding, 2026-06-12)"** section (lines 22–33 of the committed file) documenting:
- `TYPE_CHECKING` imports are counted (Import Linter parity) but tagged `[type-checking-only]`
- Function-level (lazy) imports are not distinguished
- Dynamic imports (`importlib`, string-based) are not detected

---

### Finding 2 — `TYPE_CHECKING` pairs indistinguishable in counts/appendix for Phase 1 planning

**RESOLVED** — The scanner now splits `runtime=` vs `type-checking-only=` in every section header. In `agents -> application`:
```
import-lines=22 (runtime=20, type-checking-only=2) unique-module-pairs=22
```
The two TC pairs (`carousel_workflow_engine` and `carousel_workflow_nodes` → `phase_artifact_runner`) are tagged `[type-checking-only]` in the per-section listing and `# type-checking-only` in the machine-readable appendix. Counts verify unchanged totals:
- `application→infrastructure`: 66 ✓
- `application→agents`: 26 ✓
- `agents→application`: 22 ✓
- `api→infrastructure`: 101 ✓

---

### Finding 3 — `baseline_loc.sh` lacked snapshot-vs-drift semantics note

**RESOLVED** — The shell header now includes a 5-line `Snapshot semantics` comment block documenting that a committed baseline reflects the tree at its commit and later runs on HEAD legitimately differ (drift, not non-determinism). The script still executes cleanly, producing the expected output.

---

### Additional verification

| Check | Result |
|-------|--------|
| `import_baseline.py` double-run (stdout md5) | `8bdc024e7919528c6d0a29b6b962574b` → `8bdc024e7919528c6d0a29b6b962574b` — **byte-identical** ✓ |
| `import-violations-baseline.md` file md5 (after both runs) | `fbbbbfd22a076c10f8dc286d5d12a0ee` — **persistent** ✓ |
| `ruff check scripts/metrics/import_baseline.py` | `All checks passed!` ✓ |
| `baseline_loc.sh` execution | Exits 0, produces correct output ✓ |

### New issues introduced

None detected. The 3 changed files (`import-violations-baseline.md`, `baseline_loc.sh`, `import_baseline.py`) all carry the targeted fixes without regressions. Ruff passes, script output is deterministic, and the report structure remains clean.

---

**QA_VERDICT: PASS**
All checks completed. Ready for next steps.

---

## Review provenance

- Reviewer: separate ephemeral OpenCode sessions (provider CrofAI, model kimi-k2.6, plan/read-only agent), repository root access
- Round 1: full wave QA (scripts re-run, tests re-executed, fixture strings audited) — WARN 90/100, zero blockers, 22/22 ACs verified
- Round 2: fix confirmation against commit 716dba5 — PASS
- Operational note: two OpenCode launches hung at init and one died mid-stream; resolved by clean-kill-then-relaunch (alternating-launch pattern), resilience rules added to the QA prompt
- Date: 2026-06-12
