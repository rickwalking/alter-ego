I'll begin by verifying the packet's factual claims against the live codebase before issuing my review. Let me read the referenced files in parallel.
Now let me check the guard check script and look for the architect skill location, plus validate the pytest test's claim about the popped env var.
Now let me check one more thing — the researcher protocol reference for completeness.
Here is the adversarial review.

# Cold Critic Review

## Verdict

**BLOCK** — Two proposals have material gaps serious enough to warrant redesign or evidence before merging.

---

## Findings

### [BLOCKER] P1 — Structural AST detection of LLM-bound prompts is not feasible with Python's `ast` module

- **Assumption:** The checker can statically determine whether a multi-line string is "passed to an LLM call (`ainvoke`/`.invoke`, `SystemMessage`/`HumanMessage`, `ChatPromptTemplate.from_*`)" using Python's `ast.walk()`.
- **Risk:** This is a data-flow analysis problem, not a local syntactical one. A multi-line string defined in function `A` and passed as an argument to function `B` which calls `.ainvoke()` requires cross-function call-graph tracking. Python's `ast` module gives flat AST trees with no inter-procedural understanding. Consider:
  ```python
  def build_prompt() -> str:
      return """You are a helpful assistant. """  # no marker
  prompt = build_prompt()
  llm.invoke(prompt)
  ```
  The `ast.Constant` containing the string and the `ast.Call` containing `.invoke` are in different branches of the tree. No local pattern can connect them without resolving the call graph and the return-value identity — neither of which Python's stdlib `ast` provides.
- **Impact:** The "passed to an LLM call" branch would either (a) be unimplementable within the stdlib-only constraint the checker currently respects, or (b) produce rampant false negatives (only catching strings that happen to be AST-siblings of an `.invoke` call within the same function body, missing the common pattern of a builder function returning a prompt). The proposal would functionally devolve to the `*prompt*`/`*_PROMPT` naming branch, which is trivially evadable by naming the variable `my_string` instead of `my_prompt`.
- **Suggested mitigation:** Explicitly acknowledge that only lexical adjacency (same-function `ainvoke` call) is detectable, and the `*prompt*` naming is a naming-convention heuristic, not a structural guarantee. Alternatively, switch to a runtime scanning tool (e.g., a custom ruff rule with control-flow analysis) if the stdlib-only constraint is negotiable.
- **Open question for author:** Do you accept that the "passed to an LLM call" branch will detect only the subset of strings that are inline literals in the same function body as the call, and that the naming-convention branch is trivially by-passable? If so, what is the concrete detection improvement over the existing marker list?

---

### [BLOCKER] P1 — The `*_PROMPT` naming check would break the existing FALLBACK/TEMPLATE allowlist pattern

- **Assumption:** Adding `*_PROMPT` / `*prompt*` as a trigger condition is purely additive (widen the detection net) and does not conflict with any existing patterns.
- **Risk:** The existing codebase has `*_FALLBACK` and `*_TEMPLATE` as **exemptions**. But the proposed `*_PROMPT` check would catch a constant named `_ALTER_EGO_FALLBACK_PROMPT` because its name contains `PROMPT`. The current `_allowed_name` check in `check_inline_prompts.py` uses `_ALLOWED_NAME_TOKENS = ("FALLBACK", "TEMPLATE")`. Under the proposal, a multi-line string assigned to `_MY_FALLBACK_PROMPT` would be simultaneously:
  - **Allowed** by the FALLBACK name check (existing branch), and
  - **Flagged** by the `*_PROMPT` name check (new branch).
  The order-of-operations between the new trigger and the existing allowlist is unspecified. If the new check is applied first, every `*_FALLBACK_PROMPT` constant with a multi-line string becomes a violation, breaking the existing registry-fallback convention.
