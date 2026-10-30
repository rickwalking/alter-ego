"use client";

import { useTranslations } from "next-intl";
import { useGenerationQueue } from "@/modules/editorial";
import { QueuePanel } from "./queue-panel";

/** The queue panel wired to the generation queue API (polls like the board). */
export function QueuePanelSection(): React.ReactElement | null {
  const t = useTranslations("workflow.queue");
  const {
    board,
    error,
    forbidden,
    pending,
    actionError,
    processPending,
    processError,
    act,
    processQueue,
  } = useGenerationQueue();
  if (forbidden) {
    return <p className="py-8 text-center text-sm">{t("adminsOnly")}</p>;
  }
  return (
    <QueuePanel
      board={board}
      error={error}
      pending={pending}
      actionError={actionError}
      processPending={processPending}
      processError={processError}
      onAction={(action, id, reprocess) => void act(action, id, reprocess)}
      onProcess={() => void processQueue()}
    />
  );
}
