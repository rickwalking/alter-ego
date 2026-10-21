# AE-0442 — Langfuse captures traces on prod but they show no logs (input/output/names)

Status: Dev Complete
Tier: T1
Priority: High
Type: Bug
Area: Backend
Owner: Worker (AE-0442)
Branch: feat/ae-0442-langfuse-trace-io
PR: #167 https://github.com/rickwalking/alter-ego/pull/167
Kanban Card: TBD
Created: 2026-10-20
Updated: 2026-10-20

## Goal

Every Langfuse trace/observation records a meaningful input, output and name: a
phase trace carries the phase brief as input and the result/error as output,
generations are named after the agent + phase (not "ChatOpenAI"), review events
live in a named trace, and short-lived background phases flush what they record.

## Problem

Prod evidence (ClickHouse, read 2026-10-20 23:25Z; project
`cmpxc9w100006qo07rh9geeui`), last 24 h: 128 traces, 222 GENERATION, 176 SPAN,
18 EVENT. Every trace had empty input AND output (0/128); every SPAN and EVENT
had empty input/output (0/176, 0/18). Only GENERATIONs carried input/output and
every generation was named `ChatOpenAI` (or `OpenCodeSidecarChatModel`). 18
traces had an empty name. The Langfuse list rows therefore showed no input, no
output and no useful names: "capturing traces but no logs".

### Root causes (file:line on `origin/main`, f935db43)

- `backend/src/rag_backend/infrastructure/langfuse_phase_trace.py:114-134`:
  `phase_trace` opens the root span and calls `update_trace` with name/user/
  metadata/tags only. In Langfuse v3 the trace-level input/output comes from the
  root observation; neither the span nor the trace ever receives `input`/`output`,
  so every trace and every phase span is empty (0/128, 0/176).
- `backend/src/rag_backend/infrastructure/monitoring_langfuse.py:237-242`:
  `get_langfuse_runnable_config` returns only `callbacks`; no `run_name`. The
  Langfuse LangChain callback names a generation from the LangChain run name,
  which falls back to the serialized model class (`ChatOpenAI` /
  `OpenCodeSidecarChatModel`). 404/404 generations are uninformative.
- `backend/src/rag_backend/infrastructure/monitoring_langfuse.py:260-284`:
  `create_workflow_trace` uses `client.start_span`, never ends or flushes it.
  `record_human_review` (`:344-364`) calls `create_event` on that unexported
  span: the parent observation is never ingested, so the event becomes a root of
  a new, unnamed trace with no I/O. That is the source of the 18 empty-name
  traces (each one an orphan `human_review_review_completed` EVENT).
- Nested helpers double-open spans and clobber metadata:
  `blog_image_batch._one` opens `workflow_blog_section_image` with the real
  project/user, then `BlogImageService.generate` calls `blog_ai_propagate` which
  opens a second `workflow_blog_section_image` span with only `post_id`. The
  inner `update_trace` overwrites the trace metadata with
  `project_id=unknown`, `user_id=unknown`, `agent_name=editorial_workflow`.
  Prod trace `44ce9045...` shows exactly that pair.

Config is not the cause: deploy.yml already supplies `LANGFUSE_SECRET_KEY` /
`LANGFUSE_PUBLIC_KEY`, the SDK samples everything by default, and generations
are ingested (so the export pipeline works). The gap is what the code records.

## Scope

- `phase_trace` records:
  - trace input: project id, content type, agent, phase, plus the caller's
    brief (topic, attempt, model queue, counts — no raw prompts/secrets);
  - trace output: the caller's result summary, or a redacted error summary when
    the phase raises (then re-raise);
  - the same input/output on the root span, `session_id` = project id, tags
    unchanged, and a flush at the phase boundary.
- `get_langfuse_runnable_config` derives a `run_name` from the active phase
  (`<content_type>.<phase>`) plus an optional detail such as `slide 3`, so
  generations are named `carousel.content slide 3`, `blog_post.blog_generation
  draft`, never `ChatOpenAI`.
- `create_workflow_trace` opens and ends a real named span with trace
  attributes and input/output; when a phase trace is already active it reuses
  that span instead of opening a nested one or clobbering its metadata.
