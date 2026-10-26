"use client";

import { useId } from "react";
import { useTranslations } from "next-intl";
import { TEXT_MUTED } from "@/constants/neon";
import {
  QUEUE_ACTION,
  REPROCESS_REFUSAL,
  REPROCESS_REFUSAL_CODES,
} from "@/constants/workflow";
import type { GenerationQueueReprocessTarget } from "@/modules/editorial";
import type { QueueItem } from "@/schemas/generation-queue";
import { QueueRowAction } from "./queue-row-action";
import type { QueueReprocessButtonProps } from "./types";

function canTarget(item: QueueItem): boolean {
  if (!item.can_reprocess || item.stuck_kind === null) return false;
  if (item.staged) return true;
  return (
    item.autopilot_run_id !== null &&
    item.project_id !== null &&
    item.lock_version !== null
  );
}

function reprocessTarget(
  item: QueueItem,
): GenerationQueueReprocessTarget | undefined {
  if (!item.staged) {
    if (item.project_id === null || item.lock_version === null)
      return undefined;
    return {
      projectId: item.project_id,
      expectedVersion: item.lock_version,
    };
  }
  if (item.lock_version === null) return undefined;
  return { expectedVersion: item.lock_version };
}

function refusalReason(
  item: QueueItem,
  translate: (key: string) => string,
): string {
  if (item.can_reprocess && item.refusal_code === null) {
    return translate("errors.unavailable");
  }
  if (
    item.refusal_code !== null &&
    REPROCESS_REFUSAL_CODES.has(item.refusal_code)
  ) {
    return translate(`refusals.${item.refusal_code}`);
  }
  return translate(`refusals.${REPROCESS_REFUSAL.UNSUPPORTED}`);
}

/** Reprocess from the backend capability and its staged or project-safe target. */
export function QueueReprocessButton({
  item,
  pending,
  onAction,
  theme,
}: Readonly<QueueReprocessButtonProps>): React.ReactElement {
  const t = useTranslations("workflow.reprocess");
  const reasonId = useId();
  const busy = pending === item.id;
  const available = canTarget(item);
  let reason: string | null = null;
  if (busy) reason = t("pendingReason");
  if (!busy && !available) reason = refusalReason(item, t);
  return (
    <span className="flex max-w-64 flex-col items-start gap-1">
      <QueueRowAction
        id={item.id}
        action={QUEUE_ACTION.REPROCESS}
        theme={theme}
        label={t("action")}
        pendingLabel={t("pending")}
        pending={busy}
        disabled={!available}
        describedBy={reason ? reasonId : undefined}
        reprocess={reprocessTarget(item)}
        onAction={onAction}
      />
      {reason && (
        <span id={reasonId} className="text-xs" style={{ color: TEXT_MUTED }}>
          {reason}
        </span>
      )}
    </span>
  );
}