- **Impact:** Either the FALLBACK/TEMPLATE exemption must take priority (making the new `*_PROMPT` check useless for those variables) or the exemption is silently broken — silently because the current test only covers `_THING_FALLBACK` (no `PROMPT` in the name).
- **Suggested mitigation:** Define the priority chain explicitly: `docstring > FALLBACK/TEMPLATE > structural trigger > marker trigger`. Add a test case with `_MY_FALLBACK_PROMPT` to prove it is NOT flagged.
- **Open question for author:** Which priority order do you intend? Should a constant named `_FALLBACK_PROMPT` be flagged or not?

---

### [WARN] P2 — Moving `.wt.log` to a `mktemp` path removes only ONE of two leak sources

- **Assumption:** Moving `.wt.log` to a non-repo path fully resolves the guard-tripping when the output path is in a tracked directory.
- **Risk:** `ext_run_guarded` at line 129 runs the external tool inside the worktree but writes the output file to `$output_file`, which is the same path as the caller specified. If that path is inside a tracked directory (e.g., `.agent/reports/report.md`), the tool writes to the **primary repo** via the worktree's git-aware path, modifying `git status --porcelain`. The `.wt.log` being moved to `/tmp` prevents ONE file mutation, but the primary output file itself still mutates the working tree and trips the guard. The stated problem — "forcing a manual workaround (write output to /tmp) on every run" — persists.
- **Impact:** The proposal is strictly better (eliminates one aggravating factor) but does not fully close the failure class described. A user who forgets the `/tmp` output convention will still trip the guard.
- **Suggested mitigation:** Either (a) also redirect the output file itself to a `/tmp` staging path and copy it to the requested location only AFTER the guard check passes, or (b) document explicitly that the proposal's scope is limited to the sidecar, and the output-file convention remains a caller responsibility.
- **Open question for author:** Is the intent to fix only the `.wt.log` sidecar (leaving the output-file leak as a caller convention), or should the fix also stage the output file and copy it after the guard check? The answer affects whether a test with "output under a tracked dir" would actually pass.

---

### [WARN] P2 — No cleanup of `.wt.log` on non-error paths

- **Assumption:** Writing to `mktemp` is sufficient; the OS will eventually clean up `/tmp`.
- **Risk:** The current `external_agent_guard_check.sh` traps `"$out".wt.log` cleanup (line 15), but the real `ext_run_guarded` function in `external_agent.sh` has **no trap** for the sidecar. Only the worktree is cleaned. A `mktemp` path under `/tmp` that is never cleaned is a minor leak (not security-critical), but it's inconsistent with the guard-check test's rigor.
- **Impact:** Accumulation of stale `.wt.log` files in `/tmp`, especially if `ext_run_guarded` is called frequently (e.g., during CI or automated QA sweeps).
- **Suggested mitigation:** Add a `trap` in `ext_run_guarded` to delete the `mktemp`'d sidecar, or use `mktemp --tmpdir` which auto-cleans on some systems. Document the temp-file lifecycle.
- **Open question for author:** Should the sidecar be cleaned immediately (trap), or is leaving OS-temp files acceptable?

---

### [INFO] P3 — Autouse fixture is correct but the conftest boundary is not tested

- **Assumption:** An autouse fixture in `backend/tests/unit/scripts_ci/conftest.py` covers all gate tests.
- **Risk:** If a developer adds a second test file under `scripts_ci/` (e.g., `test_gates_foo.py`) without importing conftest, the fixture does not apply. In practice, pytest auto-discovers conftest.py in parent directories, so `conftest.py` at `tests/unit/scripts_ci/conftest.py` covers all files in that directory. This is the standard pytest mechanism, so the risk is low.
- **Impact:** None under normal usage. The gap would only occur if someone bypasses conftest (e.g., running a standalone test script outside pytest).
- **Suggested mitigation:** None needed beyond the standard conftest pattern. The proposal is sound.

---

### [WARN] P4 — Documentation-only enforcement of "file:line cite" is unverifiable

