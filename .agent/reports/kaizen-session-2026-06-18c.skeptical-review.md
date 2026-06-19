I'll start by verifying the stated repo facts and examining the relevant code paths to ground my adversarial review in actual code, not hearsay.
Now let me verify the `gate_frontend_dead_files` behavior and the `lint:dead-files` npm script definition:
Let me get some final context — the `.gitignore` and the existing `render_board` regeneration pattern:
Now I have a thorough understanding of the codebase. Let me synthesize the review.

# Cold Critic Review

## Verdict
**WARN** — proceed only after the cross-cutting sequencing risks are addressed and the barrel-policy decision is documented. P1-P3 are well-motivated; P4 needs tighter scoping.

---

## Findings

### [BLOCKER] P1 — Board-auto-regenerate creates a concurrent-writer blind spot

- **Assumption:** regenerating BOARD.md from render_board and then mutating it in the same call is safe because the agent task scripts are serial CLI invocations.
- **Risk:** the `make board` target (via `render_board.py`) writes BOARD.md from scratch based on current `Status` fields. If `add_to_board()` regenerates then mutates, there is a TOCTOU window between `read_text()` → `replace()` → `write_text()` in the mutation step where a concurrent agent could also regenerate the board, and one writer's changes get silently dropped. Two agents running `create_ticket.py` simultaneously (e.g., parallel session handoffs) would race on the board file. The probability is low but the failure mode is silent data loss (a ticket disappears from the board).
- **Impact:** dropped ticket entries in BOARD.md with no error.
- **Suggested mitigation:** use an atomic file-write strategy (write to `.board.tmp`, `os.replace()`) for both `render_board.py` and the mutation functions. Even in CLI serial context, this is a cheap hardening step and documents awareness of the race.
- **Open question:** is the board intended to be a concurrent-writer file? If yes, a `filelock` or advisory lock might be warranted.

### [BLOCKER] P1+P2 — Stacked-merge timing: P1's board regeneration is already needed before P2 lands

- **Assumption from packet:** PR #54 (gitignore-board) and #55 (stacked) are both unmerged. Therefore P1-P4 ride on top.
- **Risk in live tree:** commit `789220ad` (gitignore-board) IS already an ancestor of HEAD. This means the crash-in-absence bug that P1 fixes is already latent in the current working tree. CI gate `agent-ticket-hygiene.yml` clones fresh and runs `pytest tests/unit/agent_tasks/` — tests that currently DO NOT exercise `add_to_board` or `update_board`. As soon as someone adds tests for those functions (as P1 proposes), the absent-board test will fail on the current code unless the fix ships in the same commit. The ordering trap: if the test is written first (TDD), CI breaks immediately. If the fix is written first, there's no regression test on the uncovered gap.
- **Impact:** partially-merged stack could produce a commit that passes CI but breaks the board mutation for any fresh checkout.
- **Suggested mitigation:** merge P1 (fix + tests) as a standalone PR BEFORE any other ticket that calls `add_to_board`/`update_board` in CI. Alternatively, ensure the tests use `tmp_path`-based monkeypatching of `BOARD_PATH` so they don't touch the real `.agent/` at all.
- **Open question:** are P1-P4 intended to ship as one PR or separate stacked PRs? The landing-order constraints change accordingly.

### [BLOCKER] P2 — Duplicate-ID blocking only catches branch-vs-main, not parallel-vs-parallel

