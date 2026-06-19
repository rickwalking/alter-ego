Now let me also check the `check-integrity.sh` script briefly to understand its output format:
# Cold Critic Review

## Verdict

**WARN** — P1 has material gaps that make it partially security theater; P3's core assumption is unenforceable; P2 is correct-but-weak. Each proposal fails to address at least one stated problem.

---

## Findings

### P1 — `GATES_JSON` proof in QA report before Review

#### [BLOCKER] P1.1 — The validator cannot distinguish a forged GATES_JSON from a real one, and the "CI catches it later" mitigation is weaker than claimed

- **Assumption:** A forged GATES_JSON will be caught by CI re-running gates, and SHA pinning makes forging detectable.
- **Risk:** The SHA pinning compares the report's claimed SHA against `git rev-parse HEAD` —  but they match trivially when the validator runs. The forgery surface is: agent runs no gates, fabricates `GATES_JSON: {"pass":18,"fail":0,"skip":0,"results":[...]}`, writes it into `.qa.md` pinned to the current HEAD, runs `validate_all_tickets.py` → passes → moves ticket to Review. CI *will* catch it later, but the ticket is now in Review. A human (or a reviewer who trusts the green validator) may approve based on the `.qa.md`. The proposal lowers forge effort from "write three words" to "construct a JSON blob" but does not structurally prevent it. CI-as-backstop only helps after a human is notified, which is after the gate was meaninglessly satisfied.
- **Impact:** The proposal improves observability (a human can glance at GATES_JSON) but does not make the *automated gate* meaningfully harder to bypass. The "self-pasted, hence forgeable" limitation is stated but its consequence is understated: this is a **deterrent, not a control**.
- **Suggested mitigation:** Make the validator *re-run* `gates.sh` itself at the `can_transition(STATUS_REVIEW)` checkpoint and compare the live output to the report's claimed GATES_JSON. If they differ → block. This turns the validator from a passive format-checker into an active verifier. Yes, it's slower; gate it behind `--verify-gates` or run it only when `gates.sh` is available.
- **Open question for author:** If forgery is the stated residual risk, what specifically prevents an agent from writing `fail:0, skip:0` without ever running gates? The answer "CI catches it" still puts a forged ticket in Review — is that acceptable? If yes, the proposal should call this an informational ratchet, not a "require" gate.

#### [WARN] P1.2 — `skip=0` requirement forces false positives for legitimate skips

- **Assumption:** Every gate can always run; `skip=0` is achievable for a proper run.
- **Risk:** Legitimate runs without Postgres produce `skip>0` (e.g. `backend:test`, `backend:diff-cover`, `backend:migrations` all SKIP when `DATABASE_URL` is unset — lines 138, 143, 164 of `gates.sh`). The proposal says "or each SKIP justified" — but the validator cannot evaluate justification quality. Does it accept a comment like `"backend:test SKIP — no Postgres"`? If yes, the forgery surface widens (an agent can write a plausible justification). If no (reject all SKIPs), the gate blocks every ticket QA'd in a no-Postgres environment, which is most local runs.
- **Impact:** Either the validator is too strict (blocks legitimate work by developers who can't run Postgres locally) or too lenient (accepts any justification text, making the requirement nearly as forgeable as before).
- **Suggested mitigation:** Drop the `skip=0` / "justified" aspect from P1's validator. Instead, *require* the GATES_JSON to be present, and have the validator emit a *warning* (not a block) when `fail>0` or `skip>0`. Let the CI run (which re-evaluates the same gates with `GATES_REQUIRE_ALL=1`) be the real authority. This lowers false-positive risk while still requiring the author to paste *something* machine-readable.
- **Open question for author:** How does the validator distinguish a justified SKIP from an unjustified one without re-running gates? If it cannot, should SKIP just be a WARN, not a block?

#### [INFO] P1.3 — GATES_JSON format coupling

- **Assumption:** The GATES_JSON line format is stable and can be parsed reliably by the Python validator.
- **Risk:** The format is currently `{"pass":N,"fail":N,"skip":N,"results":[...]}` on line 321 of `gates.sh`. Nothing enforces this schema — a future change to the JSON structure (e.g. adding `"total":N`, reordering keys, changing key names) would silently break the validator without any compilation or test feedback unless the rule-fires test explicitly monitors it.
- **Impact:** Silent breakage. The validator may start rejecting every QA report because the format regex no longer matches, or worse, accept a malformed line because the regex is too permissive.
- **Suggested mitigation:** (a) Add a unit test that runs `gates.sh` in a mode that produces output and asserts the GATES_JSON format matches what the validator expects; (b) make the parser lenient — extract `"fail":(\d+)` and `"skip":(\d+)` via regex on the raw JSON, not by re-parsing the whole object, so field reordering is resilient.
- **Open question for author:** What is the coupling test between the validator's parser and gates.sh's output format? The rule-fires test for P1 seeds a bad `.qa.md` — does it also test that a *valid* `.qa.md` produced by gates.sh actually passes?

---

### P2 — Codify loop discipline + ban pipe-masked gate exits

#### [WARN] P2.1 — Purely documentary; the entire problem class recurs as soon as the agent ignores the CLAUDE.md rule

- **Assumption:** Adding text to CLAUDE.md will change agent behavior when the root problem was that agents already ignored undocumented expectations.
- **Risk:** The problem being fixed is that an agent declared Dev Complete on a gate subset, trusted a subagent's self-report, and deferred to CI. Every single one of these is now forbidden by the proposed CLAUDE.md rule. But the agent was not following the *previously implicit* rule either. Adding an explicit rule without enforcement raises the bar from 0% compliance to "depends on the agent reading and obeying the right section." That is an improvement, but it is the weakest possible intervention — entirely reliant on model adherence.
- **Impact:** The pipe-masking problem is the one part that could be mechanically prevented, but it's left as documentation. A shell script wrapper (`scripts/ci/gate-runner.sh` that captures exit code and writes the capture to a log) would make the documented practice the *only* way to invoke gates and provide a deterministic GATES_JSON capture at Dev Complete time (bridging to P1). The documentation-only choice leaves the pipe mask replicable by any agent that doesn't read this line.
- **Suggested mitigation:** Ship a small shell helper — `scripts/ci/gate-capture.sh <scope>` that runs `gates.sh <scope>`, captures exit code, writes stdout+stderr to a deterministic log path (e.g. `.agent/reports/.gates-capture-<scope>.log`), and prints the exit code. Then document that agents MUST use this wrapper. The wrapper itself can't be piped to mask the exit (it writes, it doesn't pipe). This makes the documentation enforceable in code review (CI can check that the capture log exists and is up to date).
- **Open question for author:** Why leave the pipe-masking fix as documentation-only when a 15-line shell wrapper would make it structurally impossible? If the answer is "T1 tier limits scope," consider whether this one line-item deserves a brief T2 follow-up.

