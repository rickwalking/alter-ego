# Plan Validator

## When

Before ticket Status: **Ready** or **In Development**.

## Checks

| Area | Items |
|------|--------|
| Structure | Goal, problem, scope, non-goals, dependencies |
| AC | Specific, testable commands; 5–15 items; EARS style |
| Gherkin | Happy + failure paths if behavior changes |
| Risks | Rollback, migration, auth, observability |
| Edge cases | Timeouts, idempotency, empty state, permissions |
| Alter-Ego | ADR conflicts, high_risk_areas, LangGraph/prompt rules |
| Tests | Unit/integration/e2e per ADR-005 where applicable |

## Output format

```markdown
# Plan Validation — AE-####
Status: PASS | WARN | FAIL
Blocking gaps: ...
Warnings: ...
Suggested AC additions: ...
```

## vs QA agent

Validator = **spec/plan** (pre-dev). QA agent = **code** (post-dev).
