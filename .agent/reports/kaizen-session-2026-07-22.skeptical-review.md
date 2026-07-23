# Cold Critic Review

## Verdict
WARN

## Findings

### [BLOCKER] P1 `GATE_CAPTURE_ALLOW_DIRTY=1` re-opens the exact failure class FC-1 exists to close, without bounding its blast radius
- Assumption: A reviewer/automation will see `"dirty":N` in the GATES_JSON stamp and treat the verdict as untrusted.
- Risk: The override makes the guard opt-out-by-env-var. In a multi-session repo (the packet's own context: "repo routinely has uncommitted files from OTHER parallel agent sessions"), the *normal* state is a dirty tree. The escape hatch becomes the default operating mode; `"dirty":N` degrades to noise that nothing enforces a response to. The signal report's own AE-0301 incident was a false green where the damage (2 ruff violations) would have been *identical* under ALLOW_DIRTY=1 — the gate still no-ops on untracked files, just now with a stamp nobody is required to block on. This is a down-ratchet dressed as an UP.
- Impact: The class FC-1 (false greens) is re-permitted whenever the override is set, which the plan itself implies will be frequent. The ratchet direction claim is false for the override path.
- Suggested mitigation: Make ALLOW_DIRTY **not** skip the diff gates but instead force them into a *staged-only* mode (`git diff --cached`) so tracked-but-uncommitted work IS seen, OR require a GATES_JSON `"dirty":N>0` to be a hard transition-block at the move-time guard, not advisory. State explicitly what consumes the `dirty` stamp and blocks on it.
- Open question for author: What downstream guard reads `"dirty":N` and fails the transition? If none, the override is a silent disable and the ratchet label is wrong.

### [BLOCKER] P2 model pin assumes `opencode-go/glm-5.2` is the *funded/working* route, but the only evidence in the packet says the opposite
- Assumption: `opencode-go/glm-5.2` is the correct default and only the missing `-m` flag caused "Insufficient balance".
- Risk: The signal report R16 says the agent default (Zen `glm-5.2`) was *unfunded*, and the workaround was `opencode run -m opencode-go/glm-5.2`. The plan then sets `EXT_OPENCODE_MODEL:-opencode-go/glm-5.2` — i.e. it hard-codes the *observed workaround* as the baked-in default with no evidence that this route is stably funded, nor that it's the intended model for all external run types (QA vs. review vs. cold-critic). If `glm-5.2` funding/availability flips, the pin turns every external run red and there's no fallback path described. Also: pinning one model erases the per-task model-selection freedom thecold-critic/QA separation may want.
- Impact: A new, repo-wide single point of failure for the external QA spine; and a possible future where the pin is silently half-right (model exists funded but is wrong for a given task).
- Suggested mitigation: Source the default from a config var/env with a documented funded-route list; add a smoke test that runs a trivial `opencode run` and asserts non-empty output *at install/CI*, not just post-failure. The empty-output retry is good but it fires *after* the run is already wasted.
- Open question for author: What evidence confirms `opencode-go/glm-5.2` is currently funded and is the intended model for ALL external agent tasks, not just the one R16 workaround?

### [WARN] P3 "string-aware" parser rewrite is under-specified and may trade false positives for false negatives (a down-ratchet in disguise)
- Assumption: Stripping comments and treating strings as opaque removes ONLY false positives; "the gate's teeth are unchanged."
- Risk: A naive comment-stripper (e.g., line-based `//` removal) will corrupt `"//"` inside strings or template literals with `${}` containing `//`; a naive string-as-opaque walker will mis-handle template literals, regex literals, and multiline backtick strings — all legal in Zod object literals. The plan claims "detection surface unchanged" but introduces real risk that a genuinely drifted field name hidden behind a string/regex now parses as opaque and is *missed*. The AE-0180 tests (comment case passes, drift case still fails) are necessary but not sufficient — they don't prove no NEW false negatives exist for the myriad string/comment shapes in real source.
- Impact: A gate that previously over-reported (annoying) now potentially under-reports (dangerous, and silent). That's a potential down-ratchet mislabeled UP.
- Suggested mitigation: Use a real TS parser (e.g., the existing `typescript` package the frontend surely has) to extract the object-literal property names rather than hand-rolling a char-walker; add tests for regex literals, template literals, nested string keys, and `${//}` interpolation. State the ratchet as "UP *only if* no new false-negative test fails."
- Open question for author: Why not use the TS compiler API instead of hardening the hand-rolled walker, given the frontend already depends on typescript?

### [WARN] P4 spike has no decision threshold or time-box; "measure-then-decide" hides a likely indefinite deferral
- Assumption: The spike produces a count that maps cleanly to a "small vs. large" decision.
- Risk: There's no definition of "small" or "large" fallout, no time-box, and no ratchet-baseline file specified upfront. "Large → enable via a ratcheted follow-up" is a generic commitment with no date/owner/error-count threshold; the classic end state is a spike report and the flag never gets enabled. FC-4 remains open and there's no gate forcing closure. The plan's own record (AE-0295 fixed one instance, class still unenforced) is the precedent for exactly this kind of instance-only resolution.
- Impact: FC-4 recurrences remain possible; the spike is plausible-deniability for inaction.
- Suggested mitigation: Pre-commit the decision rule: e.g., "≤K errors → fix & enable in this ticket; >K → create follow-up ticket + add `noUncheckedIndexedAccess: false` with `// @ts-expect-error` baseline in this ticket, and flag follow-up as blocker-ranked." Require the follow-up ticket to be *emitted by this ticket's completion*, not deferred.
- Open question for author: Define K and the time-box; what stops this from becoming another AE-0295-style "instance fixed, class open" outcome?

### [WARN] P5 one-command regen removes the friction that was also a guardrail; no integrity check that regen was run *completely*
- Assumption: Bundling the 4 steps removes friction without removing safety; the pinned gates remain enforcers.
- Risk: The 4 separate gates currently act as a *checklist* — each red gate forces an explicit re-run and surfaces partial-regen states. A one-shot script that runs all 4 silently can *partially* succeed (openapi.json regenerates, a snapshot update fails) and leave the repo in an inconsistent state that diff gates may not catch until next CI. Worse, the packet's own context notes an `.env-CWD` landmine on `export_openapi.py`; the script "cd's into backend/ itself" — but if any of the 4 steps assumes a different CWD or env var, the bundle now hides that in a script rather than surfacing it in docs/landmines. Also: `--snapshot-update` is a write operation; bundling it into a `make` target makes accidental local clobbering easy.
- Impact: Partial/failed regens become less visible, not more; possible broken snapshots committed.
- Suggested mitigation: Script must run all 4 steps and `exit 1` if ANY step fails, leaving no partial artifacts (or atomically writing to a temp dir and swapping); add a post-regen verification step that re-runs the read-only snapshot tests green-before-commit.
- Open question for author: What guarantees atomicity/all-or-nothing across the 4 steps, and what blocks committing a half-updated snapshot?

### [WARN] P6 codifies a convergence rule derived from n=2 sessions; risk of prematurely canonizing an under-evidenced heuristic
- Assumption: "3 consecutive zero-blocker rounds" is the correct stop rule (not just the one two sessions happened to use).
- Risk: Two sessions is thin evidence for a permanent rule, and the number 3 is arbitrary — no analysis of whether 2 would have sufficed or whether certain defect classes need 4+. Canonizing it may cause premature stops on complex work (FC-6's original concern: "premature stop") — i.e., it can *cause* the failure it's meant to prevent. Also: "severity trajectory, not verdict text" presumes reviewer consistency in assigning BLOCKER vs WARN across models/sessions; if a reviewer downgrades a real blocker to WARN, convergence is falsely declared.
- Suggested mitigation: Document as *default* stop rule, not absolute; allow override with recorded justification; add a calibration note that WARN→BLOCKER boundary inconsistency is a known noise source.
- Open question for author: Is there any across-model calibration of BLOCKER severity, or is "zero BLOCKERs" sensitive to reviewer drift?

### [INFO] S1/S2 supplemental candidates are included but unowned; they can drift forever
- Assumption: Marking "user undecided" keeps them visible without forcing a decision.
- Risk: Kaizen's purpose (per the packet) is to convert tribal knowledge into enforcement; S1 is described as a *clobbering prod bug* ("bugfix-ticket candidate") sitting in the same plan that criticizes leaving things as landmines. Carrying S1 as "supplemental, undecided" reproduces the exact class the plan is meant to close.
- Suggested mitigation: Force S1 to a ticket decision (file or reject with reason) within this cycle; S2 genuinely can stay optional.
- Open question for author: Why is a known clobbering prod bug kept as a candidate and not promoted?

## Missing evidence
- What consumes `GATES_JSON` `"dirty":N` and hard-fails on it (P1)? No consumer was named.
- Current funded status and intended-task fit of `opencode-go/glm-5.2` across QA/review/cold-critic (P2).
- Fallout count distribution from a real `noUncheckedIndexedAccess` dry-run (P4) — the plan defers the measurement but commits to an outcome-dependent path without defining the threshold.
- Whether `splitTopLevelFields()` is exercised by tests over template literals / regex / `${//}` interpolation today (P3).
- Snapshot of current external-review stop-rule usage: n=2 is the entire empirical basis for P6.
- Whether the multi-session dirty-tree state is *expected* at move-time (context says it "routinely" is) — if expected, the default (fail) branch of P1 will fire constantly, suggesting the override is the real path and the guard is theater.

## Residual risks if plan proceeds unchanged
- FC-1 false greens remain possible whenever `GATE_CAPTURE_ALLOW_DIRTY=1` is used (likely often in a multi-session repo); the override path is a silent down-ratchet mislabeled UP.
- FC-2 external runs become single-model dependent; a funding/availability flip reds-out the whole external QA spine with no fallback.
- P3 may introduce *false negatives* — a silent weakening — if the hand-rolled string/comment handling misses edge cases; ratchet mislabel.
- P4 may stall as "spike needs follow-up" with no forcing function, leaving FC-4 class-level open indefinitely.
- P6 may cause *premature convergence* if BLOCKER/WARN assignment drifts across reviewers/models — the exact harm FC-6 targets.
- S1 (a prod-clobbering bug) sits ungated; the plan reproducibly leaves a known defect as tribal knowledge, which the plan's own philosophy condemns.
