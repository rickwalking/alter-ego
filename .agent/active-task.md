# Active Task

AE-0556 is In Development on `feat/ae-0556-generation-log`.

The architecture plan, ADR, ticket and Gherkin contracts are committed. Implementation follows the red-first acceptance loop.

## Rules

- Only one ticket should be active per agent session unless explicitly coordinating multiple tickets.
- The active ticket must exist under `.agent/tasks/`.
- Agents must update the active ticket before and after implementation work.
- QA must clear active task ownership after writing its report.
