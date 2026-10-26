"use client";

import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";
import { NeonButton } from "@/components/atoms/neon-button";
import { DASHBOARD_ROUTES } from "@/constants/dashboard-routes";
import { TEXT_DIM, TEXT_MUTED } from "@/constants/neon";
import { QUEUE_ACTION, QUEUE_STATUS } from "@/constants/workflow";
import { QueueReprocessButton } from "./queue-reprocess-button";
import { formatQueueTime, QUEUE_ROW_CLASS } from "./queue-row-utils";
import type { QueueRowProps } from "./types";

const KNOWN_KINDS: ReadonlySet<string> = new Set(["autopilot", "dashboard"]);
const KNOWN_PHASES: ReadonlySet<string> = new Set([
  "brief",
  "research",
  "outline",
  "content",
  "design",
  "images",
  "final_review",
  "published",
]);
const KNOWN_REASONS: ReadonlySet<string> = new Set([
  "transient",
  "permanent",
  "phase_budget_exhausted",
  "run_budget_exhausted",
  "held_by_queue",
]);
/** The line under an active run: status, phase and start estimate. */
function ActiveDetail({
  item,
}: Readonly<Pick<QueueRowProps, "item">>): React.ReactElement {
  const t = useTranslations("workflow.queue");
  const tPhase = useTranslations("create.phases");
  const locale = useLocale();
  const parts: string[] = [];
  if (item.status === QUEUE_STATUS.RUNNING) parts.push(t("status.running"));
  if (item.status === QUEUE_STATUS.QUEUED) parts.push(t("status.queued"));
  if (item.status === QUEUE_STATUS.RETRY_WAIT && item.next_attempt_at) {
    parts.push(
      t("status.retryWait", {
        time: formatQueueTime(locale, item.next_attempt_at),
      }),
    );
  }
  if (item.phase) {
    const phase = KNOWN_PHASES.has(item.phase)
      ? tPhase(item.phase)
      : item.phase;
    parts.push(t("phase", { phase }));
  }
  if (item.eta) {
    parts.push(t("eta", { time: formatQueueTime(locale, item.eta) }));
  }
  return (
    <p className="text-xs" style={{ color: TEXT_MUTED }}>
      {parts.join(" · ")}
    </p>
  );
}

/** A queued, running or retry-waiting run, with "Cancelar" when it has not started. */
export function QueueActiveRow({
  item,
  pending,
  onAction,
}: Readonly<QueueRowProps>): React.ReactElement {
  const t = useTranslations("workflow.queue");
  return (
    <li className={QUEUE_ROW_CLASS}>
      <div className="min-w-0">
        <p className="text-sm font-medium">
          <span style={{ color: TEXT_DIM }}>
            {t("position", { position: item.position ?? 0 })}
          </span>{" "}
          {item.title || t("untitled")}{" "}
          {KNOWN_KINDS.has(item.kind) && (
            <span className="text-xs" style={{ color: TEXT_DIM }}>
              {t(`kind.${item.kind}`)}
            </span>
          )}
        </p>
        <ActiveDetail item={item} />
      </div>
      <div className="flex flex-wrap gap-2">
        <QueueReprocessButton
          item={item}
          pending={pending}
          onAction={onAction}
        />
        {item.can_cancel && (
          <NeonButton
            size="sm"
            variant="secondary"
            disabled={pending === item.id}
            onClick={() => onAction(QUEUE_ACTION.CANCEL, item.id)}
          >
            {t("cancel")}
          </NeonButton>
        )}
      </div>
    </li>
  );
}

/** A run the queue parked: the reason, and the buttons or the editor link. */
export function QueueDeadRow({
  item,
  pending,
  onAction,
}: Readonly<QueueRowProps>): React.ReactElement {
  const t = useTranslations("workflow.queue");
  const code = item.error_code ?? "";
  const reason = KNOWN_REASONS.has(code)
    ? t(`reason.${code}`)
    : t("reason.other", { code });
  const busy = pending === item.id;
  return (
    <li className={QUEUE_ROW_CLASS}>
      <div className="min-w-0">
        <p className="text-sm font-medium">{item.title || t("untitled")}</p>
        <p className="text-xs" style={{ color: TEXT_MUTED }}>
          {reason}
        </p>
      </div>
      <div className="flex flex-wrap gap-2">
        <QueueReprocessButton
          item={item}
          pending={pending}
          onAction={onAction}
        />
        {item.can_retry && (
          <NeonButton
            size="sm"
            disabled={busy}
            onClick={() => onAction(QUEUE_ACTION.RETRY, item.id)}
          >
            {t("retry")}
          </NeonButton>
        )}
        {item.can_discard && (
          <NeonButton
            size="sm"
            variant="secondary"
            disabled={busy}
            onClick={() => onAction(QUEUE_ACTION.DISCARD, item.id)}
          >
            {t("discard")}
          </NeonButton>
        )}
        {!item.can_retry && item.project_id && (
          <Link
            className="text-xs underline"
            href={DASHBOARD_ROUTES.CREATE_WORKSPACE(item.project_id)}
          >
            {t("openEditor")}
          </Link>
        )}
      </div>
    </li>
  );
}
