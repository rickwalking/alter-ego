"use client";

import { useTranslations } from "next-intl";
import { NEON_RED, TEXT_MUTED } from "@/constants/neon";
import type { QueueBoard } from "@/schemas/generation-queue";
import {
  QueueActiveRow,
  QueueBacklogRow,
  QueueDeadRow,
} from "./queue-panel-rows";
import type { QueuePanelProps } from "./types";

const MINUTES_DIGITS = 0;

/** True when the queue, the parked runs and the backlog are all empty. */
function isEmpty(board: QueueBoard): boolean {
  return (
    board.active.length === 0 &&
    board.dead.length === 0 &&
    board.backlog.length === 0
  );
}

/**
 * The generation queue: one carousel at a time in arrival order (running first),
 * the runs the queue parked with "Tentar de novo" / "Descartar", and the backlog
 * themes with "Gerar agora". Data and buttons come from the caller.
 */
export function QueuePanel({
  board,
  error,
  pending,
  actionError,
  onAction,
}: Readonly<QueuePanelProps>): React.ReactElement | null {
  const t = useTranslations("workflow.queue");
  if (!board) {
    return error ? (
      <p role="alert" className="text-sm" style={{ color: NEON_RED }}>
        {error}
      </p>
    ) : null;
  }
  return (
    <section aria-labelledby="queue-panel-title" className="mb-6 space-y-3">
      <div>
        <h2 id="queue-panel-title" className="text-base font-semibold">
          {t("title")}
        </h2>
        <p className="text-xs" style={{ color: TEXT_MUTED }}>
          {t("subtitle", {
            minutes: board.average_drive_minutes.toFixed(MINUTES_DIGITS),
          })}
        </p>
      </div>
      {actionError && (
        <p role="alert" className="text-xs" style={{ color: NEON_RED }}>
          {actionError}
        </p>
      )}
      {isEmpty(board) && (
        <p className="text-sm" style={{ color: TEXT_MUTED }}>
          {t("empty")}
        </p>
      )}
      {board.active.length > 0 && (
        <div>
          <h3 className="mb-1 text-sm font-medium">{t("active")}</h3>
          <ol className="space-y-2">
            {board.active.map((item) => (
              <QueueActiveRow
                key={item.id}
                item={item}
                pending={pending}
                onAction={onAction}
              />
            ))}
          </ol>
        </div>
      )}
      {board.dead.length > 0 && (
        <div>
          <h3 className="mb-1 text-sm font-medium">{t("dead")}</h3>
          <ul className="space-y-2">
            {board.dead.map((item) => (
              <QueueDeadRow
                key={item.id}
                item={item}
                pending={pending}
                onAction={onAction}
              />
            ))}
          </ul>
        </div>
      )}
      {board.backlog.length > 0 && (
        <div>
          <h3 className="mb-1 text-sm font-medium">{t("backlog")}</h3>
          <ul className="space-y-2">
            {board.backlog.map((item) => (
              <QueueBacklogRow
                key={item.candidate_id}
                item={item}
                pending={pending}
                onAction={onAction}
              />
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
