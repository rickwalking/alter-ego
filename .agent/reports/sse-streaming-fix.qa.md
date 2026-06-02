# QA Validation Report — SSE Streaming Fix

**Date:** 2026-06-02
**Scope:** `frontend/src/lib/sse-client.ts`, `frontend/src/lib/sse-client.test.ts`, `nginx/nginx.conf`, `skills/developer-skill/SKILL.md`
**Tests:** 748/748 passing (63 test files)

---

## Overall Score: 86/100 (Grade B)

### Per-Dimension Results

| Dimension | Status | Score | Findings |
|-----------|--------|-------|----------|
| Security | ✅ PASS | 90/100 | 0 blockers, 1 warning (gzip config), 4 suggestions |
| Code Quality | 🟠 WARN | 90/100 | Lint/typecheck pass; test file 12 lines over 400 limit |
| Mutation Testing | ❌ FAIL | 62/100 | Estimated ~62% (below 70% ADR-005 threshold); 10 surviving mutants |
| Acceptance Criteria | ✅ PASS | 100/100 | All 12 criteria satisfied with passing tests |
| Orphan/Unfinished Code | 🟠 WARN | 85/100 | 2 orphaned exports (low), test file over 400-line limit |

---

## 🔴 Blocker Findings

None.

---

## 🟠 Warning Findings

### W1 — Test file exceeds 400-line limit
- **File:** `frontend/src/lib/sse-client.test.ts`
- **Detail:** 412 lines (12 over the project's 400-line cap per CLAUDE.md)
- **Suggestion:** Extract `createMockReader` and `createSseResponse` helpers into a `sse-client.test-utils.ts` fixture file, or split tests into two files.
- **Reference:** CLAUDE.md universal rule: "Max 400 lines per file"

### W2 — Gzip may interfere with SSE in production
- **File:** `nginx/nginx.conf`, line 25; `nginx/nginx.conf.ssl`, line 25
- **Detail:** `gzip on;` is set globally. While `gzip_types` does NOT include `text/event-stream` (mitigating this today), `gzip_proxied any;` combined with nginx behavior could buffer responses before compression. If `text/event-stream` is ever added to `gzip_types`, SSE streaming will break.
- **Reference:** OWASP A02 — Security Misconfiguration
- **Action:** Add `gzip off;` inside the `/api/conversations/` location blocks to prevent future regression.

### W3 — Estimated mutation score below threshold
- **File:** `frontend/src/lib/sse-client.ts`
- **Detail:** Manual mutation analysis estimates ~62% mutation score (ADR-005 requires 70% for business logic). 10 surviving mutants identified, including null-ID events, non-JSON data fallback, CRLF delimiters, and mid-stream abort handling.
- **Reference:** ADR-005 mutation testing thresholds
- **Action:** Add 6 suggested test cases (see M1–M6 below)

---

## 🟡 Suggestion Findings

### S1 — Orphaned export: `SseEventType`
- **File:** `frontend/src/lib/sse-client.ts`, line 14
- **Detail:** Exported type never imported by any production consumer (only used internally). Consumers get type inference through callback parameters.
- **Action:** Consider removing `export` keyword.

### S2 — Orphaned export: `SseStreamOptions`
- **File:** `frontend/src/lib/sse-client.ts`, line 28
- **Detail:** Exported interface never imported by any consumer. All callers pass object literals directly to `streamSseEvents()` and get type inference.
- **Action:** Consider removing `export` keyword unless an external consumer needs it.

### S3 — No explicit `proxy_read_timeout` on chat API location
- **File:** `nginx/nginx.conf`, lines 150–160
- **Detail:** The carousel workflow location has `proxy_read_timeout 300s` but the `/api/conversations/` location relies on the nginx default (60s). A long SSE stream could be terminated prematurely.
- **Action:** Add `proxy_read_timeout 300s;` to the `/api/conversations/` location block.

### S4 — No reconnection or diagnostics on connection drops
- **File:** `frontend/src/lib/sse-client.ts`, lines 316–322
- **Detail:** If `onError` callback is not provided, errors are silently swallowed. No reconnection logic exists.
- **Action:** Add `console.warn` before delegating to optional `onError`, at least in non-production builds.

### S5 — `statusText` may expose server diagnostic details
- **File:** `frontend/src/lib/sse-client.ts`, line 279
- **Detail:** Error message includes `response.statusText` which some servers populate with diagnostic details.
- **Action:** Sanitize to only include status code, or log full statusText server-side.

### S6 — HTTP protocol strings as literals
- **File:** `frontend/src/lib/sse-client.ts`, lines 261–283
- **Detail:** `"Content-Type"`, `"application/json"`, `"text/event-stream"`, `"Last-Event-ID"`, `"POST"`, `"include"` are inline string literals rather than named constants.
- **Action:** Extract to constants (e.g., in `frontend/src/constants/api.ts`).

---

## ⚪ Suggested Test Additions (for mutation score improvement)

| # | Test Case | Priority | Surviving Mutant It Kills |
|---|-----------|----------|---------------------------|
| M1 | Events without `id:` field | High | Null-flower path in `flushEvent` |
| M2 | Non-JSON data → `raw` fallback | High | JSON try/catch removal |
| M3 | CRLF `\r\n` delimiters | Medium | CRLF branch in `findBlankLine` |
| M4 | Unicode/multi-byte content | Medium | TextDecoder corruption |
| M5 | Empty response body | Medium | Empty-body crash |
| M6 | Mid-stream abort | Medium | Mid-stream abort handling |

---

## Top 3 Risks

1. **Mutation score below threshold (62% vs 70%)** — Tests are comprehensive for happy paths and errors, but missing edge-case coverage for null-ID events, non-JSON data, and CRLF delimiters means some mutants survive.
2. **Test file exceeds 400 lines** — Violates CLAUDE.md universal rule. Minor but structural — should be addressed before merging.
3. **Gzip could silently break SSE** — Currently mitigated (text/event-stream not in gzip_types) but fragile. A future config change could regress SSE without any test catching it.

---

## Recommended Next Steps

1. **Fix high-priority items:** Extract test helpers to reduce `sse-client.test.ts` under 400 lines; Add M1 (null-ID events) and M2 (non-JSON raw fallback) tests.
2. **Harden nginx config:** Add `proxy_read_timeout 300s` and `gzip off` to `/api/conversations/` location.
3. **Address orphaned exports:** Review if `SseEventType` and `SseStreamOptions` need to be exported.
4. **Run StrykerJS incrementally** when mutation testing infrastructure is available to validate the estimated 62% score.
