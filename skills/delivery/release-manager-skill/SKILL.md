---
name: release-manager-skill
description: "Prepare PR description, release notes, and merge checklist from ticket, dev summary, and QA report. Use before human review. Never auto-merges."
version: 1.0.0
---

# Release Manager Skill

## Purpose

Prepare completed work for human PR and merge.

## Rules

- Do not auto-merge or push without explicit user request.
- Verify `.agent/reports/AE-####.qa.md` exists.
- Verify docs/ADR updates when architect flagged ADR required.
- Conventional commits; link ticket `AE-####`.
- Move to Ready to Merge only when evidence complete.
- Move to Done only after human approval.

## Checklist

- [ ] QA report PASS or accepted WARN
- [ ] Dev summary present
- [ ] PR description drafted
- [ ] Migration/rollback notes if applicable
- [ ] Final summary in ticket

## Output

PR body, release notes snippet, update ticket `Final Summary`.

## References

- `docs/guides/agentic-team-operating-model.md`
