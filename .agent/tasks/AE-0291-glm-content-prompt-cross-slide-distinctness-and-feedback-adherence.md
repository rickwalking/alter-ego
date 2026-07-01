# AE-0291 — GLM content prompt: cross-slide distinctness + rework-feedback adherence

Status: Dev Complete
Tier: T2
Priority: P1
Type: Enhancement
Area: backend
Owner: Unassigned
Agent Lane: architect → developer → qa → release
Branch: feat/ae-0291-glm-content-distinctness-feedback
Created: 2026-07-01
Updated: 2026-07-01

## Goal

Improve GLM 5.2 carousel content generation on the v3 editorial path so that
(1) slide bodies are distinct across the carousel (no near-duplicate copy) and
(2) content-phase rework/send-back feedback is reliably applied on regeneration.

## Scope

- `agents/prompts/carousel/v3/` (new version folder), `content_draft_agent.py`,
  `editorial_workflow_generators.py`, `phase_artifact_runner.py`,
  `instruction_context_loader.py`, the content skill/`_shared` standards, + tests.
- v3 editorial path only.

## Non-Goals

- No change to the v2 legacy whole-carousel path.
- No live-model quality assertions in CI (diversity/adherence proven by an
  offline eval, not a gate).
- B3 per-slide feedback targeting is deferred to a follow-up if it requires a
  `structured_feedback` schema change (ship B1+B2 first).
- No editing of the existing v3 prompt in place (version-folder bump instead).

## Problem

Two GLM 5.2 carousel-content quality defects, both rooted in the **v3 editorial**
content path (the current/primary one — `ContentDraftAgent.draft_slide` →
`prompts/carousel/v3/content.yaml`):

**(1) Repetitive slide bodies.** The v3 path drafts each slide in complete
isolation — one LLM call per slide, and the prompt only ever sees ONE slide's
`title` + `key_points` (`content.yaml:10-12`). It has zero awareness of what the
other slides say, so GLM produces near-identical body copy across slides.
No prompt in the chain (`content.yaml`, `skills/carousel-pipeline/phases/content/SKILL.md`,
`_shared/*`) contains a **cross-slide distinctness** rule — the only related rule
is intra-slide `body_must_not_repeat_heading`
(`_shared/contracts/hero_lower_third_v1.yaml:51`).

**(2) Rework feedback not reliably followed.** On a content send-back the reviewer
notes *are* wired into regeneration
(`phase_artifact_runner.py:387` → `editorial_workflow_generators.py:73-90` →
`content_draft_agent.py:80-81` → `content.yaml:25` `{{ revision_notes }}` +
`instruction_context_loader.py:98-99`). But adherence is weak because:
- Feedback is **global** — the same `revision_notes`/`persona_context` string is
  passed identically to every slide, with no per-slide targeting
  (`editorial_workflow_generators.py:92-103` loop).
- It is rendered under **soft headings** ("Apply these reviewer notes",
  "## Reviewer revision notes") with no imperative "you are regenerating; the
  previous draft was rejected; you MUST change X" framing.
- The model **never sees its previously-rejected draft**, so it has nothing to
  diff against and tends to reproduce the same copy.

Context gotchas found during investigation:
- **YAML `model:` blocks are inert on the v3 path.** `render_prompt` returns
  `(prompt_text, model_cfg)` but `content_draft_agent.py:68` discards the config
  (`prompt_text, _ = ...`) and `ainvoke` passes no temperature/max_tokens. Effective
  knobs come from `infrastructure/external/chat_model_factory.py` (`_TEMPERATURE=0.7`,
  `_MAX_TOKENS=32000`). So editing `content.yaml`'s temperature will do nothing
  unless we also wire `model_cfg` through.
- `instruction_context_loader.py` hard-truncates the instruction blob at
  `INSTRUCTION_CONTEXT_MAX_CHARS = 12000` (revision notes are added early, so
  currently safe — but adding sibling-slide context must respect this budget).
- Response cache keys on `full_prompt` (`content_draft_agent.py:86-92`) — changed
  feedback busts it correctly; identical feedback + identical inputs returns the
  cached (unchanged) draft.

## Proposed Design

