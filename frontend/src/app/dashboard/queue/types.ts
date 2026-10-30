import type { QueueAction } from "@/constants/workflow";
import type { GenerationQueueReprocessTarget } from "@/modules/editorial";
import type {
  BacklogItem,
  QueueBoard,
  QueueItem,
} from "@/schemas/generation-queue";

export type QueueActionHandler = (
  action: QueueAction,
  id: string,
  reprocess?: GenerationQueueReprocessTarget,
) => void;

/** The generation queue panel; data and buttons come from the section. */
export interface QueuePanelProps {
  board: QueueBoard | null;
  error: string | null;
  pending: ReadonlySet<string>;
  actionError: string | null;
  processPending: boolean;
  processError: string | null;
  onAction: QueueActionHandler;
  onProcess: () => void;
}

/** One active or parked generation run row. */
export interface QueueRowProps {
  item: QueueItem;
  pending: ReadonlySet<string>;
  onAction: QueueActionHandler;
}

/** One backlog theme row. */
export interface BacklogRowProps {
  item: BacklogItem;
  pending: ReadonlySet<string>;
  onAction: QueueActionHandler;
}

export interface QueueReprocessButtonProps extends QueueRowProps {
  theme: string;
}

export interface QueueRowActionProps {
  id: string;
  action: QueueAction;
  theme: string;
  label: string;
  pending: boolean;
  onAction: QueueActionHandler;
  disabled?: boolean;
  variant?: "primary" | "secondary";
  confirmation?: string;
  pendingLabel?: string;
  describedBy?: string;
  reprocess?: GenerationQueueReprocessTarget;
}
