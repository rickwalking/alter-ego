# Mutation Testing Report — Phase 1 Implementation

## Tools Status

| Tool | Status | Files Scoped | Result |
|------|--------|--------------|--------|
| **Backend: `mutmut`** | Installed (`>=3.5.0`) but **failed to run** in this environment — `PermissionError` on `/proc/1/cwd` during `copy_src_dir()` | 6 backend files | Manual mutation analysis performed instead |
| **Frontend: `StrykerJS`** | Installed (`@stryker-mutator/core >=9.6.1`) | 3 frontend hooks | **0% score** — "No tests were found" for the mutated files |

---

## Backend Mutation Score

- **Category:** API Routes & ORM Models (per ADR-005)
- **Target (Low):** 60%+
- **Break Threshold:** 40%
- **Actual:** **38.5%**
- **Grade:** **F** (below break)

### Methodology
`mutmut` was attempted with a custom config targeting the 6 scoped backend files, but it crashed with a `PermissionError` on `/proc/1/cwd` (environment limitation). A manual mutation script was executed instead, applying 26 representative mutants across the scoped files and running the existing integration suite (`tests/integration/test_phase1.py`).

### Results Breakdown
- **Killed:** 10 / 26
- **Survived:** 16 / 26
- **Skipped:** 2 / 28

Killable mutants were almost exclusively **404 guard-clause reversals** on endpoints that ARE tested (`get_persona`, `update_persona`, `delete_persona`, `get_blog_post`, `update_blog_post`, `delete_blog_post`, and the `submit` / `approve` / `publish` workflow transitions). All other logic branches survived.

---

## Frontend Mutation Score

- **Category:** UI Components / Hooks (per ADR-005)
- **Target (Low):** 50%+
- **Break Threshold:** 30%
- **Actual:** **0%**
- **Grade:** **F** (below break)

### Methodology
`StrykerJS` was run with a temporary config scoped to the 3 Phase 1 hooks. Stryker instrumented **249 mutants** but exited immediately with:

> "Vitest failed to find test files related to mutated files. [...] No tests were executed. Stryker will exit prematurely."

### Root Cause
There are **zero unit tests** for the scoped hooks:
- `use-personas.ts` — no test file
- `use-rubrics.ts` — no test file
- `use-blog-posts.ts` — no test file (the existing `use-carousel-blog.test.ts` tests a *different* `useBlogPosts` from `@/features/blog/hooks/use-carousel-blog`, not the Phase 1 hook).

Without tests, every mutant survives by definition.

---

## Surviving Mutants (Top 5)

1. **`personas.py:35`** — `data.tone_attributes.model_dump() if data.tone_attributes else {default}` → `if not data.tone_attributes` (always uses default).  
   **Why it survived:** `test_create_persona` passes `tone_attributes` but only asserts `name` and `description`; it never validates the defaulted field.

2. **`personas.py:40`** — `writing_samples=data.writing_samples or []` → `and []`.  
   **Why it survived:** No test asserts `writing_samples` (or `forbidden_phrases`, `preferred_phrases`, `expertise_areas`) on creation.

3. **`blog_post.py:57`** — `if status:` (filter active) → `if not status:` (bypass filter).  
   **Why it survived:** `test_list_blog_posts` calls the endpoint with no query params; the test only checks that `items` and `total` exist, not the actual count or filter behavior.

4. **`rubrics.py:132`** — `if rubric.is_default:` → `if not rubric.is_default:` (deletion protection reversed).  
   **Why it survived:** There is **no `test_delete_rubric`** in the integration suite. The rubric tests only cover `create` and `list`.

5. **`blog_post.py:307`** — `v_data.get("version_number") == version_number` → `!=`.  
   **Why it survived:** There is **no test for version restoration** (`/blog-posts/{id}/restore-version/{version_number}`). The `restore_blog_post_version` endpoint is completely untested.

## Equivalent Mutants

- **Error-message detail strings** (e.g., `"Persona not found: {persona_id}"` → any other text). Tests do not assert the exact `detail` field of `HTTPException`, so changing the string text would survive but is semantically equivalent from an HTTP-contract perspective (still returns 404).
- **`__all__ = []` mutations** at end of route files. Removing or populating this list does not change runtime behavior for these modules.

---

## Summary

- **Backend Mutation Score:** **38.5%** (Grade: F — below 40% break threshold for API Routes)
- **Frontend Mutation Score:** **0%** (Grade: F — below 30% break threshold for UI Components)
- **Overall Mutation Score:** **19/100**

### Key Gaps
1. **Missing frontend unit tests** — All 3 Phase 1 hooks have zero test coverage. Stryker cannot run without tests.
2. **Happy-path-only integration tests** — The 14 backend integration tests only exercise successful flows. No 404 paths, no filter queries, no rejection, no version restoration, no rubric deletion, no source removal, and no persona feedback are tested.
3. **No assertion depth** — Where tests do exist, they assert top-level response fields (`name`, `status`, `items`) but do not verify side effects, filtered counts, default values, or error payloads.

### Recommended Actions
- Add unit tests for `use-personas.ts`, `use-rubrics.ts`, and `use-blog-posts.ts` (mock `fetch` with MSW, assert state updates).
- Extend backend integration tests to cover:
  - 404 error paths for all `GET /{id}`, `PUT /{id}`, `DELETE /{id}` endpoints
  - Query-param filters (`?status=`, `?author_id=`, `?is_default=`)
  - Workflow edge cases: reject, unpublish, version restore
  - Rubric deletion (including the default-rubric guard)
- Once test suites are expanded, re-run `mutmut` (backend) and `StrykerJS` (frontend) to establish a Phase 1 baseline >= 70%.