- **Assumption in packet:** "on a GitHub `pull_request` run the merge ref is checked out, so a branch whose new ids collide with main fails the gate before merge."
- **Risk:** this is true for a single branch colliding with main. However, two parallel PRs (branch-A adds AE-0501, branch-B adds AE-0501) each pass their own CI: GitHub checks out the merge result of `main+head`, and the other branch's AE-0501 file is NOT present in either merge result. Both PRs go green. When A merges, B's CI is already green, and B can merge immediately after — landing duplicate AE-0501 on main. The blocking gate detects this post-facto only on push to main (the CI triggers on push too), so it would fail on the merge to main, but only *after* the merge commit lands. If the deploy-on-push is fast enough, production deploys before the gate catches it.
- **Impact:** duplicate IDs land on main, deploy production, and the CI failure fires after deploy.
- **Suggested mitigation:** either (a) make duplicate-ID detection a **required check** on the CI-gate aggregator (AE-0203's single required check) that triggers on push and blocks subsequent merges, or (b) document that the merge-to-main race window exists and accept the post-facto detection (since `_report_attributed_to` still prevents freeload). Document the explicit gap.
- **Open question:** has the team considered a centralized ID allocation service (e.g., a GitHub Action that reserves IDs via an API on the repo's issue tracker) to eliminate the root cause?

### [WARN] P1 — Board regeneration side effects on ticket file state

- **Assumption:** calling `render_board` from within `add_to_board` or `update_board` is a transparent operation that only affects BOARD.md.
- **Risk:** `render_board.py` calls `load_tickets(TASKS_DIR)` which calls `parse_ticket()` on every file. If a ticket file is temporarily in an invalid state (e.g., being edited), `parse_ticket` returns `None` and the ticket silently disappears from the regenerated board. Then the mutation function writes the board again, and the ticket is double-dropped.
- **Impact:** a ticket disappears from the generated board without warning.
- **Suggested mitigation:** after regenerating the board, re-validate that the ticket being added/moved appears in the output. If not, log a warning and do a second full render.
- *Note: lower probability on local CLI, but if the tooling runs in CI (e.g., validate step), a race with an editor could trigger this.*

### [WARN] P2 — Seeded test must account for the exit-code boundary with existing `_warn_duplicate_ids` behavior

- **Assumption:** changing exit code from 0 to 1 when duplicates exist is a simple numeric change.
- **Risk:** the current `_warn_duplicate_ids` function name starts with underscore, suggesting it's private. The exit code logic is in `main()`:
  ```python
  _warn_duplicate_ids(tickets)
  blocking = 0
  for ticket in tickets:
      errors = validate_ticket_file(ticket)  # <-- this accumulates blocking errors
  if blocking:
      return 1
  ```
  Making `_warn_duplicate_ids` blocking means it must either (a) increment `blocking` instead of only printing, or (b) call a new separate counter that feeds into the exit code. The subtle edge: if there are also regular validation errors, the exit code is already 1. If there are ONLY duplicate-ID warnings, the exit code changes from 0 to 1. Need to ensure the test asserts exactly this case.
- **Suggested mitigation:** in the seeded test, create two files with the same AE-#### ID and NO other validation errors, then assert exit code 1. This is the pure edge case that changes behavior.

### [WARN] P3 — The "preflight" mechanism needs careful integration with the existing advisory-gate pattern

- **Assumption:** checking if `knip`/`jscpd` are resolvable and giving a helpful message is straightforward.
- **Risk:** The `gate_frontend_dead_files` gate is explicitly advisory and swallows errors:
  ```bash
  npm run lint:dead-files || echo "ADVISORY: knip dead-file findings above"
  ```
  If a preflight check exits early before the `||` can swallow it, the advisory gate would suddenly start FAILING when tools are absent. But in CI, `npm ci` installs them, so this only affects local runs. The risk is that local runs get a raw FAIL on an advisory gate, which is a worse UX than today's SKIP (which is what the run_gate machinery maps exit 127/1 to — actually, 127 maps to `status="FAIL"` in `run_gate`). Today, when knip is absent locally:
  1. `npm run lint:dead-files` fails (non-zero exit)
  2. `|| echo "ADVISORY"` catches it → exit 0
  3. Gate PASSES
  With a preflight that exits before the npm script, the `||` never fires, and the gate FAILs.
- **Suggested mitigation:** make the preflight return `EXIT_SKIP` (77) when tools are missing on advisory gates, not `EXIT_FAIL`. For blocking gates, return `EXIT_FAIL` with the helpful message. The skip/block distinction is important.
- **Open question:** what about `npx`? `npx knip` auto-installs if missing. Do you actually want to check for `node_modules/.bin/knip` rather than `which knip`? `which` won't find npm-installed binaries.

### [INFO] P4 — Knip-reported "unused files" can include false negatives from dynamic references

- **Assumption:** the ~9 files flagged by knip are "genuinely dead" and safe to delete.
- **Risk:** knip's file-scope detection (`--include files`) traces static imports only. It does NOT detect files loaded dynamically (e.g., `import()` expressions with computed paths, file-based routing, `fs.readFileSync` of a module, or config files referenced by Next.js config `pageExtensions` or `layout` conventions). The `personas/` route files flagged as unused might be genuinely live if the route is active but no component statically imports them. Before deleting any file, you must verify absence of *any* reference (grep the whole repo including config files, dynamic imports, and test fixtures). Knip's "unused" is a heuristic, not a proof.
- **Impact:** deleting a file that IS referenced dynamically breaks the build, possibly in an edge case that CI doesn't catch (e.g., admin-only route).
- **Suggested mitigation:** for each candidate file, run `rg -l --no-ignore-vcs <basename>` across the entire repo, then run tests after deletion. Do not rely solely on knip's output. The barrel re-export files (design-system `index.ts`) must be especially scrutinized because their consumers bypass the barrel (128 direct imports), meaning the barrel IS dead — but that changes the team's import convention retroactively.

### [INFO] P4 — Barrel policy decision has lasting consequences and should be documented

- **Assumption from packet:** "either configure them as knip `entry` points or migrate consumers to import via the barrel — a one-time convention decision."
- **Risk:** the choice is not symmetric. If you make barrels `entry` points, they are permanently invisible to knip's dead-file analysis — they can never detect a barrel that has become empty or useless. If you migrate all 128+ direct imports to go through the barrel, that's a large, tedious, review-heavy change with no behavioral benefit (the direct imports work fine). The real question is: do you want barrels to serve as a public-API contract (all consumers must import from the barrel) or are they optional sugar? This is an architectural convention that should be decided, documented, and enforced — not buried in a T2 cleanup ticket.
- **Impact:** whichever path is taken changes the team's import hygiene pattern permanently. An undocumented tacit decision will be confusing to new contributors.
- **Suggested mitigation:** write a short decision record or update the existing module-convention docs. Separate the truly-dead-file deletion (uncontroversial) from the barrel-policy decision (controversial, needs team alignment). Do not combine them in one ticket.

---

## Missing evidence

1. **P1 — Concurrent-agent-usage pattern.** Are agent task scripts ever invoked by two agents/terminals simultaneously (e.g., parallel Cursor sessions, or a CI job and a local agent)? The board file's concurrency contract is implicit but critical for deciding whether a file lock is needed.

2. **P2 — Historical collision count.** The packet says collisions occurred twice. Were both caught pre-merge or post-merge? What was the remediation time? This data would calibrate whether a blocking gate is urgent or merely nice-to-have.

3. **P3 — Actual CI error messages when tools are absent.** Has a contributor hit the unhelpful error in practice? The packet implies yes, but without knowing the frequency, it's hard to size the priority against the other proposals.

4. **P4 — Inventory of the 21 knip-flagged files with manual verification.** Which 9 are "genuinely dead" — what grep/code-ownership evidence supports each one? Which 7 are barrels, and what are their import counts/distribution? The packet gives approximate numbers but no filenames or evidence traces.

5. **Stacking — Actual PR numbers and branch names for #54 and #55.** The tree shows commit `789220ad` (gitignore-board) is already an ancestor of HEAD. If #54 has merged, it changes the landing-order analysis significantly. If it hasn't, the current tree is not reflective of actual PR state.

---

## Residual risks if plan proceeds unchanged

1. **Landing-order explosion:** If P1-P4 ship combined with the existing stacked PRs, and the base PR (#54, gitignore-board) auto-deploys upon merge, then the deploy that lands the gitignore-board change also ships the broken `add_to_board`/`update_board` code to main. Any CI job between the #54 merge and the #55 merge that calls those scripts will crash. The window is small (hours, ideally), but production deploys on every main push.

2. **Duplicate ID still lands on main before gate fires:** P2's blocking gate catches the merge-to-main push but only *after* the commit is on main. The deploy.yml workflow might have already started the rollout. The mitigation is to make the duplicate-ID check a pre-receive hook or a required status check on the CI-gate aggregator that blocks **before** GitHub allows the merge button to be pressed.

3. **P4 deletions could break the build on a dynamic import path that knip missed.** Without manual grep verification per file, the risk is small but real. And the advisory nature of the dead-files gate means the current CI wouldn't catch a mistaken deletion — the deletion itself would need to be caught by the build gate if the missing file breaks an import chain. If the file is only used at runtime via a dynamic path, only production would break.

4. **Barrel-policy drift:** Without a documented decision, months from now a future cleanup ticket will face the same question with more debt. The "one-time convention decision" in P4 either needs to happen now with enforcement, or be deferred explicitly with the barrels configured as knip `entry` points and a note added to the module docs. Doing nothing is a decision by default — and it's the wrong one if the team wants strict barrel usage.
