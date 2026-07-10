# AE-0312 — PT sentence-case validation and deterministic casing repair for carousel copy

Status: Ready
Tier: T2
Priority: High
Type: Feature
Area: backend
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: TBD
Kanban Card: TBD
Created: 2026-07-10
Updated: 2026-07-10

## Goal

Portuguese carousel copy is held to the same casing bar as English: headings
and body sentences start uppercase and configured proper nouns (e.g.
"Claude", "Anthropic") are correctly capitalized. Violations are caught by
validation (visible in the client like every other rule) and fixed by a
deterministic casing repair that runs in the drafting pipeline and in the
AE-0311 repair endpoint — so the fix is one button-click away for the user,
never a prod SQL edit.

## Problem

Prod incident (project `66014ba3`, 2026-07-10): the published carousel
shipped slide 1 heading "o **espaço mental** privado descoberto no claude"
and slide 2 heading "o que os pesquisadores **descobriram**" — lowercase
sentence starts and lowercase "claude". The EN side has a
`heading_not_sentence_case_en` validation, but PT has **no casing rule at
all**, so nothing flagged it at content review, design validation, or
publish. The fix required manual SQL against `carousel_slides` plus an
in-container re-render. The generation model emits lowercase PT headings
routinely (observed across multiple slides/projects), so this will recur on
every carousel until enforced.

## Scope

- Backend validation: new PT rules in the presentation policy, mirroring the
  EN structure:
  - `heading_not_sentence_case_pt` — heading must start with an uppercase
    letter (markdown emphasis markers like `**` skipped when locating the
    first letter).
  - `body_not_sentence_case_pt` — each sentence in the body starts
    uppercase.
  - `proper_noun_casing` (both locales) — words from a configurable
    proper-noun list must match their canonical casing. **The list lives
    in the policy YAML (`hero_lower_third_v2.yaml`), not code constants**
    (cold-critic r3: a code list needs a PR + deploy per new product
    name; the policy file is already the version-aware home). Seeded with
    `Claude`, `Anthropic`; maintenance ownership documented in the policy
    README. Per-project overrides are a non-goal.
- **Severity model (net-new, in scope — cold-critic verified it does not
  exist today):** add `severity: blocker | warning` to
  `SlideValidationViolation`, thread it through `build_validation_report`,
  and change the blocking decision (`_blocking_from_repaired_localized`,
  `_blocking_from_drafts`) so `blocking=True` only when blocker-severity
  violations remain. **The STORED report must agree with the decision**
  (cold-critic r4: `validate_localized_slides` hardcodes
  `build_validation_report(violations, blocking=True)`, and the stored
  report is what the client/SSE fast path serves verbatim — changing only
  the approval gate would show casing warnings as blocking while the
  approve button works, and would make AE-0310's blocking-driven UI treat
  warnings as needing recovery): `validate_localized_slides` (and every
  producer of a stored report) computes `blocking` from severity; the
  hardcoded literal is removed. Existing rules default to `blocker` (behavior
  unchanged); the new casing rules are `warning`. The severity model and
  the casing rules ship **atomically in this ticket** so a warning-tier
  rule never enters the system before the tier exists.
  **Absent-severity default is pinned in code** (cold-critic r2: a missing
  severity tag must never silently unblock a rule):
  `severity = rule.severity or BLOCKER` at the model level, AND the policy
  loader asserts every rule in v2 carries an explicit severity (load
  fails otherwise), AND a regression test seeds one violation per
  pre-existing rule code and asserts `blocking=True` for each.
- Cross-ticket invariant (declared here, asserted by test): AE-0309's
  fail-closed chain (repair → retry → blocking interrupt) triggers **only
  on blocker-severity violations**; warnings pass through to the review
  panel without consuming the LLM retry or blocking approval. Since AE-0309
  keys on the report's `blocking` flag, the refactored blocking decision
  satisfies this automatically — the test seeds a casing-only violation set
  and asserts no retry and no blocking interrupt.
