# Mutation Analysis Report: SSE Client (`sse-client.ts`)

**Target**: `frontend/src/lib/sse-client.ts`
**Tests**: `frontend/src/lib/sse-client.test.ts` (12 tests)
**Threshold (ADR-005)**: 70%+ mutation score (utility/business logic)

---

## Executive Summary

| Metric | Value |
|--------|-------|
| Estimated mutation score | **~62%** |
| Surviving mutants identified | **10** |
| Strongly killed | ~16 |
| Tests | 12 |
| Target (ADR-005) | 70%+ |
| **Verdict** | **❌ Below threshold — needs 3–5 additional tests** |

---

## Surviving Mutants (Detailed)

### 1. SSE `event:` field never exercised

| Property | Value |
|----------|-------|
| **Location** | `parseSseLine()` lines 74-76 |
| **Mutant** | Remove the `line.startsWith("event: ")` branch |
| **Effect** | `state.currentEvent` is never set — all events get `event: undefined` |
| **Why it survives** | All 12 tests use the backend convention of embedding the event type in `data.type` (e.g. `data: {"type":"token"}`). The `event:` SSE field is completely untested. |
| **Killed by** | No existing test |

```typescript
// sse-client.ts:74-76 — untested branch
if (line.startsWith("event: ")) {
  state.currentEvent = line.slice(7) as SseEventType;
  return null;
}
```

### 2. `id:` field initialization / leak across events

| Property | Value |
|----------|-------|
| **Location** | `createParserState()` line 54 + `flushEvent()` line 126 |
| **Mutant A** | `currentId` initialized to `""` instead of `undefined` |
| **Mutant B** | `flushEvent` does NOT reset `state.currentId = undefined` (line 126) |
| **Effect** | Events without `id:` would inherit stale ids from previous events |
| **Why it survives** | All events in tests include `id:` fields (test 1: `id: 1`; test 2: `id: 1,2,3,4`). No test sends an event **without** an `id:` field. |
| **Killed by** | No existing test |

### 3. Non-JSON data `raw` fallback untested

| Property | Value |
|----------|-------|
| **Location** | `flushEvent()` lines 105-109 |
| **Mutant** | Remove the `try/catch` entirely — `JSON.parse()` throws uncaught |
| **Effect** | Non-JSON SSE data crashes the parser instead of being captured as `{ raw: ... }` |
| **Why it survives** | All test data is valid JSON: `{"type":"token","content":"Hello"}`. No test sends malformed JSON. |
| **Killed by** | No existing test |

```typescript
// sse-client.ts:105-109 — untested error recovery path
try {
  parsedData = JSON.parse(state.currentData) as Record<string, unknown>;
} catch {
  parsedData = { raw: state.currentData };
}
```

### 4. CRLF (`\r\n`) delimiter never tested

| Property | Value |
|----------|-------|
| **Location** | `findBlankLine()` lines 190-196 |
| **Mutant** | Remove the `\n\r\n` detection branch |
| **Effect** | CRLF-delimited streams (`\r\n` line endings) would not be recognized |
| **Why it survives** | All tests use `\n\n` (LF) delimiters. No test uses `\n\r\n`. |
| **Killed by** | No existing test |

```typescript
// sse-client.ts:190-196 — untested branch
if (
  i + 2 < buffer.length &&
  buffer[i + 1] === "\r" &&
  buffer[i + 2] === "\n"
) {
  return i;
}
```

### 5. Unicode / multi-byte content

| Property | Value |
|----------|-------|
| **Location** | `streamSseEvents()` line 301 — `TextDecoder.decode(chunk)` |
| **Mutant** | Various: change decoder encoding, drop `{ stream: true }`, mishandle multi-byte boundaries |
| **Effect** | Corrupted Unicode content silently parsed |
| **Why it survives** | All tests use ASCII content only (`"Hello"`, `" world"`, `"!"`, etc.). No test sends emoji, CJK, or accented characters. |
| **Killed by** | No existing test |

### 6. Empty response body

| Property | Value |
|----------|-------|
| **Location** | `processChunk()` line 143 and while loop lines 295-307 |
| **Mutant** | Various: crash on empty chunk, infinite loop, hang |
| **Effect** | Empty body causes undefined behavior |
| **Why it survives** | No test sends an empty string chunk or an empty response body. |
| **Killed by** | No existing test |

### 7. `event:` field without `data:` field

| Property | Value |
|----------|-------|
| **Location** | `flushEvent()` lines 99-100 |
| **Mutant** | Events with only `event:` but no `data:` are mishandled |
| **Effect** | `!state.currentData` is `true`, `!state.currentEvent` is `false` → does NOT return null, produces `data: {}` |
| **Why it survives** | No test sends `event: xxx\n\n` without a `data:` line. |
| **Killed by** | No existing test |

