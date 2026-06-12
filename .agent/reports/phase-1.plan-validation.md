# Phase 1 Plan Validation — architect validate loop

<!-- Provenance: external cold-critic plan-validation (run_external_qa.sh).
Round 1: Cursor — FAIL (3 blockers V-1/V-2/V-3 + 7 warnings). Round 2: OpenCode — PASS.
Protocol: skills/delivery/architect-skill/references/plan-validator.md. Date 2026-06-12. -->

**Verdict: PASS** — all 7 Phase 1 tickets (AE-0079..0085) validated Ready.
Round 1 FAIL → fixes (commit 4c98d72) → Round 2 PASS, all 10 findings resolved.

## Round 1 findings (Cursor) — all resolved
{
  "verdict": "FAIL",
  "scope": "phase-1-validation",
  "tickets": {
    "AE-0079": "WARN",
    "AE-0080": "WARN",
    "AE-0081": "WARN",
    "AE-0082": "FAIL",
    "AE-0083": "WARN",
    "AE-0084": "WARN",
    "AE-0085": "WARN"
  },
  "findings": [
    {
      "id": "V-1",
      "severity": "blocker",
      "ticket": "AE-0082",
      "gap": "AE-0078 baseline measures get_container() (26) and adapter .commit() (9) but AE-0082/0085 ACs only ratchet Import Linter module-pair exceptions; new service-locator or repo-commit violations can land undetected.",
      "fix": "Extend AE-0082 scope+ACs and AE-0085 ratchet to include per-category counts for all six AE-0078 categories; fail CI on any increase."
    },
    {
      "id": "V-2",
      "severity": "blocker",
      "ticket": "AE-0082",
      "gap": "AC 'exception count SHALL equal AE-0078 baseline' is ambiguous: baseline has per-section unique-module-pairs, separate get_container/.commit counts, and TYPE_CHECKING-tagged pairs.",
      "fix": "Add AC specifying exact compared fields per section (runtime pairs, type-checking-only pairs, locator hits, commit hits) and the committed file paths that hold canonical numbers."
    },
    {
      "id": "V-3",
      "severity": "blocker",
      "ticket": "AE-0080",
      "gap": "Moving composition root to bootstrap/ invalidates import_baseline.py CONTAINER_ALLOWED (api/app.py, api/dependencies/) with no ticket AC to update allowed bootstrap paths.",
      "fix": "Add AE-0080 AC to relocate CONTAINER_ALLOWED to bootstrap/; add AE-0082 AC that regenerated baseline matches updated allowed paths."
    },
    {
      "id": "V-4",
      "severity": "warn",
      "ticket": "AE-0080",
      "gap": "'git diff shows only moves/wiring' is not objectively verifiable; no OpenAPI/route snapshot test exists in repo.",
      "fix": "Replace with deterministic check: sorted OpenAPI paths+methods equality or a committed routes snapshot test invoked in AC."
    },
    {
      "id": "V-5",
      "severity": "warn",
      "ticket": "AE-0083",
      "gap": "No reproducible cross-feature import baseline generation AC; grandfather count undefined.",
      "fix": "Add script + committed baseline file; AC: lint cross-feature count <= baseline; new violations error."
    },
    {
      "id": "V-6",
      "severity": "warn",
      "ticket": "AE-0081",
      "gap": "Only 4 ACs; no automated validation of _template module.",
      "fix": "Add mypy/import smoke ACs; raise to 5+ items."
    },
    {
      "id": "V-7",
      "severity": "warn",
      "ticket": "AE-0084",
      "gap": "Only 4 ACs; optional downgrade round-trip in scope but not in AC.",
      "fix": "Add upgrade-head AC with timeout; optionally add downgrade-base round-trip AC."
    },
    {
      "id": "V-8",
      "severity": "warn",
      "ticket": "AE-0082",
      "gap": "Blocked by AE-0078 (Review); baseline artifact exists on branch but merge not guaranteed before Wave B.",
      "fix": "Keep explicit Blocked-by until AE-0078 merged; or reference committed report SHA as pin."
    },
    {
      "id": "V-9",
      "severity": "warn",
      "ticket": "AE-0081",
      "gap": "Ticket blocks AE-0082 but epic plan runs them in parallel Wave A.",
      "fix": "Either add AE-0081 as hard blocker on AE-0082 or mark 0081 conventions as 'minimum stub before 0082 merges'."
    },
    {
      "id": "V-10",
      "severity": "suggestion",
      "ticket": "AE-0079",
      "gap": "Epic exit gate 'routes byte-identical' not propagated as concrete AC to code-touching children beyond AE-0080.",
      "fix": "Add shared no-behavior-change AC template referenced by AE-0080/0082/0083."
    }
  ]
}
## Round 2 verification (OpenCode)

Now let me read all 7 Phase 1 tickets and check for the round-1 validation report.
Let me check for round-1 findings and additional context:
Let me check for the round-1 validation report and verify the wave plan:
Now let me verify the governance structure and check the plan's wave ordering:
Now let me verify the AC counts with precision for the borderline tickets:
Let me verify one more thing — the AE-0078 baseline report and check the CI workflow:
I now have all the evidence I need. Here is the complete validation report.

---

# Phase 1 Round 2 Validation — Resolution Audit

## Per-Finding Verdict

### V-1 (blocker) — AE-0082 scope + AE-0085 ACs: ratchet ALL SIX AE-0078 categories
**RESOLVED.** AE-0082 Scope (lines 28) explicitly enumerates all six categories: "the four import layer/module-pair categories PLUS `get_container()` service-locator sites (baseline=26) and adapter `.commit()` sites (baseline=9)". AE-0082 ACs 2–3 ratchet locator (baseline=26) and commit (baseline=9). AE-0085 AC 1 says "comparing ALL SIX AE-0078 categories (four import layer/module-pair categories + `get_container()` sites + adapter `.commit()` sites) to the committed baseline" and AC 2 requires per-category fail-on-exceed.

