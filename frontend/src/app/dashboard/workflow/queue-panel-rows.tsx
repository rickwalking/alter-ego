"use client";

import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";
import { DASHBOARD_ROUTES } from "@/constants/dashboard-routes";
import { TEXT_DIM, TEXT_MUTED } from "@/constants/neon";
import { QUEUE_ACTION, QUEUE_STATUS } from "@/constants/workflow";
import { formatLocaleRelative } from "@/lib/locale-format";
import { firstNonBlank } from "@/lib/utils";
import { QueueReprocessButton } from "./queue-reprocess-button";
import { QueueRowAction } from "./queue-row-action";
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
function useRunningDetailParts(
  item: QueueRowProps["item"],
  locale: string,
): string[] {
  const t = useTranslations("workflow.queue");
  if (item.status !== QUEUE_STATUS.RUNNING) return [];
  const parts = [t("status.running")];
  if (item.started_at) {
    parts.push(
      t("startedAt", { time: formatQueueTime(locale, item.started_at) }),
    );
  }
  if (item.run_heartbeat_at) {
    const age = formatLocaleRelative(item.run_heartbeat_at, locale);
    if (age) parts.push(t("heartbeatAge", { age }));
  }
  return parts;
}

/** The line under an active run: status, phase and start estimate. */
function ActiveDetail({
  item,
}: Readonly<Pick<QueueRowProps, "item">>): React.ReactElement {
  const t = useTranslations("workflow.queue");
  const tPhase = useTranslations("create.phases");
  const locale = useLocale();
  const parts = useRunningDetailParts(item, locale);
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

/** A queued, running or retry-waiting run with its capability-driven actions. */
export function QueueActiveRow({
  item,
  pending,
  onAction,
}: Readonly<QueueRowProps>): React.ReactElement {
  const t = useTranslations("workflow.queue");
  const theme = firstNonBlank([item.title, t("untitled")]);
  return (
    <li className={QUEUE_ROW_CLASS}>
      <div className="min-w-0">
        <p className="text-sm font-medium">
          {item.position !== null && (
            <>
              <span style={{ color: TEXT_DIM }}>
                {t("position", { position: item.position })}
              </span>{" "}
            </>
          )}
          {theme}{" "}
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
          theme={theme}
        />
        {item.staged && item.can_cancel && (
          <QueueRowAction
            id={item.id}
            action={QUEUE_ACTION.CANCEL}
            theme={theme}
            label={t("cancel")}
            pending={pending.has(item.id)}
            confirmation={t("confirmCancel", { theme })}
            onAction={onAction}
          />
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
  const theme = firstNonBlank([item.title, t("untitled")]);
  return (
    <li className={QUEUE_ROW_CLASS}>
      <div className="min-w-0">
        <p className="text-sm font-medium">{theme}</p>
        <p className="text-xs" style={{ color: TEXT_MUTED }}>
          {reason}
        </p>
      </div>
      <div className="flex flex-wrap gap-2">
        <QueueReprocessButton
          item={item}
          pending={pending}
          onAction={onAction}
          theme={theme}
        />
        {item.staged && item.can_retry && (
          <QueueRowAction
            id={item.id}
            action={QUEUE_ACTION.RETRY}
            theme={theme}
            label={t("retry")}
            variant="primary"
            pending={pending.has(item.id)}
            onAction={onAction}
          />
        )}
        {item.staged && item.can_discard && (
          <QueueRowAction
            id={item.id}
            action={QUEUE_ACTION.DISCARD}
            theme={theme}
            label={t("discard")}
            pending={pending.has(item.id)}
            confirmation={t("confirmDiscard", { theme })}
            onAction={onAction}
          />
        )}
        {!item.can_retry && item.project_id && (
          <Link
            className="text-xs underline"
            aria-label={t("actionForTheme", {
              action: t("openEditor"),
              theme,
            })}
            href={DASHBOARD_ROUTES.CREATE_WORKSPACE(item.project_id)}
          >
            {t("openEditor")}
          </Link>
        )}
      </div>
    </li>
  );
}
