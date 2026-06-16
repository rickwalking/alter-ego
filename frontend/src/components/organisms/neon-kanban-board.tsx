/**
 * Re-export shim (AE-0140). The route-aware workflow `NeonKanbanBoard` is a
 * business component owned by the `editorial-operations` bounded context; its
 * canonical home is `@/modules/editorial-operations`. This shim keeps the legacy
 * `@/components/organisms/neon-kanban-board` path resolving for existing
 * importers during the Phase 7 migration window (removal deferred to Phase 8).
 * Import new code from `@/modules/editorial-operations`.
 */
export {
  NeonKanbanBoard,
  type NeonKanbanBoardProps,
} from "@/modules/editorial-operations/board/workflow/components/neon-kanban-board";