- Deterministic repair: a pure `repair_casing(payload, locale, policy)`
  transform — uppercase sentence starts (markdown-aware), apply
  proper-noun canonical casing — registered in the bounded repair pipeline
  so it runs (a) during content drafting post-build repair (AE-0309 chain)
  and (b) in the AE-0311 endpoint.
  **Policy-version aware** (cold-critic r2): `repair_casing` executes only
  when the project's active policy defines the casing rules (v2+). A v1
  project neither reports casing violations nor gets casing mutations —
  the AE-0311 button stays honest (nothing flagged, nothing silently
  rewritten). **In-flight v1 projects are auto-upgraded** (cold-critic
  r3: an informational note alone lets the exact 66014ba3 incident class
  recur for every carousel in flight at deploy time — the cohort with the
  highest review traffic): a run-once migration bumps
  `presentation_policy_version` to v2 for every **non-completed** project.
  Safe because casing rules are warning-severity (non-blocking) — the
  worst outcome is new visible warnings with a working repair button.
  **Deploy-order constraint (cold-critic r4):** the auto-upgrade
  migration ships only when AE-0311's repair endpoint is live — warnings
  without a working "Fix issues" button would degrade every in-flight
  review. The rules + severity model + v2 policy can deploy any time;
  the run-once migration is a separate, explicitly AE-0311-gated
  deliverable (recorded in Dependencies).
  **The migration re-validates, not just re-labels** (cold-critic r5:
  bumping the version alone leaves the STORED v1 report served verbatim —
  a project parked at final_review would be approved off a stale report
  that never checked casing, re-shipping the 66014ba3 incident): for each
  upgraded project the migration re-runs `validate_localized_slides`
  under v2 and stores the fresh severity-aware report, so warnings are
  visible at whatever step the project is parked on, including
  final_review and the publish health card.
  **Rollback story (cold-critic r5, prod auto-deploys on merge):** the
  policy loader's unsupported-version behavior is pinned to
  **fall back to `DEFAULT_PRESENTATION_POLICY_VERSION` (v1) with a
  warning log — never raise** (seeded test: a project stamped with an
  unknown version still validates under v1); a down migration restores
  v1 + the prior stored reports for non-completed rows; the up migration
  is idempotent (re-running skips already-v2 rows), **batched and
  resumable** (cold-critic r6: prod deploys block on migrations — the
  re-validation runs in batches of 50 with progress logs, commits per
  batch, and a re-run continues from where it stopped; runtime is bounded
  because re-validation is pure CPU over already-loaded slide data, and
  the current in-flight fleet is single-digit). Completed projects stay on v1
  (frozen artifacts; the AE-0311 repair response notes the upgrade option
  for them). Tests cover: a v1 completed project hitting the repair
  button (no casing mutation), and an auto-upgraded in-flight project
  reporting casing warnings.
- **New-carousel v2 routing mechanism (pinned; cold-critic r4 verified no
  routing path exists):** project creation stamps
  `presentation_policy_version = hero_lower_third_v2` explicitly;
  `DEFAULT_PRESENTATION_POLICY_VERSION` stays v1 so legacy NULL-version
  rows keep their current semantics on re-validation reads.
- Slide-type awareness: rules honor per-slide-type exemptions the policy
  already supports (e.g. a stylistic all-lowercase CTA slide type can be
  exempted explicitly rather than accidentally).
- Frontend: the existing inline violation list (`content-phase-review.tsx`
  today; panels added by AE-0310/0311 as they land) gains **warning-tier
  visual treatment** distinct from blockers (non-blocking badge/styling) —
  this is a component change, not copy-only. New rule codes get pt-BR/en
  i18n strings.
- Policy versioning decision (pinned): the policy file is flat
  (`hero_lower_third_v1.yaml`, singleton supported set), not
  folder-versioned. Per the never-modify-existing rule, ship
  `hero_lower_third_v2` (v1 + casing rules + severity metadata), add it to
  `SUPPORTED_PRESENTATION_POLICY_VERSIONS`, route **new** carousels to v2,
  and keep v1 valid for in-flight projects.

## Non-Goals

- No title-casing or typographic style rules beyond sentence-start +
  proper nouns.
- No LLM-based rewriting; prompt tuning to reduce lowercase emission is a
  separate concern.
- No EN rule changes.
- No retroactive changes to completed carousels (their policy version and
  artifacts stay frozen; the AE-0311 endpoint covers on-demand fixes).
  In-flight projects ARE auto-upgraded (see Scope).

## Acceptance Criteria

