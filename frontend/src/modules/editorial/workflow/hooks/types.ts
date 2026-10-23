/**
 * Editorial workflow hook data-shape types (colocated `types.ts`).
 *
 * Per the component-type-location convention (
 * `frontend/scripts/component-type-location.config.mjs`), object-shape types
 * live here rather than inline in the hook `.ts` files.
 */

export interface CalendarItem {
  id: string;
  content_type: string;
  title: string;
  status: string;
  event_date: string;
  is_scheduled?: boolean;
  phase?: string;
  phase_status?: string;
}

export interface ContentCalendar {
  items: CalendarItem[];
  start: string;
  end: string;
  total: number;
}

export interface KanbanCard {
  id: string;
  title: string;
  topic: string;
  current_phase: string;
  phase_status: string;
  workflow_status?: string | null;
  updated_at: string | null;
  /** The caller may archive or restore it (owner or admin, not a reviewer). */
  can_archive?: boolean;
  /** Why the archive rules refuse it now, if they do. */
  archive_refusal?: string | null;
}

export interface KanbanColumn {
  phase: string;
  cards: KanbanCard[];
}

export interface WorkflowKanban {
  columns: KanbanColumn[];
}

export interface WorkflowPostActionMessages {
  success: string;
  failed: string;
}

export interface WorkflowPostActionResult {
  submitting: boolean;
  message: string | null;
  post: (url: string, body: object) => Promise<void>;
}