### V-2 (blocker) — AE-0082: field-exact comparison
**RESOLVED.** AE-0082 AC 4: "THE comparison SHALL be field-exact per the AE-0078 artifact: per section, runtime unique-module-pairs, type-checking-only pairs, `get_container()` hits, and `.commit()` hits are each compared; counts may only stay equal or decrease, never increase". Scope line 29 also records these exact fields.

### V-3 (blocker) — AE-0080: update `CONTAINER_ALLOWED`, AE-0082 checks regenerated baseline
**RESOLVED.** AE-0080 Scope line 28: "Update `scripts/metrics/import_baseline.py` `CONTAINER_ALLOWED` (currently `api/app.py`, `api/dependencies/`) to the new `bootstrap/` composition-root paths". AE-0080 AC 4: "WHEN `CONTAINER_ALLOWED` is updated to the bootstrap paths THE regenerated AE-0078 baseline SHALL show no NEW container-locator violations from the move (count unchanged)". AE-0082 AC 5 cross-links to the reproducible `import_baseline.py` command.

### V-4 (warn) — AE-0080: deterministic OpenAPI route-snapshot equality AC
**RESOLVED.** AE-0080 AC 3: "WHEN the app boots THE sorted OpenAPI paths+methods SHALL equal a committed pre-change snapshot (deterministic route-equality check)". This is a field-exact, byte-identical comparison, not a "git diff looks like moves".

### V-5 (warn) — AE-0083: committed, reproducibly-generated cross-feature baseline + count ratchet
**RESOLVED.** AE-0083 AC 2: "using a COMMITTED, reproducibly-generated baseline/allowlist (documented generation command — not hand-edited)". AC 4: "THE cross-feature violation count SHALL be recorded in the committed baseline and the lint SHALL fail if the count rises above it".

### V-6 (warn) — AE-0081: ≥5 ACs incl. template mypy + lint-imports smoke
**RESOLVED.** AE-0081 has **7 ACs** (confirmed by section grep): 1 (conventions doc content), 2 (skeleton exists), 3 (glossary alignment), 4 (contract shape for AE-0082), 5 (mypy type-check clean), 6 (lint-imports passes public-facade contract), 7 (stub contracts reference). ACs 5 and 6 provide the mypy + lint-imports smoke tests.

### V-7 (warn) — AE-0084: upgrade-head timeout AC + downgrade round-trip AC
**RESOLVED.** AE-0084 AC 1: "within a bounded timeout and fail if any migration errors or the step times out". AC 2: "WHEN `alembic downgrade base` is run after `upgrade head` on the fresh DB THE round-trip SHALL succeed". Both present.

### V-8/V-9 (warn) — AE-0082 Blocked-by: AE-0081 + AE-0078; plan Wave B reflects 0081→0082
**RESOLVED.** AE-0082 Dependencies line 95: "Blocked by: AE-0080 (package roots); AE-0081 (conventions inform contract shape); AE-0078 (baseline — pin to its committed artifact since it is in Review)". AE-0081 Dependencies line 81: "Blocks: AE-0082 (contracts implement these conventions)". Plan §Suggested order: "Wave A: AE-0080, AE-0081, AE-0083, AE-0084 → Wave B: AE-0082 (needs...AE-0081 conventions)". AE-0079 line 27 also confirms wave order.

### V-10 (suggestion) — AE-0079: no-behavior-change AC on code-touching children
**RESOLVED.** AE-0079 AC 5: "EVERY code-touching child (AE-0080, AE-0082, AE-0083) SHALL carry an explicit no-behavior-change AC (route-snapshot equality and/or unchanged test suite); the epic SHALL NOT close while any child lacks it". Each child is verified: AE-0080 AC 2 (suite + route snapshot), AE-0082 AC 6 (pytest pass), AE-0083 AC 5 (lint + typecheck pass on current tree).

---

## Re-Confirmation Checks

**(a) 6 work tickets fully cover plan deliverables**
| Plan deliverable | Ticket(s) |
|---|---|
| Package roots + comp root → bootstrap/ | AE-0080 |
| Module conventions + template | AE-0081 |
| Import contracts + baseline exception list | AE-0082 |
| Frontend boundary rules | AE-0083 |
| Fresh-DB alembic CI | AE-0084 |
| Arch reports + ratchets | AE-0085 |
**PASS** — all six plan deliverables mapped.

**(b) Dependencies acyclic**
AE-0080 ⟶ AE-0082 ⟶ AE-0085 ← AE-0081 ⟶ AE-0082. No cycles. **PASS**

**(c) No ticket exceeds Phase 1 scope**
All 7 tickets have explicit non-goals stating "no behavior moves, no schema changes, no route changes, no write redirection". **PASS**

**(d) 5–15 testable EARS ACs per ticket**
- AE-0079: 6 ✓ | AE-0080: 7 ✓ | AE-0081: 7 ✓ | AE-0082: 7 ✓
- AE-0083: 6 ✓ | AE-0084: 5 ✓ | AE-0085: 6 ✓
**PASS**

---

## New Gaps

**None.** The edits introduced no new gaps or inconsistencies.

```json
{ "verdict":"PASS", "scope":"phase-1-validation-r2",
  "tickets": {
    "AE-0079":"PASS","AE-0080":"PASS","AE-0081":"PASS",
    "AE-0082":"PASS","AE-0083":"PASS","AE-0084":"PASS","AE-0085":"PASS"
  },
  "findings": [] }
```

**QA_VERDICT: PASS** — All 10 round-1 findings resolved. All 7 Phase 1 tickets are Ready.