- [ ] Validation flags a PT heading starting lowercase, a PT body sentence
      starting lowercase, and lowercase "claude" in either locale, each with
      its own rule code and slide index.
- [ ] The 66014ba3 regression fixture (real prod payloads) produces exactly
      the expected violations, and `repair_casing` fixes all of them:
      "O **espaço mental** privado descoberto no Claude" etc.
- [ ] Markdown emphasis is preserved through repair (`**palavra**` markers
      untouched; first *letter* is what gets uppercased).
- [ ] Accented first letters are handled (`é` → `É`).
- [ ] The proper-noun list lives in a constants file and is covered by a
      rule-fires test (seeded violation → rule fires, per AE-0180).
- [ ] Casing violations render in the existing client violation panels and
      are repaired end-to-end via the AE-0311 button (integration test or
      documented manual QA against a seeded project).
- [ ] Casing rules are warning-severity: `blocking=False` when only casing
      violations remain, and the workflow can be approved past them.
- [ ] Stored-report agreement: the persisted `presentation_validation`
      report's `blocking` field equals the severity-derived decision — a
      casing-only violation set is stored AND served with
      `blocking=False` (test reads the stored report, not the gate).
- [ ] Severity model regression: all pre-existing rules still produce
      `blocking=True` (seeded blocker violation → report blocks).
- [ ] Cross-ticket invariant test: a casing-only violation set does not
      trigger AE-0309's fail-closed retry/interrupt chain.
- [ ] Warning-tier violations render with distinct non-blocking styling in
      the client violation list.
- [ ] Policy ships as `hero_lower_third_v2` routed to new carousels; v1
      untouched and still supported for in-flight projects.
- [ ] Absent-severity hardening: the loader rejects a v2 policy rule with
      no severity (seeded-violation test); the code-level default for a
      missing severity is `blocker`; every pre-existing rule code still
      yields `blocking=True` — the sweep enumerates rule codes
      dynamically from the loaded policy (single source of truth), so new
      rules are automatically covered.
- [ ] In-flight v1 projects are auto-upgraded to v2 by a run-once
      migration that also re-validates and stores fresh severity-aware
      reports (test: a final_review-parked project shows v2 casing
      warnings immediately after migration); completed projects are
      untouched; the migration is deploy-gated on AE-0311 being live,
      idempotent, and has a working down migration.
- [ ] Loader safety: an unsupported `presentation_policy_version` falls
      back to v1 with a warning log and never raises (seeded test) — a
      code rollback after the migration cannot freeze v2-stamped rows.
- [ ] Cross-ticket integration: a report containing one casing warning
      AND one real blocker fires AE-0309's fail-closed chain on the
      blocker only, and the design/content recovery UI treats the report
      as blocking (integration test spanning the severity refactor and
      the fail-closed chain).
- [ ] New projects are stamped `hero_lower_third_v2` at creation;
      `DEFAULT_PRESENTATION_POLICY_VERSION` remains v1 (test covers a
      legacy NULL-version row keeping v1 semantics).
- [ ] `repair_casing` is policy-version-gated: a v1 project reports no
      casing violations and receives no casing mutations from the AE-0311
      repair (test).

## Gherkin Scenarios

```gherkin
Feature: PT sentence-case validation and repair

  Scenario: Lowercase PT heading is flagged and repaired
    Given a slide with PT heading "o **espaço mental** privado no claude"
    When presentation validation runs
    Then heading_not_sentence_case_pt and proper_noun_casing are reported
    When the deterministic casing repair runs
    Then the heading becomes "O **espaço mental** privado no Claude"
    And re-validation reports no casing violations

  Scenario: Body sentence starts are repaired without touching markdown
    Given a PT body "antes de emitir uma palavra... uma janela inesperada."
    When the deterministic casing repair runs
    Then both sentences start uppercase and emphasis markers are unchanged

  Scenario: Exempted slide type keeps stylistic lowercase
    Given a slide type exempted from casing rules in the policy
    When presentation validation runs
    Then no casing violation is reported for that slide

  Scenario: Casing warnings never block approval or trigger fail-closed
    Given a slide whose only violations are warning-severity casing rules
    When the validation report is built
    Then blocking is false
    And the content-phase fail-closed chain does not retry or interrupt
    And the reviewer can approve the phase
```

## Delta

### ADDED

