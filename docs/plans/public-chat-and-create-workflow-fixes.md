# Public Chat & Create Workflow Fixes

**Status:** `accepted`
**Branch:** `design-implementation`

## Issues

| ID | Issue | Root cause | Fix |
|----|-------|------------|-----|
| C1 | Public chat messages vanish, no AI reply | `finalizeStream` clears optimistic messages when `enableHistory: false` | Skip clear/invalidate when history disabled |
| C2 | No typing animation | Static dot in `ChatMessageList` | Add `chat-pulse-dot` animation |
| H1 | Homepage not in PT | `HomePageContent` ignores `t`/`tc` props | Wire `next-intl` keys in hero, stats, features, CTAs |
| H2 | No Chat in public header | `public-header.tsx` missing link | Add `/chat` nav link |
| W1 | 404 on workflow state | SSE/poll runs before workflow started | Gate SSE until `current_phase` exists; stop poll on 404 |
| W2 | Stream endpoint polling constantly | SSE `onerror` → fallback poll loop on 404 state | Stop fallback when state is null |
| W3 | No feedback after start with materials | `onWorkflowStarted` only sets flag; never calls `start()` | Invoke `editorialWorkflow.start()` + navigate to outline |
| W4 | Materials form box grows | Unbounded textarea/list in card | Fixed textarea height + scroll |
| W5 | Reload 404 on state | Same as W1/W2 | Same fixes |

## Verification

- `npm run lint && npm run typecheck && npm run test -- --run`
- Playwright MCP: login → create carousel → materials → workflow through gates
