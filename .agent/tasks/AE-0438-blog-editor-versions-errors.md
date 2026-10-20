# AE-0438 — Blog editor: v1 = original AI draft (F-05), rewrite heading dup (F-08), surface errors (F-11)

Status: Dev Complete
Tier: T1
Priority: P1
Type: Bug
Area: Cross-cutting
Owner: Worker (orchestrator brief `~/alter-ego-qa/orch/ae0438-brief.md`, 2026-10-20)
Agent Lane: developer → qa → release
Branch: feat/ae-0438-blog-editor-versions-errors
Kanban Card: TBD
Created: 2026-10-20
Updated: 2026-10-20

## Goal

The blog editor keeps the original AI draft as version 1, a single-section voice
rewrite never duplicates the heading into the body, and every failed editor action
shows a visible, translated message (pt + en).

## Problem

QA on prod after `ba37f6f9` (2026-10-19/20 full run,
`~/alter-ego-qa/2026-10-19-qa-full/REPORT.md`, flow 04):

- **F-05 (major):** version 1 of a generated post is the empty bootstrap
  `{"schema":"blog.v2","sections":[],...}`; `POST /restore-version/1` 422s with no
  UI message, so the original AI draft is unrecoverable.
- **F-08 (minor):** "Reescrever esta seção na minha voz" stored
  `**Planilha vence torcida**\n\nMinha cadência...` — the section heading duplicated
  (bold) at the top of `body_md`; the public render would show it twice.
- **F-11 (minor):** restore-version 422 and submit-review 400 `self_review_not_allowed`
  are not surfaced at the point of action in the UI (the only alert is a generic
  kind-level message rendered far from the action).

## Root cause (file:line on `origin/main`, 4f811e6fd2)