- `severity` field on `SlideValidationViolation` + severity-aware blocking
  decision (warnings never set `blocking=True`).
- `heading_not_sentence_case_pt`, `body_not_sentence_case_pt`,
  `proper_noun_casing` rules in the presentation policy.
- `repair_casing` deterministic transform in the bounded repair pipeline.
- Proper-noun canonical-casing constants.
- `hero_lower_third_v2` policy (v1 + casing rules + severity metadata),
  routed to new carousels.
- Rule-fires regression tests (AE-0180) for each new rule.
- Warning-tier styling in the client violation list.

### MODIFIED

- `build_validation_report` / `_blocking_from_*` (severity-aware blocking).
- `SUPPORTED_PRESENTATION_POLICY_VERSIONS` (adds v2; v1 kept).
- Frontend i18n strings for the new rule codes.

### REMOVED

- Nothing.

## Affected Areas

- Backend: `application/services/carousel/presentation_validation.py`,
  `presentation_copy_repair.py`, `presentation_policy.py`,
  `domain/constants/carousel_presentation.py`
- Frontend: violation panel copy/i18n only
- Database: none
- API: validation report content only (additive rule codes)
- Tests: unit + `.feature` (behavior change) + rule-fires seeded violations
- Docs: qa-checkpoints validation-rule table
- Prompts/LLM: none
- Observability: violations visible in existing validation logging
- Deployment: none

## Dependencies

- Blocks: none (AE-0311 ships without it and picks it up when ready)
- Blocked by: none for the rules/severity/policy deliverables; the
  in-flight auto-upgrade migration is deploy-gated on AE-0311
- Related: AE-0309, AE-0311, AE-0289 (case-preserving sanitization)

## Implementation Plan

1. Add rule implementations + policy wiring, PT-locale aware (accents,
   markdown emphasis).
2. Add `repair_casing` + register in the bounded repair pipeline.
3. Seed proper-noun constants; rule-fires tests per rule.
4. Regression fixture from 66014ba3 prod payloads.
5. Frontend i18n strings for rule codes; verify panels render them.
6. Full gates.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested (accents, emphasis-first headings, empty bodies,
      summary/closing slides with extras-based copy)
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-07-10

Ticket created from prod incident analysis (project 66014ba3 lowercase
headings shipped to publish).

### 2026-07-10 — Developer implementation

Implemented the severity model, PT casing rules, deterministic casing repair,
create-time v2 stamping, the deploy-gated in-flight upgrade migration, and the
frontend warning-tier treatment. Highlights:

- Net-new severity tier: `severity: blocker | warning` on
  `SlideValidationViolation` (code default BLOCKER); `build_validation_report`
  now derives `blocking` from severity (dropped the hardcoded literal);
  `validate_localized_slides` / every stored-report producer inherit it, so the
  stored report agrees with the approval gate. `_blocking_from_*` are unchanged
  because they read the derived `blocking` flag.
- v2 policy `hero_lower_third_v2.yaml` = v1 + `rule_severities` map (all
  pre-existing codes `blocker`, three casing codes `warning`) + `casing` section
  (proper_nouns [Claude, Anthropic] + per-rule `exempt_slide_types`). Loader
  asserts every casing rule carries an explicit severity (load fails otherwise)
  and now falls back to v1 with a structlog warning for unknown versions
  (never raises). Added to `SUPPORTED_PRESENTATION_POLICY_VERSIONS`; DEFAULT
  stays v1. Proper-noun maintenance ownership documented in `contracts/README.md`.
- Casing rules in `presentation_casing.py`: `heading_not_sentence_case_pt`,
  `body_not_sentence_case_pt` (markdown-aware, accent-aware), `proper_noun_casing`
  (both locales). `repair_casing()` deterministic transform, policy-version
  gated (no-op on v1), registered in the bounded repair pipeline.
- Create-time stamping: both project-creation sites stamp
  `hero_lower_third_v2`; DEFAULT stays v1 for legacy NULL rows.
- Migration `scripts/upgrade_inflight_presentation_policy_v2.py` (batched 50/
  commit, resumable, idempotent, down path) + pure testable core in
  `presentation_policy_upgrade.py`; DEPLOY-GATED on AE-0311 (documented in the
  script docstring — must not run in prod before AE-0311 ships).