### 8. Buffer-leak across `processChunk()` calls (single-chunk tests)

| Property | Value |
|----------|-------|
| **Location** | `processChunk()` line 173 — `state.buffer = state.buffer.slice(searchStart)` |
| **Mutant** | Remove the buffer-trimming line |
| **Effect** | On multi-chunk streams, old processed data is re-processed, emitting duplicate events |
| **Why survives partially** | The 8 tests that use a single chunk (tests 1, 4, 6, 7, 8, 9, 10, 11) would NOT catch this because `processChunk` is called only once — no buffer accumulation between calls. Only multi-chunk tests (2, 3, 5, 12) would catch it. **Score: ~67% of tests miss it.** |
| **Killed by** | Tests 2, 3 (barely — test 5 and 12 have special paths) |

### 9. Abort mid-stream (during reader.read, not during fetch)

| Property | Value |
|----------|-------|
| **Location** | `streamSseEvents()` lines 295-322 |
| **Mutant** | AbortError thrown from `reader.read()` (second call onward) is not handled |
| **Effect** | The `if (error instanceof DOMException && error.name === "AbortError")` check is present, but no test exercises an abort **after** fetch succeeds but **during** reading |
| **Why it survives** | Test 7 mocks `fetch` to reject immediately with AbortError. This exercises the abort **before** fetch resolves. Mid-stream abort (after fetch, during reader.read) is untested. |
| **Killed by** | No existing test |

### 10. Forward-slash data lines (edge case)

| Property | Value |
|----------|-------|
| **Location** | `parseSseLine()` line 70, 74, 78 |
| **Mutant** | Lines that start with `data:` without a following space (i.e. `data:something` without the space that SSE spec mandates) |
| **Effect** | `line.startsWith("data: ")` is `false` for `"data:something"` — line falls through to unknown handler |
| **Why it survives** | No test sends SSE lines with non-standard formatting. |
| **Killed by** | No existing test |

---

## Equivalent Mutants (no behavioral change)

These mutations change the code but produce identical behavior. They do not affect mutation score.

| Location | Mutant | Why Equivalent |
|----------|--------|----------------|
| `parseSseLine()` lines 83-84 | Remove `:` comment handling | Unknown lines already return `null` at line 91. The comment handler is documentation-only. |
| `processChunk()` line 148 | `<=` instead of `<` | When `searchStart === buffer.length`, `findBlankLine` loop condition `i < buffer.length - 1` is already false, returns `-1`, loop breaks. |
| `flushEvent()` line 115 | `||` instead of `&&` | For `parsedData.type` = truthy string, `"token" \|\| typeof ...` evaluates to `"token"` (truthy) same as `"token" && "string"` which is also `"string"` (truthy). Both pass the outer `??` same way. |

---

## Test Coverage Gap Analysis

### Covered Behaviors ✅

| Behavior | Test(s) |
|----------|---------|
| Single token event parsing | Test 1 |
| Multiple events across chunks | Test 2 |
| Chunk boundaries splitting lines | Test 3 |
| Keep-alive comment lines | Test 4 |
| HTTP error → onError | Test 5 |
| Wrong content type → onError | Test 6 |
| AbortError silence (pre-fetch) | Test 7 |
| Network error → onError | Test 8 |
| Error event data → onEvent + onComplete | Test 9 |
| Last-Event-ID header | Test 10 |
| Null response body → onError | Test 11 |
| Final event without trailing blank line | Test 12 |
| Multiple events per chunk (after buffering) | Test 3 (second chunk) |

### Uncovered Behaviors ❌

| Behavior | Gap Severity | Suggested Test |
|----------|-------------|----------------|
| Events without `id:` field | **High** | Send `data: {"type":"token"}\n\n` with no `id:` — verify `event.id` is `undefined` |
| SSE `event:` field | **High** | Send `event: custom\ndata: {}\n\n` — verify `event.event === "custom"` |
| Non-JSON `data:` content | **High** | Send `data: plain text, not JSON\n\n` — verify `event.data.raw` exists |
| Unicode content | **Medium** | Send `data: {"content":"Olá, mundo! 🌍"}\n\n` — verify correct parsing |
| CRLF delimiters (`\r\n`) | **Medium** | Send `data: {"type":"token"}\r\n\r\n` — verify event parsed |
| Empty response body | **Medium** | Send `[]` (no chunks) — verify `onComplete` called, no `onEvent` |
| Mid-stream abort | **Medium** | Mock `reader.read()` to reject with AbortError on second call — verify silent abort |
| `event:` without `data:` | **Low** | Send `event: ping\n\n` — verify `event.data` is `{}` |