- `record_human_review` creates the review event inside a named `workflow_review`
  trace with input/output; no orphan EVENT traces.
- Nested `propagate_attributes`/`blog_ai_propagate` inherit the enclosing
  phase's project/user/agent and merge metadata instead of resetting it.
- In-process background runners flush Langfuse when they finish (phase traces
  already flush; the runner end is the belt-and-braces boundary).
- Redaction: every string captured for input/output/metadata goes through the
  existing `redact_secrets` rules.
- Tests: fake Langfuse client asserting input/output/name/metadata for a phase
  trace, a blog generation trace and a generation; error output; no secrets.

## Non-Goals

- No new Langfuse deployment/config; no sampling change.
- No change to LLM prompts, model routing or workflow behavior.
- No writes to production (verification is a read-only ClickHouse query).
- Do not touch the blog document-model tickets' files.

## Acceptance Criteria

- [x] AC1: a phase trace records an input summary (project id, phase, topic,
  attempt, model queue) and an output summary on BOTH the trace and root span.
- [x] AC2: a phase that raises records `status=error`, error type/message
  (redacted) as output, then re-raises.
- [x] AC3: generations carry a descriptive `run_name` (`<content_type>.<phase>`
  + detail, e.g. `carousel.content slide 3`), not the model class name.
- [x] AC4: no trace is unnamed; human review events live in `workflow_review`
  with input/output.
- [x] AC5: nested tracing helpers reuse the outer phase span and never replace
  its project/user/agent metadata with `unknown`.
- [x] AC6: a blog generation phase records the writer brief as input and the
  article/quality summary as output.
- [x] AC7: phase boundaries and background-runner completion flush Langfuse.
- [x] AC8: captured payloads contain no Telegram/Graph secrets.
- [x] AC9: local backend gates green (mutation/full suite delegated to CI per the orchestrator memory directive); CI result tracked on the PR.

## Gherkin Scenarios

`backend/tests/features/langfuse_trace_io_ae0442.feature`

## Repro Steps

1. Read prod ClickHouse: `default.traces`/`default.observations` for the last
   24 h — trace input/output lengths are 0, generations are all `ChatOpenAI`.
2. Run a carousel phase or blog generation in a local fake-client test before
   the fix: the fake collector sees `update_trace(name/user/metadata/tags)` but
   no `input`/`output`, and the run config has no `run_name`.
3. Resume a workflow: the review EVENT's parent observation is never exported,
   yielding an unnamed trace.

## Affected Areas

- [x] Backend
- [ ] Frontend
- [x] Tests

## Dependencies

None.

## Progress Log

### 2026-10-20

Ticket created from the orchestrator brief and prod evidence. Root causes
confirmed in code + ClickHouse: no trace/span I/O, no generation run_name,
unended `create_workflow_trace` spans/events, nested span metadata clobbering.
Gherkin written first; tests then code.

Implemented in `bd334f3b`..`5bd59c53`; PR #167 opened with base `main`.

- `phase_trace` now takes `trace_input`, writes sanitized input/output to both
  the root span and the trace, defaults success output to
  `{"status": "completed"}`, records a redacted `status=error` output (and
  span `level=ERROR`) before re-raising, sets `session_id`, keeps tags, and
  flushes at the phase boundary.
- `get_langfuse_runnable_config` sets `run_name` from the active phase
  (`<content_type>.<phase>`) plus an optional detail; `generation_run_name`
  contexts name units such as `slide 3`.
- `create_workflow_trace` opens a named span and ends it with I/O; when a phase
  span is active it reuses it, so nested `blog_ai_propagate` calls no longer
  clobber project/user/agent metadata.
- `record_human_review` opens a `workflow_review` phase trace and creates the
  review event inside it; the 18 orphan unnamed EVENT traces disappear.
- Blog writer/image phases record the brief (post/slot/section) as input and
  the article/voice/image summary as output.
- Background blog/resume runners flush at run end through application-layer
  wrappers (`flush_workflow_traces`), keeping the DDD import boundary intact.
- Redaction reuses `redact_secrets`; captured values are bounded to 2000 chars.