- API: `severity` added to `SlideValidationViolationResponse` + threaded through
  the response mapper; openapi.json regenerated.
- Frontend: `ViolationSeverity` type + `isWarningViolation`/`violationToneClasses`
  helpers; content-phase-review + design-recovery-panel render warnings with a
  distinct non-blocking tone + severity label; pt/en i18n for the tier labels.

## Files Touched

Backend (src):
- `domain/constants/carousel_presentation.py` (severity + casing violation codes)
- `domain/constants/presentation_policy.py` (v2 constant, supported set, errors)
- `domain/constants/workflow_state_fields.py` (`STATE_FIELD_VIOLATION_SEVERITY`)
- `domain/models/carousel_presentation.py` (`severity` field + `is_blocker`)
- `application/services/carousel/presentation_policy_types.py` (`CasingRulePolicy`,
  policy severity/casing fields + helpers)
- `application/services/carousel/presentation_policy.py` (parse casing/severity,
  loader v1 fallback, severity assertion)
- `application/services/carousel/presentation_casing.py` (NEW: validators + repair)
- `application/services/carousel/presentation_validation.py` (severity-derived
  `build_validation_report`, casing wiring)
- `application/services/carousel/presentation_review_pipeline.py` (drop literal)
- `application/services/carousel/presentation_review_repair.py` (register repair)
- `application/services/carousel/presentation_policy_upgrade.py` (NEW: migration core)
- `api/schemas/carousel_workflow.py` (`severity` on response schema)
- `api/routes/carousels/editorial_workflow_routes_response.py` (thread severity)
- `api/routes/carousels/crud.py` + `application/tools/carousel/generate_carousel.py`
  (create-time v2 stamping)
- `agents/skills/carousel-pipeline/contracts/hero_lower_third_v2.yaml` (NEW)
- `agents/skills/carousel-pipeline/contracts/README.md` (NEW)

Backend (scripts): `scripts/upgrade_inflight_presentation_policy_v2.py` (NEW)

Backend (tests): `tests/features/carousel_pt_casing_severity.feature` (NEW),
`tests/unit/application/test_presentation_casing.py` (NEW),
`test_presentation_severity.py` (NEW), `test_presentation_policy_upgrade.py` (NEW),
`test_presentation_policy.py` (updated), and
`tests/unit/api/routes/carousels/test_create_carousel_policy_stamp.py` (NEW).

Frontend: `modules/editorial/workspace/types-ai.ts`,
`modules/editorial/workspace/lib/presentation-review-utils.ts` (+ `.test.ts`),
`modules/editorial/index.ts`,
`app/dashboard/create/workspace/phase-review/content-phase-review.tsx` (+ `.test.tsx`),
`app/dashboard/create/workspace/phase-review/design-recovery-panel.tsx`,
`i18n/locales/en.json`, `i18n/locales/pt.json`.

Docs: `docs/architecture/openapi.json` (regenerated — additive `severity` field).

## Test Evidence

- Backend full unit suite: `2277 passed, 1 skipped` (pre-existing skip).
- New/updated backend tests: `test_presentation_casing.py` 17, plus
  `test_presentation_severity.py` / `test_presentation_policy_upgrade.py` /
  `test_presentation_policy.py` / `test_create_carousel_policy_stamp.py` — all
  green (67 in the combined new-file run).
- Route snapshot + carousel API create integration: green.
- `MYPYPATH=src mypy -p rag_backend`: `Success: no issues found in 587 files`;
  migration script mypy clean.
- `ruff check` + `ruff format`: clean on all touched files.
- Frontend: `presentation-review-utils.test.ts` (13) + `content-phase-review.test.tsx`
  (5, incl. warning-tier render) + `design-phase-review.test.tsx` (5) green;
  `tsc --noEmit` clean; `eslint --quiet` exit 0; `lint:i18n` OK.

## QA Report

Pending.

## Decision Log

### 2026-07-10 (r5) — Cold-critic BLOCKERs resolved: migration re-validates + rollback pinned