---

## Suggested Additional Tests

### Test 13 — Event without `id:` field preserves `undefined`
```typescript
// Scenario: SSE event without id: field
//   Given a streaming response without an id field
//   When streamSseEvents is called
//   Then onEvent is called with id: undefined
it("handles events without id field", async () => { ... });
```
**Payload**: `'data: {"type":"token","content":"no-id"}\n\n'`
**Assertions**:
- `onEvent` called with `id: undefined`
- IDs don't leak across events (send a second event also without `id:` — both should have `id: undefined`)

### Test 14 — Non-JSON data uses `raw` fallback
```typescript
// Scenario: Non-JSON data line
//   Given a streaming response with plain text data
//   When streamSseEvents is called
//   Then onEvent is called with data.raw containing the text
it("wraps non-JSON data in raw field", async () => { ... });
```
**Payload**: `'data: Hello, this is plain text\n\n'`
**Assertions**:
- `onEvent` called once
- `event.data.raw === "Hello, this is plain text"`

### Test 15 — CRLF line endings
```typescript
// Scenario: SSE with CRLF line endings
//   Given a streaming response using \r\n line endings
//   When streamSseEvents is called
//   Then events are parsed correctly
it("parses CRLF-delimited SSE events", async () => { ... });
```
**Payload**: `'data: {"type":"token"}\r\n\r\n'`
**Assertions**:
- `onEvent` called with `event.event === "token"`

### Test 16 — Unicode content
```typescript
// Scenario: Unicode content in stream
//   Given a streaming response with Unicode characters
//   When streamSseEvents is called
//   Then the Unicode content is correctly decoded
it("correctly decodes Unicode content", async () => { ... });
```
**Payload**: `'data: {"type":"token","content":"Olá, mundo! 🌍"}\n\n'`
**Assertions**:
- `onEvent` called
- `event.data.content === "Olá, mundo! 🌍"`

### Test 17 — Empty response body
```typescript
// Scenario: Empty response body
//   Given a streaming response with no data chunks
//   When streamSseEvents is called
//   Then onComplete is called without any events
it("handles empty response body gracefully", async () => { ... });
```
**Payload**: `[]` (no chunks)
**Assertions**:
- `onEvent` not called
- `onComplete` called once
- `onError` not called

### Test 18 — Abort mid-stream
```typescript
// Scenario: Abort signal received during stream reading
//   Given an active stream that gets aborted mid-read
//   When streamSseEvents is called with abort signal
//   Then no callbacks are called (silent abort)
it("silently handles mid-stream abort", async () => { ... });
```
**Setup**: Mock `reader.read()` to return one event on first call, then reject with AbortError on second call.
**Assertions**:
- `onEvent` called once (for the first event)
- `onError` not called
- `onComplete` not called

---

## Mutation Score Estimate Breakdown

| Category | Count |
|----------|-------|
| Strongly killed mutants | ~16 |
| Surviving mutants | **10** |
| Equivalent mutants | 3 |
| **Estimated score** | **~62%** |

### Killable mutants (16)
These would be caught by the existing 12 tests:
| Mutant Location | Killer Test |
|----------------|-------------|
| `createParserState()` returns `{}` | Test 1 |
| `currentData` starts as `null` | Test 1 |
| Remove `id:` parsing | Test 1 |
| Remove `data:` parsing | Test 1 |
| Remove `!response.ok` | Test 5 |
| Remove content-type check | Test 6 |
| Remove null body check | Test 11 |
| Remove `onComplete?.()` | Tests 1, 2, 4, 9, 12 |
| Remove `onError` call | Tests 5, 6, 8, 11 |
| Remove AbortError silence | Test 7 |
| Remove `onEvent` dispatch loop | Test 1 |
| Remove while loop | All tests |
| `===` changed to `!==` in `findBlankLine` | Test 1 |
| Always-done reader read | Test 1 |
| `flushBuffer` returns null always | Test 12 |
| `flushEvent` never resets `currentData` | Test 2 |

---

## Recommendations

1. **Add tests 13–18** (6 new tests) to reach 70%+ mutation score
2. **Prioritize tests 13, 14, and 15** — they cover three distinct untested branches with real-world relevance (SSE without `id:`, non-JSON data for robustness, CRLF interop)
3. **Add a test for event-only events** (test 13 variant with `event:` field) — the `event:` SSE field is a core part of the SSE spec and should be supported even if the backend currently uses `data.type`
4. **Verify after adding tests**: re-run StrykerJS to confirm the mutation score exceeds 70%

---

*Analysis performed manually against `frontend/src/lib/sse-client.ts` revision implementing SSE streaming with 12 unit tests.*