**A. Cross-slide distinctness (goal 1)**
1. Add a `sibling_context` variable to `content.yaml`: for slide N, inject the
   other slides' headings + key_points with an explicit instruction: *"These are
   the OTHER slides in this carousel. Your slide MUST cover a distinct angle — do
   not repeat their framing, examples, or sentences."* Thread it through
   `draft_slide` / `generate_slide_drafts`.
   - **DECISION (external QA #1 — was left "either/or"): use the CHEAP up-front
     option** — feed all slides' headings + key_points before the per-slide loop,
     so each slide sees the full outline. Chosen over the sequential
     (prior-bodies) variant because sequential grows the prompt O(N²) over the
     loop, makes response-cache hits order-dependent, and forces restructuring the
     `editorial_workflow_generators.py:92-103` loop to accumulate bodies. The
     up-front outline keeps the loop order-independent and cache-friendly and is
     enough to break the "each slide blind to the others" root cause. Revisit
     sequential only if the cheap option proves insufficient.
   - **Placement (external QA #5):** `sibling_context` must be added to the
     instruction context BEFORE `SECTION_PHASE_SKILL`/`SECTION_SHARED` and after
     `SECTION_REVISION`, so `_bound_instruction`'s tail-truncation
     (`instruction_context_loader.py:131-135`, 12000-char cap) drops shared
     boilerplate first, never the notes or sibling outline. Specify the ordering
     explicitly in the loader.
2. Add an explicit cross-slide distinctness rule to
   `skills/carousel-pipeline/phases/content/SKILL.md` writing rules and/or
   `_shared/content-contracts.md`.
3. Post-generation distinctness check (cosine/Jaccard on bodies) that forces a
   re-draft of the offending slide. **Bounded (external QA #7): at most 1 re-draft
   attempt per slide; on second failure keep the best draft and log a WARN** — no
   unbounded loop, no cost balloon.

**B. Rework-feedback adherence (goal 2)**
1. Reframe the revision notes imperatively and hoist to the TOP of the slide
   instruction: *"⚠️ REGENERATION: your previous draft for this slide was REJECTED.
   You MUST apply every reviewer note below and change the copy accordingly. Do not
   return the previous text."*
   - **Dedupe the two render sites (external QA #3):** revision notes currently
     render TWICE — `instruction_context_loader.py:98-99` (`SECTION_REVISION`) AND
     `content.yaml:25` (`{{ revision_notes }}`). Pick ONE authoritative site for
     the imperative block and make the other a no-op (or remove it), so the model
     never sees the imperative header next to a soft "## Reviewer revision notes"
     duplicate. Recommended: keep it in the instruction loader (rendered first,
     truncation-safe) and drop the soft `content.yaml` copy.
2. Pass the **previous rejected draft** for the slide into the prompt so the model
   can diff against it (persist per-slide prior draft; render as
   `{{ previous_draft }}` with "change this"). This ALSO fixes an **independent
   adherence blocker**: the response cache keys on `full_prompt`
   (`content_draft_agent.py:86-92`), so a re-prompt with identical notes + inputs
   returns the *cached rejected draft*. Injecting `previous_draft` (which differs
   per cycle) busts the cache correctly. Note this dependency explicitly.
3. Where feedback is per-slide addressable, target it to the relevant slide rather
   than broadcasting one global string to all slides.
   - **Scope flag (external QA #4):** `SlideDraftGenerationParams.revision_notes`
     is currently `list[str]` (global). Per-slide targeting requires a
     `structured_feedback` schema change (per-slide notes) touching the API and
     likely the frontend. If that expands scope beyond T2, **split B3 into a
     follow-up ticket** and ship B1+B2 (global-but-imperative feedback) first.

**C. Make the model knobs real (enabler)**
- Wire `model_cfg` from `render_prompt` into the LLM call. **Mechanism (external
  QA #6): use `.bind(temperature=..., max_tokens=...)` to produce a per-call bound
  runnable** — `chat_model_factory.py` sets temperature at *construction*, so the
  fix is a per-call `.bind`, not an `ainvoke` kwarg. Assert the bound kwargs, not
  just that `ainvoke` was reached.

**Cross-cutting project-rule guards (external QA):** the imperative "you MUST
change this copy" reframe + injected sibling context can push GLM off-persona —
keep `PersonaAgent.enforce()` voice-match ≥70 (CLAUDE.md rule). Any new/extra LLM
calls must carry Langfuse metadata (`project_id`, `phase`, `agent_name`) per the
observability standard.

Scope note: keep changes on the **v3 editorial** path. The v2 legacy whole-carousel
prompt (`carousel/v2/content_prompt.yaml`) already has global visibility; leave it
unless we decide to converge paths. Prompt versioning rule: bump to a new version
folder rather than editing v3 in place if the contract changes materially.

## Acceptance Criteria

CI can only validate *plumbing* (that context reaches the prompt); the actual
diversity/adherence quality goals belong to an **offline eval**, not CI — canned
GLM responses would make a CI "distinctness" assertion circular (external QA #2).

- [x] **Plumbing:** the rendered slide prompt for slide N contains the OTHER
      slides' headings + key_points (sibling context) and the cross-slide
      distinctness instruction — deterministic string assertion, no live model.
- [x] **Plumbing:** on a content send-back the rendered prompt contains the
      substituted `previous_draft` and the imperative REGENERATION header,
      exactly once (dedupe verified — not duplicated across
      `instruction_context_loader` and `content.yaml`).
- [x] **Offline eval (not a CI gate):** `scripts/eval/carousel_distinctness_eval.py`
      reuses the runtime metric to report pairwise similarity + flagged slides over
      a real GLM `slide_drafts` JSON. (Run manually against a live carousel; not a
      gate.)
- [x] A cross-slide distinctness rule exists in the content skill
      (`phases/content/SKILL.md`); prompt change ships as new version folder `v4`
      (v3 untouched).
- [x] **`model_cfg` delivery:** the YAML `temperature`/`max_tokens` reach the LLM
      via a per-call `.bind(...)` — asserted on the bound kwargs, not merely that
      `ainvoke` was called.
- [x] **Truncation:** sibling context + revision notes survive the
      `INSTRUCTION_CONTEXT_MAX_CHARS` (12000) tail-truncation given the section
      ordering (notes + sibling context before shared boilerplate) — tested with an
      oversized shared-standards blob.
- [x] **Cache:** changed `previous_draft` busts the `full_prompt` cache; the
      re-draft is bounded to one attempt per slide (no unbounded loop).
- [x] Persona voice-match enforcement (`PersonaAgent.enforce()`) preserved after
      the imperative reframe; content LLM calls carry the Langfuse config.
- [x] `gates.sh backend` green + external QA.

## Test Evidence

`gate-capture.sh backend` → 15 PASS / 0 FAIL / 4 SKIP (test/diff-cover/migrations/
schema-drift SKIP locally — need Postgres; CI runs them). Integrity: 0 net-new
blockers. mypy strict: clean.

`GATES_JSON: {"pass":15,"fail":0,"skip":4,"results":[{"gate":"backend:format","status":"PASS"},{"gate":"backend:lint","status":"PASS"},{"gate":"backend:lint-diff","status":"PASS"},{"gate":"backend:blanket-ignore","status":"PASS"},{"gate":"backend:strict-diff","status":"PASS"},{"gate":"backend:type","status":"PASS"},{"gate":"backend:imports","status":"PASS"},{"gate":"backend:arch-ratchet","status":"PASS"},{"gate":"backend:docstrings","status":"PASS"},{"gate":"backend:dead-code","status":"PASS"},{"gate":"backend:inline-prompts","status":"PASS"},{"gate":"backend:bandit","status":"PASS"},{"gate":"backend:pip-audit","status":"PASS"},{"gate":"backend:integrity","status":"PASS"},{"gate":"backend:test","status":"SKIP"},{"gate":"backend:diff-cover","status":"SKIP"},{"gate":"backend:migrations","status":"SKIP"},{"gate":"backend:schema-drift","status":"SKIP"},{"gate":"backend:mutation","status":"PASS"}]}`

New/updated tests (all green): `test_content_distinctness.py` (8 — metric +
duplicate detection), `test_editorial_workflow_generators.py` (dedup, sibling
excludes self, previous-draft mapping, bounded re-draft keeps distinct),
`test_instruction_context_loader.py` (sibling section, imperative revision +
previous draft once, truncation ordering), `test_content_draft_agent.py` (.bind
kwargs, sibling+previous threaded once, cache-bust, Langfuse config). Full unit
suite: 2100 passed, 1 skipped.

## Gherkin / Tests

Behavior-changing → `.feature` required. Cover: (a) fresh generation → distinct
bodies; (b) send-back with a note → regenerated draft changes & honors the note;
(c) long feedback + sibling context → no truncation of notes; (d) temperature
override actually applied. Mock GLM (`build_chat_model`) — no live keys in CI
([[ci-no-external-api-keys]]).

## Files Touched (expected)

- `agents/prompts/carousel/v3/content.yaml` (or new version folder)
- `agents/content_draft_agent.py` (thread sibling context / previous draft / model_cfg)
- `application/services/carousel/editorial_workflow_generators.py` (build sibling context, per-slide feedback)
- `application/services/carousel/phase_artifact_runner.py` (previous-draft plumbing if added)
- `agents/skills/carousel-pipeline/phases/content/SKILL.md` + `_shared/content-contracts.md` (distinctness rule)
- tests + `.feature`

## Related

AE-0285 (GLM provider toggle), AE-0286 (deterministic copy trim). Prior GLM
overshoot/repeat context in memory: [[glm-5-2-backend-provider]].
Depends on / pairs with AE-0290 (send-back must actually reach content phase for
the feedback loop to be exercisable end-to-end).