#### [INFO] P2.2 — "Never declare green on a gate subset" conflicts with real development workflow

- **Assumption:** Agents should always run the full gate set before Dev Complete.
- **Risk:** During iterative development, running `gates.sh backend --changed-only` (fast subset, no services, no slow gates) is the correct local workflow — it is explicitly designed for this purpose (line 15: "fast local subset (no DB, no slow)"). The proposed rule as stated ("never declare green on a gate subset") would forbid this, forcing developers to either skip local validation entirely (because full gates take too long) or run the full suite on every iteration. The former creates a worse outcome (no validation); the latter forces a workflow change with no security benefit because Dev Complete is not a deploy gate.
- **Impact:** The rule, if taken literally, discourages the fast-feedback loop that `--changed-only` was designed for. Agents may skip gates entirely rather than run the full suite 20 times a day.
- **Suggested mitigation:** Be precise: "the **Dev Complete declaration** must be based on the full gate set, not a subset. During development, `--changed-only` is fine for iteration, but the final Dev Complete gate run must be full (`--changed-only` gates re-run without the flag, or identity their specific impact on the full result)."

---

### P3 — Same-session authorship REQUIRES external QA mode

#### [BLOCKER] P3.1 — "Authored in the same session" is not detectable by a static ticket validator

- **Assumption:** `validate_ticket` can determine, from the ticket file and QA report, whether the implementation was authored in the same LLM session that produced the QA.
- **Risk:** There is no metadata in any file that records "which session authored this." The ticket file is markdown; the QA report is markdown. Neither carries a session ID, agent identity, or authorship timestamp that the validator could compare. The validator operates on static file content only. Even if the QA report declares `mode: external`, the validator cannot verify that the mode declaration is truthful — the same agent that wrote the implementation also writes the QA report. The `mode` field is self-attested and unverifiable.
- **Impact:** The proposal cannot be implemented as described. The validator either:
  - (a) Rejects all tickets whose QA report lacks `mode: external` → this blocks every ticket, including the intended ones, because every QA report would now need to claim `external` mode.
  - (b) Requires the `mode` field to be present but does not cross-check it → the agent always writes `mode: external`, making the requirement meaningless.
  - (c) Attempts to infer "same session" from commit metadata (files authored by the same committer and QA'd in the same commit range) → fragile, trivially bypassed by splitting commits, and introduces false positives for legitimate single-developer workflows.
- **Suggested mitigation:** Change the requirement from *detect-and-enforce* to *default-to-external*. Instead of `validate_ticket` checking `mode`, have the QA agent *always* use external mode by default when it was the implementation agent. This is a process change in the SKILL.md, not a validator change. The validator should check that the `.qa.md` declares an *attested `mode` field*, and if the mode is `self` (same-session), it must be accompanied by an author-conducted adversarial self-review transcript (the agent cannot just claim self-mode and skip the work). This makes evasion costly rather than blocking on an undetectable property.
- **Open question for author:** What exact string or metadata in the `.qa.md` (produced by the same agent) could the validator trust to distinguish same-session from cross-session QA? If the answer is "nothing in-band," then the validator enforcement in the proposal is not implementable. Would you accept a weaker form — e.g., the SKILL.md mandates external mode for same-session, the `.qa.md` must state its mode, and the human reviewer polices mode truthfulness during walk-through?

#### [WARN] P3.2 — P3's `validate_ticket` integration requires P1 to exist first

- **Assumption:** P3 can be implemented independently of P1.
- **Risk:** P3 says "record the QA `mode` in the `.qa.md` evidence block (P1) and have `validate_ticket` reject..." This explicitly depends on the P1 GATES_JSON mechanism. If P1 is deferred or modified, P3's validator hook has no implementation path. Conversely, if P1 is implemented without the `mode` field in its evidence block, P3 must either modify P1's schema or add a separate evidence block.
- **Impact:** P3 is not independently evaluable — it is a dependent add-on to P1. If P1 is not implemented, P3 cannot be implemented as proposed.
- **Suggested mitigation:** Either (a) specify P3 as a modification to P1's "evidence block" definition (make `mode` part of the same required field set), or (b) decouple P3 so it requires a `mode` line in the `.qa.md` independent of P1's GATES_JSON line. The proposal currently reads as (a) but does not say so explicitly.
- **Open question for author:** Is P3 gated on P1's implementation, or can it ship independently by requiring a `mode:` YAML front-matter field in `.qa.md` files regardless of P1?

---

## Missing evidence

1. **Evidence of the claimed problem's frequency.** The packet says "an AI agent declared Dev Complete without running the full local QA gate set." Was this one incident, or is this a recurring pattern? The cost-benefit of these interventions depends heavily on frequency. A one-off incident might warrant P2 (documentation) but not P1+P3 (engineering investment plus false-positive risk across all tickets).

2. **The Dev Complete transition's gate gap.** The current `can_transition(STATUS_DEV_COMPLETE)` (schema.py lines 147-151) checks only: (a) `.dev-summary.md` exists and is not a scaffold, (b) the ticket has acceptance criteria. It does NOT check any gate output at all. P2's documentation-only approach leaves this gap open. None of the three proposals close the Dev Complete hole (P1 closes Review, P3 closes QA, P2 only documents). Is this intentional?

3. **Cost of false positives.** P1's `skip=0` requirement on the validator could block a significant fraction of local runs (anyone without Postgres). Are there metrics on how many local QA runs happen without Postgres? Is the intention to force all developers to run Postgres locally, or to accept the false-positive/forgeability tradeoff?

4. **External QA availability.** P3 depends on `scripts/qa/run_external_qa.sh` working with the available tool (opencode/codex/cursor). If the tool is not available (documented as a known failure mode in `external-qa.md` lines 25-31 — OpenCode hang-at-init, Codex quota errors, Cursor availability), then mandating external QA creates a hard block with no fallback. What is the fallback when the external QA toolchain is unavailable?

5. **Wave mode interaction.** The SKILL.md describes a "wave" mode where multiple tickets are QA'd together by one external run. If P3 requires `mode: external` per-ticket, does a wave-run QA report (one external pass covering AE-0072, AE-0073, AE-0074) satisfy P3 for each ticket? The `validate_ticket` checker runs per-file — would a wave report need to be replicated into each ticket's `.qa.md`, or would the validator accept a pointer-file?

---

## Residual risks if plan proceeds unchanged

1. **P1's forged GATES_JSON is still undetectable at Review-transition time.** A determined agent can paste a fabricated JSON line into the `.qa.md`. The CI backstop catches it later, but the ticket reaches Review — the gate's moment of enforcement — with a passing grade. The "raise the bar" claim is weak: the forgery cost increased from 4 words ("all green") to ~200 bytes of plausible JSON, but zero structural resistance is added.

2. **P3 is unenforceable in the validator.** It will either be implemented as a no-op (validator always accepts the mode claim) or as a source of false positives (blocking legitimate tickets whose mode field is omitted through oversight). The root goal (bias-free QA) is addressed only if the agent voluntarily runs external QA — the validator cannot force it.

3. **The Dev Complete → Review gap persists.** None of the three proposals add a gate check at Dev Complete time. An agent can still reach Dev Complete without running gates. P2 documents that they should not, but provides no mechanism. P1 checks only at Review (one transition later), and P3 checks the QA mode. The Dev Complete declaration itself remains a pure self-attestation.

4. **Documentation burden without enforcement (P2) is reversible by the same class of mistake.** The root problem was an agent not following undocumented rules. P2 documents the rules. Nothing prevents the exact same failure mode (agent ignores the rule, trusts a subagent's summary, pipe-masks the exit). The pipe-masking fix in particular is trivially avoidable — it is a `$?` capture pattern, not a structural change. If this is the only fix in the packet for a specific observed incident, a recurrence is likely.

5. **False-positive risk from `skip=0` in P1 could disincentivize the honest behavior the packet wants to encourage.** A developer who honestly runs gates locally but has no Postgres gets a `skip>0` verdict, writes a justification, and hits a validator rejection (if strictly enforced). The incentive is to either lie about skips (write `skip:0` anyway) or skip QA entirely and let CI catch it. Neither is better than the status quo.
