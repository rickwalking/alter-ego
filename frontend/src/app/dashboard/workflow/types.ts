import type { WorkflowPostActionResult } from "@/modules/editorial";
import type { KanbanCard } from "@/schemas/neon-kanban";

/** The archive control under one workflow board card. */
export interface CardArchiveActionProps {
  card: KanbanCard;
  /** The board lists archived carousels (restore) instead of active ones. */
  archived: boolean;
  /** Called once the archive or restore went through. */
  onChanged: () => void;
}

/** The board of the workflow page, active or archived. */
export interface WorkflowBoardViewProps {
  archived: boolean;
}

/** The board's first-load and failure feedback. */
export interface BoardFeedbackProps {
  loading: boolean;
  error: string | null;
  onRetry: () => void;
}

/** The Ativos | Arquivados segmented control in the board top bar. */
export interface WorkflowViewSwitchProps {
  /** Whether the archived board view is active. */
  archived: boolean;
}

/** The menu items rendered inside a card's overflow menu. */
export interface CardArchiveMenuItemsProps {
  card: KanbanCard;
  /** The board lists archived carousels (restore) instead of active ones. */
  archived: boolean;
  /** Whether the archive confirmation step is showing. */
  confirming: boolean;
  onConfirmingChange: (confirming: boolean) => void;
  archive: WorkflowPostActionResult;
  restore: WorkflowPostActionResult;
  /** Id of the element describing the refusal reason. */
  reasonId: string;
}
