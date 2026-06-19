# Kaizen Report — qa-loop-2026-06-19
Mode: incident | Generated: 2026-06-19 | Signal window: this session (agent-harness wave AE-0248/0249 + #58)

## Trigger
The operator caught the dev loop declaring tickets Dev Complete **without running the full
QA gate set** — leaning on a gate subset, a delegated subagent's self-reported "all green",
and CI as the backstop ("this is gaming, you are skipping it on the dev loop. The loop should
always run all QA gates"). A memory note was written, but a memory is a *soft* control. Kaizen's
job: make the class **structurally** hard to repeat (ratchet UP), not rely on the agent
remembering.

## Failure Classes (ranked)
| # | Class | Freq (this session) | Severity | Gate that should catch it | Status |
|---|-------|---------------------|----------|---------------------------|--------|
| 1 | Ticket reached Dev Complete / moved toward Review on a **gate subset or a prose "all green"** — full `gates.sh` (19 gates) not run | 2 (AE-0248, AE-0249) | High | ticket-hygiene `.qa.md` gate — but it only checks non-emptiness + id-attribution (AE-0181), not gate proof | **propose UP** |
| 2 | A delegated **subagent's self-reported gate result was false** — claimed "check-integrity 0 blockers" while a net-new `# type: ignore` was present (caught only by my own re-run) | 1 | High | orchestrator independent re-run — not required anywhere | **propose UP via P1+P3** |
| 3 | `gates.sh ... \| tail` reported the **pipe's exit 0**, masking a real test FAIL (#58 misread as green) | 1 | Med | none — pipe masks gate exit | **propose HOLD (doc)** |
| 4 | External (bias-free) QA was run **only after the human demanded it**; same-session/subagent code is self-reviewed by default | 1 | Med | qa-agent external mode — *listed* for this case, not *required* | **propose UP** |

## Proposals (for approval)

### P1 — Require machine-readable gate proof in the QA report before Review  [ratchet: UP] — T2
- **Failure class / root cause (1, 2):** `scripts/agent_tasks/schema.py::_qa_report_errors`
  (AE-0181) gates the `Review` transition on a `.qa.md` that is merely non-empty and
  attributed to the ticket id. It never checks whether the **full gate set actually passed** —
  so a hand-written "all green" (or a subagent's unverified claim) satisfies the gate. "QA was
  run" is unverifiable today.
- **Enforcement (UP):** require the `.qa.md` to embed the `gates.sh` **`GATES_JSON:`** verdict
  line (which `gates.sh:321` already prints) showing `"fail":0` AND `"skip":0` (or each SKIP
  explicitly justified), pinned to the reviewed commit SHA. A report with no `GATES_JSON` block,
  or `fail>0`, **fails `validate_ticket`** → the ticket cannot reach Review. Free-text QA claims
  no longer pass.
- **Exact files:** `scripts/agent_tasks/schema.py` (`_qa_report_errors`), `constants.py`
  (the marker/regex), **rule-fires test (AE-0180)** seeding a `.qa.md` with no `GATES_JSON` and
  one with `fail>0` → validator exits non-zero; `docs/guides/qa-checkpoints.md`.
- **Known limitation (for the skeptic):** the `GATES_JSON` is self-pasted, hence forgeable.
  Mitigated by CI re-running every gate (a forged PASS surfaces as CI red) + SHA pinning. Still
  UP: mechanical proof + friction beats a prose claim, and it forces the agent to have actually
  run `gates.sh` to obtain the line.
- **Eliminates:** class 1 directly; class 2 (a subagent's prose claim without the GATES_JSON proof can't pass).

### P2 — Codify the loop discipline + ban pipe-masked gate exits  [ratchet: HOLD] — T1
- **Failure class / root cause (3 + the written-rule gap):** the "run ALL gates" expectation
  lived only in my memory, not a project rule; and `bash gates.sh <scope> | tail` returns the
  pipe's exit (tail = 0), masking a non-zero gate — which made #58 read as green when 3 tests
  failed.
- **Enforcement (HOLD — codify existing best practice, loosens nothing):** a `CLAUDE.md` rule
  (Testing/Git section): the delivery loop runs the **full** `gates.sh <scope>` +
  `check-integrity.sh` + `/qa-agent` before Dev Complete; never declare green on a gate subset,
  a delegated agent's self-report, or by deferring to CI; **capture the gate exit to a file
  (`bash gates.sh <scope> >log; echo $?`) — never pipe a gate to `tail`/`head`** (the pipe's
  exit masks the gate's). Mirror note in `docs/guides/qa-checkpoints.md`.
- **Exact files:** `CLAUDE.md`, `docs/guides/qa-checkpoints.md`.

### P3 — Same-session authorship REQUIRES external `/qa-agent`  [ratchet: UP] — T1
- **Failure class / root cause (4):** the qa-agent skill **lists** external mode "when the
  implementation was authored in the same session" (SKILL.md:104) but does not **require** it,
  so bias-free QA depended on the human asking. Same-session/subagent-authored code is otherwise
  self-reviewed.
- **Enforcement (UP):** change `qa-agent` SKILL.md + `config.yaml` so external mode is
  **required** (not discretionary) whenever the implementation was authored in the same
  session/by a subagent; record the QA `mode` in the `.qa.md` evidence block (P1) and have
  `validate_ticket` reject a same-session ticket whose report shows `mode != external`.
- **Exact files:** `skills/delivery/qa-agent/SKILL.md`, `config.yaml`; `scripts/agent_tasks/schema.py` (mode check, ties into P1).
- **Mirrors** AE-0257 (made external-skeptical required for T3 plans + an existence gate) — same pattern, applied to QA.

## Rejected (would loosen the bar)
- (none proposed)

## Tickets created
- (awaiting approval)

## Phase 3.6 — External cold-critic — Verdict: WARN (all findings accepted, proposals revised)
Review: `.agent/reports/kaizen-qa-loop-2026-06-19.skeptical-review.md`. Verified each finding
against live code. Key revisions: P1 reframed as an observability/friction ratchet (skip>0→warn,
also gates Dev Complete via the dev-summary, lenient parser, wave-reference); P2 upgraded from
doc-only to a real `gate-capture.sh` wrapper (+ --changed-only precision); P3 dropped the
unenforceable "validator detects same-session" → SKILL.md default-to-external + a declared `mode`
field + tool-outage fallback. Full resolutions in each ticket's Decision Log.

## Tickets created
- AE-0258 (T2) — require machine-readable gate proof (GATES_JSON) in dev-summary + qa report
- AE-0259 (T1) — ship gate-capture wrapper + codify full-gate loop discipline (no pipe-masked exits)
- AE-0260 (T1) — require external QA by default for agent-authored work + declared mode field
