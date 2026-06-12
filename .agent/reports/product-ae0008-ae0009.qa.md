# Product QA Report — AE-0008 + AE-0009 (batch)

**Scope:** AE-0008 (URL source extraction), AE-0009 (workflow error feedback + retry)
**Verdict:** ✅ **PASS** (converged — WARN → fix → confirmation PASS)

## Provenance

| Field | Value |
|-------|-------|
| Tool | `scripts/qa/run_external_qa.sh` → **Cursor Agent** (`--print`, read-only) |
| Reviewer | external, no conversation context (cross-model vs the Claude implementer) |
| Mode | wave (batch, tagged by ticket) |
| Implementation commit | `d17dcc3`; fixes `4e49237` |
| Round 1 | WARN — 0 critical, 2 warning (F-1, F-2), 3 minor (F-3, F-4, F-5) |
| Round 2 | PASS — all 5 findings RESOLVED, zero new |
| Loop policy | WARN → fix all → confirmation round → PASS. Autonomous |
| Date | 2026-06-12 |
| **Operational incident** | **OpenCode died mid-stream on every attempt today** (both the batch prompt and the lean confirmation prompt; not an init hang — it streamed, read files, then died before emitting). **Codex** was out of usage quota (resets ~19:28). **Cursor** was used for both rounds and is the recorded reviewer. Cross-model independence preserved (dev=Claude, QA=Cursor). |

## Round summaries

### Round 1 (commit `d17dcc3`) — WARN
Cursor verified ACs across both tickets, ran backend + frontend suites, and surfaced 5 findings:
- **F-1 (AE-0009, warning)**: `_error_message_field` surfaced the raw persisted `workflow_error`
  to clients while the SSE path routes errors through the `CLIENT_SAFE_SSE_ERROR_MESSAGES`
  allowlist — a potential internal-error/secret leak + SSE/state inconsistency.
- **F-2 (AE-0009, warning)**: publish-page failed-state had no unit test (AC#19 requires it).
- **F-3 (AE-0009, minor)**: retry-failure path (button re-enable) untested.
- **F-4 (AE-0008, minor)**: the `url_scrape_failed` structlog warning was unasserted.
- **F-5 (AE-0008, minor)**: bare-URL superset scraping behavior undocumented/untested.

### Fix round (commit `4e49237`)
- **F-1**: `_error_message_field` now delegates to `resolve_workflow_sse_error_message`
  (same `CLIENT_SAFE_SSE_ERROR_MESSAGES` allowlist as SSE); non-allowlisted raw errors collapse
  to the safe `workflow_phase_failed` message — no traceback/secret leak. +allowlist tests.
- **F-2**: extracted `PublishFailedNotice` + `publish-failed-notice.test.tsx`.
- **F-3**: extracted `createRetryWorkflowHandler` + `create-retry-handler.test.ts` (failure path).
- **F-4**: `test_graceful_degradation_on_failure` asserts the warning via `capture_logs`.
- **F-5**: docstring + `test_bare_url_without_source_type_is_scraped`.

### Round 2 (commit `4e49237`) — PASS
Cursor independently confirmed all 5 RESOLVED with evidence; backend ~1661 passed, frontend
typecheck clean, no regressions, no new findings.

## Findings disposition

| Finding | Ticket | Severity | Disposition |
|---------|--------|----------|-------------|
| F-1 (raw error leak to client) | AE-0009 | warning | **Fixed** in `4e49237` (client-safe allowlist reused) |
| F-2 (publish failed-state test) | AE-0009 | warning | **Fixed** (PublishFailedNotice + test) |
| F-3 (retry-failure test) | AE-0009 | minor | **Fixed** (handler extracted + test) |
| F-4 (log assertion) | AE-0008 | minor | **Fixed** |
| F-5 (superset doc + test) | AE-0008 | minor | **Fixed** |

No findings were silently dropped.

## Developer deviations — disposition

| Deviation | Ticket | Disposition |
|-----------|--------|-------------|
| Core feature pre-existed in base; new change = structlog graceful-degradation logging | AE-0008 | **Accepted** — verified observable, no traceback leak, no get_container regression |
| `_scrape_url_sources` superset-matches bare URLs even without source_type==url | AE-0008 | **Accepted** — now documented + tested (F-5); plain documents not wrongly scraped |
| error_message sourced from existing `workflow_error` persistence (no new persistence site) | AE-0009 | **Accepted** — surfaced via client-safe allowlist (F-1) |
| phase_status kept current literals, type derived from const (AE-0071 not landed) | AE-0009 | **Accepted** — alignment-compliant; follow-up comment present |

## Per-dimension results (consolidated)

| Dimension | Status | Notes |
|-----------|--------|-------|
| Acceptance Criteria | ✅ PASS | AE-0008 12/12, AE-0009 19/19 met against current code |
| Code quality | ✅ PASS | backend mypy strict clean (389), ruff clean; frontend typecheck + lint clean |
| Tests | ✅ PASS | backend 1661 passed (2 skipped); frontend 822 passed; +new coverage for all fixes |
| Mutation (analytical) | ✅ PASS | scrape/sanitize/allowlist/failed-card tests cover branch + boundary cases |
| Orphan / unfinished | ✅ PASS | no bare except/pass; new helpers + fields used; barrels updated |
| Security | ✅ PASS | scraped web content sanitized before LLM (injection surface); error_message client-safe (no traceback/secret leak) |

## Disposition

Both tickets → **Review**. AE-0008 + AE-0009 complete.
