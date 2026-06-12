# AE-0040 Series Rollback Plan

## Scope

This document covers rollback strategy for the AE-0041 through AE-0049 ticket
series (code health, refactoring, and CI gate changes).  Each ticket below
includes the merge commit(s) that introduced the change.

> **Replace `<AE-NNNN merge hash>` with the actual merge commit SHA before
> executing.**

---

## Order of Revert (reverse of merge order)

Revert from newest to oldest to minimise merge conflicts.

| Step | Revert | Ticket | Description |
|------|--------|--------|-------------|
| 1 | `git revert <AE-0048 merge commit>` | AE-0048 | Re-enables blanket ignores |
| 2 | `git revert <AE-0049 merge commit>` | AE-0049 | Reverts CI gate changes |
| 3 | `git revert <AE-0044 merge commit>` | AE-0044 | Reverts builder pattern |
| 4 | `git revert <AE-0045 merge commit>` | AE-0045 | Reverts dispatch / CoR |
| 5 | `git revert <AE-0046 merge commit>` | AE-0046 | Reverts validation refactor |
| 6 | `git revert <AE-0047 merge commit>` | AE-0047 | Reverts frontend modifications |
| 7 | `git revert <AE-0041/AE-0042/AE-0043 merge commits>` | AE-0041–0043 | Reverts cleanup / rename |

After each revert, resolve conflicts if any and commit with `--no-edit`.

---

## Verification After Full Revert

```bash
# 1. Lint check
cd backend && uv run ruff check src/ --no-cache

# 2. Type check
cd backend && MYPYPATH=src uv run mypy -p rag_backend

# 3. Unit tests
cd backend && uv run pytest tests/ -x -q --no-header

# 4. Frontend (if AE-0047 was reverted)
cd frontend && npm run typecheck && npm run lint
```

---

## If a Specific Ticket Breaks

1. Revert just that ticket's commit:
   ```bash
   git revert <offending merge SHA> --no-edit
   ```

2. Open a fixing PR with the revert.

3. Document the failure reason in the ticket's Decision Log (`docs/decisions/`).

---

## Rollback Audit Trail

Each revert should be annotated in the commit message:

```
Revert "AE-0044: Builder pattern refactor"

This reverts commit <SHA>.

Reason: <brief explanation of why revert was needed>
```

The cumulative revert set should produce a single PR with a clear summary
of what is being rolled back and why.

---

## Post-Rollback Checklist

- [ ] `ruff check` passes
- [ ] `mypy --strict` passes
- [ ] All tests pass (backend + frontend)
- [ ] No orphaned imports or dead code from partial revert
- [ ] Decision Log updated for each reverted ticket
