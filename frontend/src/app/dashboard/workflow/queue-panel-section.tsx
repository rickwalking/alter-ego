"use client";

import { useGenerationQueue } from "@/modules/editorial";
import { QueuePanel } from "./queue-panel";

/** The queue panel wired to the generation queue API (polls like the board). */
export function QueuePanelSection(): React.ReactElement | null {
  const { board, error, pending, actionError, act } = useGenerationQueue();
  return (
    <QueuePanel
      board={board}
      error={error}
      pending={pending}
      actionError={actionError}
      onAction={(action, id) => void act(action, id)}
    />
  );
}
