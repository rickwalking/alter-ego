"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";
import { NeonBadge } from "@/components/atoms/neon-badge";
import { DASHBOARD_ROUTES } from "@/constants/dashboard-routes";
import { QUEUE_STATUS } from "@/constants/workflow";
import { NEON_RED, TEXT_MUTED } from "@/constants/neon";
import { useGenerationQueue } from "@/modules/editorial";
import type { QueueBoard } from "@/schemas/generation-queue";

const SUMMARY_CLASS =
  "inline-flex max-w-full items-center gap-2 rounded-full border border-[color:var(--color-neon-cyan-border-30)] px-3 py-1 text-xs font-semibold transition-colors hover:border-neon-cyan/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-neon-cyan focus-visible:ring-offset-2 focus-visible:ring-offset-bg-deep";
const SEGMENT_SEPARATOR = " · ";
const SUMMARY_ARROW = "→";

interface QueueSummarySegment {
  text: string;
  alert: boolean;
}

/** The queue's three segments: running now, waiting, parked. */
export interface QueueSummaryCounts {
  running: number;
  queued: number;
  dead: number;
}

/** Count the queue panel's segments from the loaded board. */
export function queueSummaryCounts(board: QueueBoard): QueueSummaryCounts {
  let running = 0;
  for (const item of board.active) {
    if (item.status === QUEUE_STATUS.RUNNING) running += 1;
  }
  return {
    running,
    queued: board.active.length - running,
    dead: board.dead.length,
  };
}

/**
 * The board's one-line queue summary: a chip linking to the queue page with
 * the live counts ("Fila: 1 gerando · 2 na fila · 1 parada →"). Only the
 * "parada" segment reads red, and only when something is parked. Non-admins
 * get no queue data and no chip.
 */
export function QueueSummaryLink({
  board,
}: Readonly<{ board: QueueBoard | null }>): React.ReactElement | null {
  const t = useTranslations("workflow.queue.summary");
  if (board === null) return null;
  const counts = queueSummaryCounts(board);
  const total = counts.running + counts.queued + counts.dead;
  const segments: QueueSummarySegment[] = [];
  if (counts.running > 0) {
    segments.push({
      text: t("running", { count: counts.running }),
      alert: false,
    });
  }
  if (counts.queued > 0) {
    segments.push({
      text: t("queued", { count: counts.queued }),
      alert: false,
    });
  }
  if (counts.dead > 0) {
    segments.push({ text: t("dead", { count: counts.dead }), alert: true });
  }
  return (
    <Link
      href={DASHBOARD_ROUTES.QUEUE}
      className={SUMMARY_CLASS}
      data-testid="queue-summary-link"
    >
      {total === 0 ? (
        <span>{t("empty")}</span>
      ) : (
        <>
          <span style={{ color: TEXT_MUTED }}>{t("label")}:</span>
          <span className="flex items-center gap-1 whitespace-nowrap">
            {segments.map((segment, index) => (
              <span key={segment.text} className="flex items-center gap-1">
                {index > 0 && (
                  <span aria-hidden="true" style={{ color: TEXT_MUTED }}>
                    {SEGMENT_SEPARATOR}
                  </span>
                )}
                <span style={segment.alert ? { color: NEON_RED } : undefined}>
                  {segment.text}
                </span>
              </span>
            ))}
          </span>
        </>
      )}
      <NeonBadge variant="cyan" size="sm" aria-hidden="true">
        {SUMMARY_ARROW}
      </NeonBadge>
    </Link>
  );
}

/**
 * The board's queue summary wired to the queue API. Rendered only on the
 * active board, so the archived board never polls the queue.
 */
export function QueueSummarySection(): React.ReactElement | null {
  const { board } = useGenerationQueue();
  return <QueueSummaryLink board={board} />;
}
