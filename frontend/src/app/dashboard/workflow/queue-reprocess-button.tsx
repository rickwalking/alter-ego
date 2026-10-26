"use client";

import { useTranslations } from "next-intl";
import { NeonButton } from "@/components/atoms/neon-button";
import { TEXT_MUTED } from "@/constants/neon";
import {
  QUEUE_ACTION,
  QUEUE_STATUS,
  REPROCESS_REFUSAL,
} from "@/constants/workflow";
import type { QueueRowProps } from "./types";

const REPROCESSABLE_STATUSES: ReadonlySet<string> = new Set([
  QUEUE_STATUS.DEAD_LETTER,
  QUEUE_STATUS.RETRY_WAIT,
]);
const ROW_REFUSAL_BY_STATUS: Readonly<Record<string, string>> = {
  [QUEUE_STATUS.QUEUED]: REPROCESS_REFUSAL.NORMAL_QUEUED,
  [QUEUE_STATUS.RUNNING]: REPROCESS_REFUSAL.FRESH_RUNNING,
};

/** Reprocess only an existing dead-letter or retry-wait generation row. */
export function QueueReprocessButton({
  item,
  pending,
  onAction,
}: Readonly<QueueRowProps>): React.ReactElement {
  const t = useTranslations("workflow.reprocess");
  const applicable = REPROCESSABLE_STATUSES.has(item.status);
  const busy = pending === item.id;
  const refusal =
    ROW_REFUSAL_BY_STATUS[item.status] ?? REPROCESS_REFUSAL.UNSUPPORTED;
  let reason: string | null = null;
  if (busy) reason = t("pendingReason");
  if (!busy && !applicable) reason = t(`refusals.${refusal}`);
  const reasonId = `queue-reprocess-reason-${item.id}`;
  return (
    <span className="flex max-w-64 flex-col items-start gap-1">
      <NeonButton
        size="sm"
        variant="secondary"
        aria-label={t("action")}
        aria-describedby={reason ? reasonId : undefined}
        loading={busy}
        disabled={!applicable}
        onClick={() => onAction(QUEUE_ACTION.REPROCESS, item.id)}
      >
        {busy ? t("pending") : t("action")}
      </NeonButton>
      {reason && (
        <span id={reasonId} className="text-xs" style={{ color: TEXT_MUTED }}>
          {reason}
        </span>
      )}
    </span>
  );
}
