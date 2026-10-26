"use client";

import { useLocale, useTranslations } from "next-intl";
import { TEXT_MUTED } from "@/constants/neon";
import { QUEUE_ACTION } from "@/constants/workflow";
import { firstNonBlank } from "@/lib/utils";
import { QueueRowAction } from "./queue-row-action";
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
  const theme = firstNonBlank([item.title, t("untitled")]);
  return (
    <li className={QUEUE_ROW_CLASS}>
      <div className="min-w-0">
        <p className="text-sm font-medium">{theme}</p>
        <p className="text-xs" style={{ color: TEXT_MUTED }}>
          {t("expires", { date: formatQueueDate(locale, item.expires_at) })}
        </p>
      </div>
      <QueueRowAction
        id={item.candidate_id}
        action={QUEUE_ACTION.GENERATE_NOW}
        theme={theme}
        label={t("generateNow")}
        variant="primary"
        pending={pending === item.candidate_id}
        onAction={onAction}
      />
    </li>
  );
}
