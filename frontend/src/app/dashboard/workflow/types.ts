import type { QueueAction } from "@/constants/workflow";
import type {
  BacklogItem,
  QueueBoard,
  QueueItem,
} from "@/schemas/generation-queue";
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

/** The generation queue panel; data and buttons come from the section. */
export interface QueuePanelProps {
  board: QueueBoard | null;
  error: string | null;
  pending: string | null;
  actionError: string | null;
  onAction: (action: QueueAction, id: string) => void;
}

/** One active or parked generation run row. */
export interface QueueRowProps {
  item: QueueItem;
  pending: string | null;
  onAction: (action: QueueAction, id: string) => void;
}

/** One backlog theme row. */
export interface BacklogRowProps {
  item: BacklogItem;
  pending: string | null;
  onAction: (action: QueueAction, id: string) => void;
}
