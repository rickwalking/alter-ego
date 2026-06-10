# Bugfix Helper

## When

- T1 with unclear root cause
- Legacy hotspot — fix vs rewrite slice
- Before large refactor

## Inputs required

- Symptom + repro
- File paths in scope
- **Non-goals** (mandatory)

## Workflow

1. Narrow research (official docs + repo patterns)
2. Propose 2–3 approaches with edge cases and test strategy each
3. Write `.agent/reports/AE-####.bugfix-design.md`
4. Human picks approach → `/developer-skill`

## Does not

- Edit production code
- Replace obvious T1 fast path (repro clear → developer directly)
