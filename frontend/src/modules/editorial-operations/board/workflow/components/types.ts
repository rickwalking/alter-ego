/**
 * Workflow board component prop types (colocated `types.ts`).
 *
 * Per the component-type-location convention (
 * `frontend/scripts/component-type-location.config.mjs`), component prop shapes
 * live here rather than inline in the `.tsx` files.
 */

import type { ReactNode } from "react";
import type { KanbanCard, KanbanColumn } from "@/schemas/neon-kanban";

export interface NeonKanbanBoardProps {
  columns: KanbanColumn[];
  /** Controls shown under a card, outside its link (e.g. archive). */
  renderCardActions?: (card: KanbanCard) => ReactNode;
}