Round-5 caught that the auto-upgrade re-labeled without re-validating
(stale stored v1 reports would still be served to final_review-parked
projects — the reviewer approves casing violations they never saw) and
that a rollback after the run-once migration had unspecified behavior for
v2-stamped rows. Resolutions: the migration re-validates and stores fresh
reports; the loader's unsupported-version behavior is pinned to
fallback-to-v1-with-warning (never raise) with a seeded test; the
migration is idempotent with a down path. Cross-ticket integration test
(warning + blocker in one report) added.

### 2026-07-10 (r4) — Cold-critic BLOCKER resolved: stored report is severity-aware

Round-4 caught that `validate_localized_slides` hardcodes `blocking=True`
into the stored report the client reads verbatim — changing only the
approval-gate decision would render casing warnings as blocking in the UI
while approval succeeds, and would fight AE-0310's blocking-driven
recovery UI. Resolution: every stored-report producer computes `blocking`
from severity (AC + stored-report test added). Also pinned: the in-flight
auto-upgrade migration is deploy-gated on AE-0311 (no warnings without a
working fix button), and new-carousel v2 routing gets an explicit
create-time stamping path (`DEFAULT` stays v1 for legacy NULL rows).

### 2026-07-10 (r3) — Cold-critic WARN resolved: v1 in-flight auto-upgrade + policy-YAML proper nouns

Round-3: the r2 "informational note" for v1 projects would let the
66014ba3 incident class recur for every carousel in flight at deploy.
Resolution: run-once migration auto-upgrades non-completed projects to v2
(safe — casing is warning-severity); completed projects stay frozen. The
proper-noun list moves into the policy YAML (no code deploy per name),
and the per-rule blocking sweep enumerates codes dynamically from the
loaded policy.

### 2026-07-10 (r2) — Cold-critic WARNs resolved: absent-severity default + v1 cohort

Round-2: (1) pinned the absent-severity behavior at three layers — code
default `blocker`, loader assertion that every v2 rule carries an explicit
severity, and a per-rule blocking regression sweep — so one missing YAML
tag can never silently unblock a rule. (2) `repair_casing` is
policy-version-gated: v1 projects get neither casing violations nor
casing mutations (honest button; opt-in upgrade path noted in the repair
response, no auto-upgrade).

### 2026-07-10 — Cold-critic BLOCKER resolved: severity tier is net-new

External GLM 5.2 review verified `SlideValidationViolation` has no severity
field and `build_validation_report` is binary (any violation → blocking).
Resolution: the severity model (enum + severity-aware blocking decision) is
now explicitly in scope and ships atomically with the casing rules, so a
warning-tier rule never exists before the tier does. Cross-ticket invariant
with AE-0309 declared and covered by a dedicated test + Gherkin scenario
(casing-only violations neither retry nor block). "Frontend: no new
components" corrected — warning styling is a component change.

### 2026-07-10 — Cold-critic INFO resolved: policy versioning pinned

The policy is a flat singleton (`hero_lower_third_v1.yaml`), not
folder-versioned. Decision: ship `hero_lower_third_v2`, add to the
supported set, route new carousels to v2, never modify v1.

## Blockers

None.

## Known Gap (flagged for QA / follow-up)

**Live workflow policy-version threading for BRAND-NEW projects.** Create-time
stamping sets `carousel_projects.presentation_policy_version = v2` (the pinned
mechanism, tested). However, the live content-drafting/review workflow currently
resolves its policy version from the drafts' embedded `policy_version`, which the
content-draft agent stamps from `InstructionContextRequest.policy_version`
(defaults to `DEFAULT_PRESENTATION_POLICY_VERSION` = v1) — the project column is
not yet threaded into `get_initial_carousel_state` /
`FailClosedReviewCommand.policy_version`. Consequences:

- In-flight projects: fully covered — the run-once migration bumps the project
  AND re-validates the checkpoint under v2 (casing warnings surface at review).
- Validation with an explicit `policy_version=v2`: fully covered and tested.
- Brand-new projects: casing rules will NOT fire live at content review until the
  project's v2 version is seeded into the workflow state at start and passed into
  the content-review command (a cross-layer change spanning the engine start,
  state seed, content node, and fail-closed command). This was deliberately left
  out of this change to avoid an under-tested modification to the live pipeline;
  recommended as a focused follow-up (or folded into AE-0311's endpoint work,
  which already threads policy versions). The severity model, casing rules,
  repair, v2 policy, loader safety, migration, and frontend are all complete.

## Final Summary

Pending.