- Every content write appends a snapshot of the state **before** the write
  (`api/dependencies/blog_content_write.py:107-117` → `OptimisticLockService.apply_versioned_update`
  → `application/services/blog/blog_version_history.py:61-81`). The generation's
  first write (the article) therefore snapshots the pre-write bootstrap, which
  becomes version 1 and is kept forever by `_bounded` ("the first entry is always
  kept"). Restoring it 422s because `validate_for_write` rejects zero sections
  (`blog_document_service.py:75-79`).
- `application/services/blog_post_ai_service.py:191-212` calls
  `PersonaAgent.enforce(body_md, context=heading)`; the model echoes the heading
  (bold / `#` / plain) as the first line of the returned body and nothing strips it.
- Frontend error mapping is status-only (`blog-editor-requests.ts:60-84`): 422/400/409/5xx
  collapse to generic kind copy (`t('errors.<kind>')`) rendered only at the top of the
  editor view (`blog-post-editor-view.tsx:85-89`); the ReviewBar and the
  VersionHistorySidebar never show the error next to the action that failed.

## Scope

- **Versions:** never append a version entry whose snapshot is an empty document
  (no cover, no quality, no non-empty section heading/body/image, empty
  translations) — the first stored version becomes the first stored AI draft.
  Restore of a still-empty stored snapshot (pre-fix prod data) answers 422 with a
  specific `blog_version_empty` code. A one-shot operator command
  (`python -m rag_backend.scripts.blog_empty_versions`) reports (`--count`) and
  fixes (`--apply`, drop empty entries + renumber, idempotent, advisory-locked,
  batched; `--verify` gates on zero remaining). The orchestrator runs it, not this PR.
- **Rewrite:** strip a leading heading echo from the single-section rewrite result
  (bold, `#`-heading or plain line equal to the heading, normalized: case, markers,
  whitespace) and tell the model not to emit it.
- **Errors:** map backend detail codes (422 validation, `self_review_not_allowed`,
  `blog_reviewer_required`, `blog_document_has_no_sections`, `blog_version_empty`,
  409 `version_conflict`, image budget, rewrite/translation failures, 5xx) to
  specific translated messages (pt + en) and render them **next to the action that
  failed**: the ReviewBar, the VersionHistorySidebar, the per-slot controls and the
  editor top banner (shared `EditorErrorNotice`).

## Non-Goals

- Blog generation (writer / EN / timeout) — AE-0435 owns `blog_generation_service`.
- Changing the write path of `content` itself; only the version snapshot append rule.
- Rebuilding any prod data automatically; the count/fix command is operator-run.

## Acceptance Criteria

- [x] AC1: the generation's first content write leaves `version_history` empty;
  the first append (the next write) is the first stored AI draft — restoring it
  succeeds (no empty bootstrap snapshot anywhere).
- [x] AC2: a content write whose pre-state is empty appends nothing; history stays
  bounded and de-duplicated as before.
- [x] AC3: `blog_empty_versions --count` lists every post whose history holds an
  empty snapshot; `--apply` drops them and renumbers 1..N (idempotent, batched);
  `--verify` exits 0 afterwards. Restoring an empty pre-fix snapshot answers 422
  `blog_version_empty`.
- [x] AC4: a single-section rewrite that echoes the heading (`**H**`, `# H`, plain
  `H`) stores the body without the echo, and the model is instructed not to emit it.
- [x] AC5: each editor error class (422, 400 `self_review_not_allowed`, 409, 5xx)
  shows a specific, translated message (pt + en) at the point of action (review
  bar, version sidebar, slot, top banner).
- [x] AC6: backend + frontend gates green locally (except mutation, CI-owned); CI green.

## Gherkin Scenarios

- `backend/tests/features/blog_versions_errors_ae0438.feature`
- `frontend/tests/features/blog_editor_errors_ae0438.feature`

## Affected Areas

- [x] Backend
- [x] Frontend
- [x] Tests

## Dependencies

None. Parallel workers (AE-0435..AE-0440): this ticket touches
`blog_version_history.py`, `blog_post_ai_service.py`, `blog_post_versions.py`,
`blog-editor-requests.ts`, editor hooks/components and locale files — kept minimal.

## Progress Log

### 2026-10-20

Root causes traced against origin/main (4f811e6fd2); Gherkin written; backend +
frontend fixes implemented with tests; local gates green (mutation deferred to CI).

## Files Touched

Backend:
- `application/services/blog/blog_version_history.py` — `is_empty_document`,
  empty snapshots skipped in `append_version`, `drop_empty_entries` (one-shot repair).
- `application/services/blog_post_ai_service.py` — `strip_heading_echo` +
  `_rewrite_context` (no-heading instruction to `PersonaAgent.enforce`).
- `api/routes/blog_post_versions.py` — restore of an empty snapshot → 422
  `blog_version_empty`.
- `domain/constants/blog_editor.py` — `ERR_BLOG_VERSION_EMPTY`,
  `REWRITE_NO_HEADING_INSTRUCTION`.
- `scripts/blog_empty_versions.py` — operator command (`--count`/`--apply`/`--verify`).

Frontend:
- `constants/blog-editor.ts` — `BLOG_EDITOR_ERROR_CODE_KEYS`.
- `modules/publishing/blog/types.ts`, `lib/editor-error.ts`,
  `components/editor-error-notice.tsx` — shared code-specific error copy/alert.
- `components/section-editor/review-bar.tsx` + `types.ts`, `use-blog-review-actions.ts`
  — review error shown in the bar.
- `components/version-history-sidebar.tsx`, `use-blog-post-editor.ts`
  (`handleRestore` returns the error), `blog-editor-sidebar.tsx` — restore error in
  the sidebar.
- `section-card.tsx` / `image-slot.tsx` / `language-tabs.tsx`,
  `blog-post-editor-view.tsx` — shared notice everywhere.
- `i18n/locales/{pt,en}.json` — `errors.code.*` messages.

Tests: `backend/tests/features/blog_versions_errors_ae0438.feature`,
`backend/tests/unit/application/test_blog_versions_errors_ae0438.py`,
`backend/tests/integration/test_blog_versions_errors_ae0438.py`,
`frontend/tests/features/blog_editor_errors_ae0438.feature`,
`frontend/src/modules/publishing/blog/lib/editor-error.test.ts` + updated
`test_blog_editor_services_ae0424.py`, `test_blog_generation_store_ae0425.py`
(bootstrap snapshot rule), `use-blog-post-editor.test.ts`,
`use-blog-review-actions.test.ts`, `version-history-sidebar.test.tsx`,
`review-bar.test.tsx`, `page.test.tsx`.

## Test Evidence

- Backend: `uv run pytest tests/unit -p no:randomly` → 5118 passed, 1 skipped.
  `uv run pytest tests/integration -p no:randomly` → 868 passed, 13 skipped.
- Frontend: `npx vitest run` → 200 files / 1655 tests passed; `npm run typecheck`
  clean; `npm run lint` + `lint:dead-code` clean.
- Gates (individual runs, no local mutation per orchestrator brief):
  backend lint, lint-diff, blanket-ignore, strict-diff, type, imports, arch-ratchet,
  docstrings, dead-code, inline-prompts, blog-v1-dead-code, redis-factory,
  autopilot-env, healthcheck-loopback, bandit, pip-audit, integrity, test,
  diff-cover, migrations, schema-drift = PASS (dedicated local Postgres,
  DATABASE_URL set); mutation: deferred to CI (worker brief forbids local mutation).
  frontend lint, lint-changed, component-types, duplication, dead-code,
  blog-v1-dead-code, typecheck, build, legacy-guard, legacy-inventory, format,
  security, integrity, test, schema-drift, duplication-tests, dead-files = PASS;
  mutation: deferred to CI.
- `python3 scripts/agent_tasks/validate_all_tickets.py` → All OK.

## QA Report

Pending.

## Blockers

None.