Decisions/deviations:

- The Langfuse `input` keyword is only used at SDK call sites; our helpers use
  `trace_input` to satisfy ruff A002 without suppressions. The `TraceSpan`
  protocol accepts `**kwargs` to mirror the SDK without `noqa` suppressions.
- The runner flush deliberately does not lazily create a Langfuse client. A
  shutdown path must not open a network connection; if no client exists there
  is nothing buffered to flush.
- Full backend suite/mutation were not run locally (shared-machine memory
  directive); CI is the source of truth. Targeted files were run individually.

## Files Touched

- `.agent/tasks/AE-0442-langfuse-traces-show-no-input-output-or-useful-names.md`
- `backend/tests/features/langfuse_trace_io_ae0442.feature`
- `backend/tests/langfuse_trace_fakes.py`
- `backend/tests/unit/infrastructure/test_langfuse_trace_io_ae0442.py`
- `backend/tests/unit/infrastructure/test_langfuse_phase_trace_ae0390.py`
- `backend/tests/unit/infrastructure/test_monitoring_langfuse.py`
- `backend/src/rag_backend/domain/constants/langfuse_tracing.py`
- `backend/src/rag_backend/infrastructure/langfuse_phase_trace.py`
- `backend/src/rag_backend/infrastructure/monitoring_langfuse.py`
- `backend/src/rag_backend/infrastructure/langfuse_client.py`
- `backend/src/rag_backend/agents/carousel_workflow_nodes.py`
- `backend/src/rag_backend/agents/llm_json_retry.py`
- `backend/src/rag_backend/agents/content_draft_agent.py`
- `backend/src/rag_backend/agents/blog_writer/agent.py`
- `backend/src/rag_backend/application/services/blog/blog_generation_service.py`
- `backend/src/rag_backend/application/services/blog/blog_image_batch.py`
- `backend/src/rag_backend/application/services/blog_workflow_observability.py`
- `backend/src/rag_backend/application/services/carousel/editorial_workflow_service.py`
- `backend/src/rag_backend/application/services/blog/blog_generation_runner.py`
- `backend/src/rag_backend/application/services/carousel/editorial_workflow_resume_runner.py`

## Test Evidence

Targeted tests (run individually; all green):

- `tests/unit/infrastructure/test_langfuse_trace_io_ae0442.py` — 14 passed
  (trace/span brief+result, error output, redaction, no-client, blog brief,
  run names, review trace, nested span reuse, background flush).
- `tests/unit/infrastructure/test_langfuse_phase_trace_ae0390.py` — 11 passed.
- `tests/unit/infrastructure/test_monitoring_langfuse.py` — 15 passed.
- `tests/unit/application/test_editorial_workflow_service.py` — 45 passed.
- `tests/unit/application/test_blog_generation_service_ae0425.py` — 18 passed.
- `tests/unit/application/test_blog_image_batch_ae0425.py` +
  `test_blog_stage_budget_ae0435.py` — 17 passed.
- `tests/unit/application/test_editorial_workflow_resume_runner.py` +
  `test_phase_sync_release_ae0390.py` — 29 passed.
- `tests/unit/agents/test_content_draft_agent.py` +
  `test_blog_writer_agent_ae0425.py` + `test_phase_trace_nodes_ae0390.py` —
  27 passed.

Static gates (each run via `bash scripts/ci/gates.sh`):

- `backend:format` PASS
- `backend:lint` PASS
- `backend:type` PASS (998 files)
- `backend:strict-diff` PASS (15 changed source files)
- `backend:imports` PASS (27 contracts)
- `backend:arch-ratchet` PASS
- `backend:docstrings` PASS
- `backend:dead-code` PASS
- `backend:inline-prompts` PASS
- `backend:bandit` PASS (advisory findings only)
- `backend:integrity` PASS (0 net-new gaming)

Deferred to CI (shared-machine memory directive): full backend test suite,
diff-cover, migrations, schema-drift, mutation. Gherkin:
`backend/tests/features/langfuse_trace_io_ae0442.feature`.

## QA Report

Pending.

## Blockers

None.
