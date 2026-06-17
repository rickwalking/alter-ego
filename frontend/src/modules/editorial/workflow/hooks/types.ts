/**
 * Editorial workflow hook data-shape types (colocated `types.ts`).
 *
 * Per the component-type-location convention (AE-0144,
 * `frontend/scripts/component-type-location.config.mjs`), object-shape types
 * live here rather than inline in the hook `.ts` files.
 */

export type CalendarItem = {
  id: string;
  content_type: string;
  title: string;
  status: string;
  event_date: string;
  is_scheduled?: boolean;
  phase?: string;
  phase_status?: string;
};

export type ContentCalendar = {
  items: CalendarItem[];
  start: string;
  end: string;
  total: number;
};

export type KanbanCard = {
  id: string;
  title: string;
  topic: string;
  current_phase: string;
  phase_status: string;
  workflow_status?: string | null;
  updated_at: string | null;
};

export type KanbanColumn = {
  phase: string;
  cards: KanbanCard[];
};

export type WorkflowKanban = {
  columns: KanbanColumn[];
};
