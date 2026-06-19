I need to read the referenced source files to assess the tickets against real code. Let me gather context.
Let me check for the skeptical review and kaizen session report referenced in the tickets.
Now I have all the context I need. Let me compile the adversarial review.

# Cold Critic Review

## Verdict
**PROCEED_WITH_CAUTION** — three of four tickets are well-scoped and structurally sound, but AE-0254 and AE-0257 contain material gaps that will produce a false sense of security if implemented as-written without hardening the AC.

---

## Findings

### AE-0254 — Strengthen Inline-Prompt Checker

#### [BLOCKER] The ACs for "LLM-call boundary" and "no new false positives" are in active tension with intra-procedural AST — the implementer cannot satisfy both without the ticket specifying the resolution order.

- **Assumption**: An intra-procedural LLM-call boundary check (``.ainvoke``/``SystemMessage``/``ChatPromptTemplate``) can distinguish rejected inline prompts from legitimate `render_prompt()` calls without flagging intermediate helpers.
- **Risk**: The checker must decide the status of every *call expression* passed to an LLM invocation. If `prompt = build_system_prompt(); llm.ainvoke(prompt)` is encountered where `build_system_prompt` is defined in another function, intra-procedural AST sees only a `Call` node — it cannot know whether that call resolves to a `render_prompt()` wrapper or an inline string factory. To avoid false negatives, it must flag it. But the current tree may contain exactly this pattern, causing AC-3 ("no new false positives on the current tree") to fail.
- **Impact**: The implementer will be forced to choose: (a) flag all call-result arguments → AC-3 breaks; (b) trust all call-result arguments → the original `evaluate_eeat`-class (a helper that returns an inline string) is still missed; (c) add `render_prompt` to a trusted-call allowlist → whack-a-mole redux (AE-0244's exact failure mode). Any choice invalidates one of the ACs.
- **Suggested mitigation**: Add AC language specifying the resolution order: "If a call-result argument cannot be resolved intra-procedurally, the checker flags it. If the current tree contains such patterns, either refactor them to move the prompt to the registry, or add an explicit exemption with a documented justification. AC-3 applies after those refactors." Without this, the ticket is underspecified.
- **Open question for author**: Does the current tree contain any function-call prompt argument that is *not* a direct `render_prompt()` call? If yes, how does the checker handle it without breaking AC-3?

#### [WARN] The `*_FALLBACK`/`*_TEMPLATE` exemption is gameable at function-local scope

- **Assumption**: FALLBACK/TEMPLATE-named assignments in the AST are legitimate registry-fallback constants.
- **Risk**: The current `_allowed_value_ids` checks module-level `ast.Assign`/`ast.AnnAssign` targets. A developer who writes `fallback_prompt = "You are ..."` *inside* a function body still creates an `ast.Assign` with an `ast.Name` target whose `.id` is `fallback_prompt` — the `_allowed_value_ids` logic walks `ast.walk(tree)` which includes nested scopes. So a local variable named `fallback_prompt` inside a function IS exempted. A determined developer can evade detection simply by naming their local `prompt_fallback`.
- **Impact**: The exemption is broader than intended: it protects registry-fallback constants (good) but also any local variable with FALLBACK/TEMPLATE in its name (evasion path).
- **Suggested mitigation**: Either (a) restrict `_allowed_value_ids` to module-level assignments only (check `parent` node in walk or add a depth check), or (b) explicitly document this residual gap in the script docstring (AC-4 requires documenting residual gaps) and mark it as an accepted evasion path.
- **Open question for author**: Is the intention to exempt *only* module-level registry-fallback constants, or also function-local variables named `*_FALLBACK`? If the latter, document the evasion vector explicitly.

#### [INFO] Single test fixture cannot exercise all LLM invocation patterns

- **Assumption**: One fixture (`.ainvoke()` with `prompt` local) covers the evasion class.
- **Risk**: The real `evaluate_eeat` pattern was f-string → `prompt` → probably `.ainvoke()`. The ticket's fixture tests exactly that. But the checker is supposed to also cover `SystemMessage(content=...)`, `ChatPromptTemplate.from_messages([("system", ...)])`, and helper functions returning bare multi-line literals. A single fixture file seeding one invocation pattern leaves the other patterns untested — and the real evasion vector may be one of those instead.
- **Impact**: A PR could pass the seeded-violation test while still failing to detect an inline prompt passed via `SystemMessage()`.
- **Suggested mitigation**: Either (a) require at least 3 fixtures covering the dominant patterns (direct `.ainvoke`, `SystemMessage()`, helper `return`), or (b) explicitly scope AC-1 to one pattern and document others as known residual gaps in the script docstring.

---

### AE-0255 — External Runner Doesn't Trip Guard

#### [WARN] The copy-after-guard ordering has a TOCTOU-like gap that the ACs do not test

- **Assumption**: Staging output to `mktemp`, running the guard, then copying to the requested path is safe because the copy happens *after* the guard passes.
- **Risk**: The callers (`run_external_qa.sh`, `run_external_kaizen.sh`) both use `ext_run_guarded` and then pass control to the main session. If the copy operation itself modifies a tracked file (e.g., overwrites an existing tracked `.agent/reports/x.out`), it changes the working tree's content AFTER the guard has already returned 0. The caller's subsequent `git status --porcelain` would show a dirty tree — but no one checks it. More critically, if `ext_run_guarded` is called in a loop, the copy from run N lands in the tracked tree, and run N+1's `status_before` captures it as a change from HEAD (the file was written after the guard). If the copy also creates new files (like the `.wt.log` sidecar being written to the tracked tree by error), the guard check could become inconsistent across runs.
- **Impact**: Not a security issue but a subtlety that could cause the guard to pass when the tree is actually dirtied — violating the spirit of AE-0170. The guard's contract says "does not mutate the primary working tree" — but the copy is a mutation, just a transparent one.
- **Suggested mitigation**: Change to copy-before-guard ordering: run in worktree with output in `/tmp`, copy output to requested path, THEN guard-check. The copy may dirty the tree, but the guard will catch it unless it was intentional (i.e., the output path is the only change). Alternatively, add the copy step under the guard's purview by capturing a second `status_before` that already includes the expected output path (treating the output file as an intentional, approved mutation).
- **Open question for author**: Is the output file itself supposed to be treated as an intentional, approved tree mutation (we *want* the artifact to land in the repo), or is the contract "absolutely zero mutation"?

#### [INFO] `mktemp` and `cp` across filesystems is an unhandled failure path

- **Assumption**: Staging in `mktemp` (typically `/tmp`) and copying to the tracked tree always succeeds.
- **Risk**: If `/tmp` and the repo root are on different filesystems (NFS mount, Docker bind mount, tmpfs vs ext4), `mv` fails and falls back to `cp`, which could fail with ENOSPC, EACCES, or EXDEV. The current `ext_run_guarded` has no error handling for the copy step.
- **Impact**: Silent output loss — the guard returns 0, the output file doesn't exist at the requested path, and the caller fails with a confusing "no output" error.
- **Suggested mitigation**: Add explicit `cp` + `mv` fallback with error checking, or ensure mktemp creates the temp dir on the same filesystem (e.g., `mktemp -p "$(dirname "$output_file")"`).

---

### AE-0256 — GATES_REQUIRE_ALL Isolation Fixture

#### [WARN] The fixture covers only one env var — the same failure class can recur for CI-only env vars the ticket does not address

- **Assumption**: `GATES_REQUIRE_ALL` is the only env var that flips SKIP→FAIL behavior.
- **Risk**: CI sets many other env vars (`CI=true`, `GITHUB_ACTIONS=true`, `ACTIONS_STEP_DEBUG`, etc.) that gates.sh or sub-processes could check in the future. A future maintainer adds `if [[ "${CI:-}" == "true" ]]; then ...` to gates.sh — any test that invokes gates.sh would now behave differently in CI vs locally, even with `GATES_REQUIRE_ALL` isolated. The ticket trains authors to believe "the fixture handles CI/env deviation" when it only handles one well-known case.
- **Impact**: False sense of completeness. The failure class "CI-only env var changes gate behavior" is not structurally solved; only one specific var is handled.
- **Suggested mitigation**: Either (a) rename/reframe the ticket as "Isolate GATES_REQUIRE_ALL" (not a general env-isolation fix), or (b) extend the fixture to drop a documented list of known CI env vars. The AC is already scoped to just `GATES_REQUIRE_ALL` — the issue is the *framing* of the Goal section ("Make it structurally impossible...") which implies general protection.
- **Open question for author**: Is this meant to be a general "gate tests don't inherit CI env" fix, or specifically "GATES_REQUIRE_ALL isolation"? The Goal and AC agree (just the one var), but the "structurally impossible" language in the Goal overpromises.

#### [INFO] The `test_dead_files_gate_skips_when_knip_hidden` subprocess env override already handles the CI path correctly — the fixture removal must not break it

- **Observation**: Lines 78-80 of `test_require_tool.py` explicitly set `GATES_REQUIRE_ALL=1` in `env_ci = {**env, "GATES_REQUIRE_ALL": "1"}` and re-run. After the fixture removes the var from `os.environ`, `env = {**os.environ, "FRONTEND_BIN_DIR": str(tmp_path)}` won't include it, and then `{**env, "GATES_REQUIRE_ALL": "1"}` correctly adds it back. This works correctly.
- **No material risk here** — the implementation looks straightforward and the existing test patterns are compatible.

---

### AE-0257 — Required External Skeptical for T3

#### [BLOCKER] The requirement is purely documentary — the same AI agent that fabricated false assertions is now expected to self-enforce a "required" step it previously skipped when it was "optional"

- **Assumption**: Changing "if high-risk" to "required" in `SKILL.md` and `config.yaml` changes agent behavior.
- **Risk**: The architect agent that calls itself (or another agent within the same session) to route "plan → research → validate → skeptical" is the *same reasoning system* that previously decided "not high-risk → skip skeptical." The SKILL.md text is a prompt instruction; the agent can override or forget it, just as it previously decided "if high-risk → not high-risk → skip." There is no external enforcement mechanism — no CI gate, no checklist validator, no human pre-merge step — that verifies the external skeptical was actually run. The ticket explicitly excludes automated gates as non-goals.
- **Impact**: Zero observable behavior change. The fix looks like a process improvement but provides no enforcement. The same failure class will recur: an agent will produce a T3 plan with false current-state assertions, skip the skeptical pass (because nothing forces it not to), and no human will notice until the next kaizen audit.
- **Suggested mitigation**: At minimum, add an AC for a post-plan validator or a human gate: e.g., a note in the plan template that says "External skeptical output: [missing / attached]", or a CI check that .agent/reports/AE-XXXX.skeptical-review.md must exist for any commit that modifies .agent/reports/AE-XXXX.arch-plan.md. Without *some* enforcement, this is a doc change that solves nothing.
- **Open question for author**: What prevents the same architect agent that manufactured a false "not high-risk" judgment from also manufacturing a false "skeptical review was done" assertion? If nothing, what evidence would you accept that this ticket changes behavior?

#### [WARN] "Current-state facts" is not defined — the threshold is subjective and unenforceable

- **Assumption**: Agent and human can agree on what constitutes a "current-state fact" vs. a design opinion.
- **Risk**: Every T3 plan asserts both current-state facts ("we use PostgreSQL") and design reasoning ("we should add an index"). The boundary is fuzzy. An agent could classify all statements as "design reasoning" and argue the skeptical pass is not required. A human reviewer could disagree, but the ticket provides no definition or test for when the requirement triggers.
- **Impact**: The current-state-fact trigger becomes a rubber stamp — always triggered (safe) or never triggered (useless). Without a crisp definition, the implementer will default to "always required for T3" (which matches the spirit) or "never required" (which matches the letter of a narrow reading).
- **Suggested mitigation**: Provide a concrete, testable definition: e.g., "any T3 plan that includes the phrase 'currently', 'uses', 'is built with', 'depends on', 'implements' in reference to the existing codebase, or asserts a file, function, or module exists, must include an external skeptical pass." Even a heuristic is better than none.

#### [INFO] T2 plans that skip research are equally vulnerable but not covered

- **Observation**: The problem statement (twice-false current-state assertions) occurred during architecture planning. T2 routing is `plan → optional research → validate` — no skeptical at all, even "if high-risk." T2 plans with current-state assertions have a higher risk of undetected falsehoods because they skip research entirely (fewer cross-checks), yet the ticket only tightens T3. A T2 plan can still fabricate and ship unchecked.
- **Impact**: Residual. Not a blocker for this ticket (which is scoped to T3), but the ticket should acknowledge this gap and suggest a follow-up if the failure class recurs on T2.

---

## Missing Evidence

1. **AE-0254**: What is the actual distribution of LLM invocation patterns in the scanned dirs?  How many `.ainvoke()`, `SystemMessage()`, `ChatPromptTemplate.from_messages()`, and helper `return` patterns exist? The implementer needs counts to design the intra-procedural rules correctly — the AC demands zero new false positives, but no one has surveyed the current tree for edge cases.

2. **AE-0254**: Is `render_prompt()` ever called through an alias or re-export? If the scanned dirs import it as `from rag_backend.agents.prompts.registry import render_prompt as render`, an intra-procedural check for the name `render_prompt` misses it. Same for `llm` objects that are stored as instance attributes (`self.llm.ainvoke`) — the tool needs to handle attribute chains.

3. **AE-0255**: The two callers (`run_external_qa.sh` and `run_external_kaizen.sh`) both call `ext_run_guarded` then use `$OUTPUT_FILE` afterward. Do either of them pass an output path that is inside a tracked dir *in production* (not just in test)? If the only tracked-dir output is tests, the fix is less urgent than stated. If the `.agent/reports/` output is the real production path, the fix is critical — but the ticket should cite evidence.

4. **AE-0257**: What is the concrete trigger rate? "Twice" is two incidents. How many T3 plans were produced in the same period without false assertions? If the rate is 2/5 (40%), the fix is urgent. If it's 2/50 (4%), the fix is still warranted but the urgency is different. Not having the denominator makes it hard to assess ROI on a purely documentary change.

---

## Residual Risks if Plan Proceeds Unchanged

- **AE-0254**: The checker will ship with either an evasion gap (function-call arguments trusted without resolution) or a false-positive breakage on the current tree. The developer will have to choose which AC to violate, and the review will be contentious.

- **AE-0255**: Minimal residual risk. The copy-after-guard ordering is a minor behavioral subtlety; in practice, the output file landing in the tracked tree is *intended* (we want the artifact). The guard should arguably have a pre-approved output-path allowlist instead. But with the current design, a concurrently running process that also writes to the tracked tree between guard-check and copy would go undetected — an extremely unlikely scenario.

- **AE-0256**: Low risk for this specific ticket. The fixture is straightforward, the existing test's `env.pop` is cleanly replaced, and the AC covers both directions (isolation + CI path still works). The main risk is framing — future contributors may assume the fixture covers all CI/env deviations, which it does not. Add a docstring to the fixture explicitly listing what it isolates and that other CI env vars are NOT handled.

- **AE-0257**: **Highest residual risk.** The ticket as written will produce zero behavioral change. The SKILL.md text becomes a suggestion that the same fallible agent can ignore. Future T3 plans with false current-state assertions will recur. The only salvageable outcomes are: (a) the ticket is acknowledged as a process *documentation* improvement only, with a follow-up ticket for enforcement, or (b) an automated gate is added in scope. As-is, it is the weakest ticket in the set by a wide margin.
