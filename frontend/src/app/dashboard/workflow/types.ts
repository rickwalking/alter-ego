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
