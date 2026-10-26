"use client";

import { useLocale, useTranslations } from "next-intl";
import { NeonButton } from "@/components/atoms/neon-button";
import { TEXT_MUTED } from "@/constants/neon";
import { QUEUE_ACTION } from "@/constants/workflow";
import { formatQueueDate, QUEUE_ROW_CLASS } from "./queue-row-utils";
import type { BacklogRowProps } from "./types";

/** A backlog theme with its expiry and "Gerar agora". */
export function QueueBacklogRow({
  item,
  pending,
  onAction,
}: Readonly<BacklogRowProps>): React.ReactElement {
  const t = useTranslations("workflow.queue");
  const locale = useLocale();
  return (
    <li className={QUEUE_ROW_CLASS}>
      <div className="min-w-0">
        <p className="text-sm font-medium">{item.title || t("untitled")}</p>
        <p className="text-xs" style={{ color: TEXT_MUTED }}>
          {t("expires", { date: formatQueueDate(locale, item.expires_at) })}
        </p>
      </div>
      <NeonButton
        size="sm"
        disabled={pending === item.candidate_id}
        onClick={() => onAction(QUEUE_ACTION.GENERATE_NOW, item.candidate_id)}
      >
        {t("generateNow")}
      </NeonButton>
    </li>
  );
}
