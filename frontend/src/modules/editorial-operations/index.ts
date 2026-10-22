/**
 * `editorial-operations` — bounded-context public contract.
 *
 * Owns the operational dashboard surface — the editorial board (blog-posts,
 * calendar, chat, personas, rubrics, workflow board adapters) and editorial
 * analytics — migrated from the legacy `features/dashboard` and
 * `features/analytics` folders. This barrel is the ONLY import surface for
 * cross-context and `app/` consumers; everything else under
 * `modules/editorial-operations/**` is internal.
 *
 * Subdivisions:
 *   - `board/`     — dashboard board domains (was `features/dashboard`).
 *   - `analytics/` — editorial analytics summary hook (was `features/analytics`).
 *
 * Cross-module needs (e.g. the calendar/workflow board adapters consuming the
 * editorial workflow hooks) go through the `@/modules/editorial` barrel, never
 * its internals. See `src/modules/README.md` for the convention.
 */

export * from "./board/blog-posts/types";
export * from "./board/blog-posts/constants";
export * from "./board/blog-posts/helpers";
export * from "./board/blog-posts/components/badge";
export * from "./board/blog-posts/components/status-badge";
export * from "./board/blog-posts/adapters/blog-post-adapter";

export * from "./board/calendar/types";
export * from "./board/calendar/constants";
export * from "./board/calendar/helpers";
export * from "./board/calendar/view-helpers";
export * from "./board/calendar/components/svg-icon";
export * from "./board/calendar/adapters/calendar-adapter";

export * from "./board/chat/types";
export * from "./board/chat/constants";
export * from "./board/chat/adapters/chat-adapter";

export * from "./board/personas/adapters/persona-adapter";

export * from "./board/rubrics/types";
export * from "./board/rubrics/adapters/rubric-adapter";

export * from "./board/workflow/constants";
export * from "./board/workflow/adapters/workflow-adapter";
export {
  NeonKanbanBoard,
  type NeonKanbanBoardProps,
} from "./board/workflow/components/neon-kanban-board";

export * from "./analytics/hooks/use-editorial-analytics";
export {
  qualityScoreStat,
  type QualityScoreStat,
} from "./analytics/quality-score";
export * from "./analytics/hooks/use-instagram-insights";