- **Assumption:** Adding a rule to the architect skill doc that requires file:line cites for current-state assertions will materially reduce false assertions.
- **Risk:** The root cause of the twice-observed failure is that LLM subagents produce plausible-sounding but wrong assertions. Adding a rule in a markdown file that the same LLM subagent is expected to self-enforce is circular: the agent that fabricated the false assertion is the same agent expected to verify it. The external skeptical pass (cross-LLM) is the actual enforcement, and it already exists. The proposed rule adds ceremony without adding a detection mechanism.
- **Impact:** The proposal is a documentation improvement, not a structural fix. It may reduce the frequency of false assertions if subagents are prompted to call `read`/`grep` tools for verification, but there is no way to detect non-compliance without reviewing every plan artifact manually.
- **Suggested mitigation:** Two options: (a) Add an automated post-generation check in the architect plan mode that scans the plan for unresolved assertions — e.g., flag any claim pattern like "directory X is empty" or "component Y is stateless" that lacks a `file:line` cite, and fail the plan generation step until cites are present. (b) If soft/documentation-only is the intent, relabel from "ratchet HOLD" to "documentation improvement" and acknowledge in the proposal that it does not ratchet the enforcement bar at all.
- **Open question for author:** The packet acknowledges "Soft/documentation enforcement only." Is the intent to keep this as a prompt-only change, or would you accept a lightweight automated check (e.g., a post-hoc scan of the plan `.md` for claims missing cites)?

---

### [INFO] P4 — T3 skeptical pass: "REQUIRED" changes the tier routing from the current spec

- **Observation:** The current architect skill (SKILL.md line 32) says for T3: "plan → research → validate → **skeptical if high-risk**". The proposal says "reaffirm the external skeptical pass as REQUIRED (not optional) for T3 plans". This changes T3 routing from conditional to unconditional. If that is the intent, the SKILL.md tier table and config.yaml would both need updating. The packet correctly states "Soft/documentation enforcement only."

---

## Missing evidence

1. **P1 — Feasibility of data-flow analysis with stdlib `ast`.** The packet asserts structural detection is feasible but provides no prototype or citation. A proof-of-concept showing that the checker can detect `evaluate_eeat`'s pattern structurally (where the f-string was returned from a function, not passed directly to `.ainvoke`) would resolve the Blockers. As written, neither the "passed to an LLM call" nor the "naming" branch would catch the `evaluate_eeat` pattern that was the original miss — the string was returned from a helper function, not passed to `.ainvoke` in the same function, and it was not assigned to a `*_PROMPT` variable (it was an inline f-string in a `return` statement).

2. **P2 — Callers of `ext_run_guarded` and their `$output_file` conventions.** The packet references `.agent/reports/` as a tracked output dir. A grep for `ext_run_guarded` call sites would clarify how many callers pass tracked-dir paths, and thus how many would still trip the guard after the `.wt.log` fix.

3. **P4 — Specific incident reports for the two false-assertion events.** The packet says "subagents twice asserted FALSE current-state facts" but provides no ticket numbers, report filenames, or examples. Without these, it's impossible to assess whether the proposed rule would actually have prevented the incidents (or whether they were caused by factors the rule doesn't address, such as stale scan results or insufficient read depth).

---

## Residual risks if plan proceeds unchanged

- **P1 would ship a checker whose "structural" branch cannot detect the `evaluate_eeat` failure class** — the exact pattern that motivated the proposal. The countermeasure (marker + naming OR) would be no stronger than the current marker-only approach. A future inline prompt that avoids all markers and is not named `*_PROMPT` would pass identically. **The failure class is not closed.**
- **P2 would fix the `.wt.log` sidecar but not the output-file leak** — users who write output to tracked dirs still trip the guard. The fix is partial; the workaround (write to `/tmp`) persists.
- **P3 is low-risk and ratchets a meaningful structural guarantee** — this could proceed independently with no residual risk.
- **P4 adds a documentation rule that the violating agent must self-enforce** — no structural change to the failure class. If the same LLM subagent generates the plan and is told to "verify with file:line," its known tendency to hallucinate cites (producing plausible but wrong file:line references) becomes a new failure mode: **incorrect but verifiably-formatted cites**, which look convincing and are harder for a human reviewer to spot than a bare false assertion.
