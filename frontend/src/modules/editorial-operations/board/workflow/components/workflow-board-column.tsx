"use client";

import Link from "next/link";
import { NeonBadge } from "@/components/atoms/neon-badge";
import { NeonCard } from "@/components/molecules/neon-card";
import { DASHBOARD_ROUTES } from "@/constants/dashboard-routes";
import { TEXT, TEXT_DIM, TEXT_MUTED } from "@/constants/neon";
import type { WorkflowBoardColumnProps } from "./types";

const COLUMN_TEST_ID_PREFIX = "workflow-column-";
const RAIL_WIDTH_CLASS = "w-11 shrink-0";
const RAIL_LABEL_CLASS = "[writing-mode:vertical-rl] rotate-180";
const FOCUS_RING_CLASS =
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-neon-cyan focus-visible:ring-offset-2 focus-visible:ring-offset-bg-deep";
const COLUMN_WIDTH_CLASS = "min-w-[232px] max-w-[320px] flex-1 basis-0";

/** One expanded workflow column or its compact vertical rail. */
export function WorkflowBoardColumn({
  column,
  collapsed,
  labels,
  onToggle,
  onCardClick,
  setColumnRef,
  renderCardActions,
}: Readonly<WorkflowBoardColumnProps>): React.ReactElement {
  const key = column.phase;
  const count = column.count ?? column.cards.length;
  if (collapsed) {
    const railLabel = labels.expandColumn(column.status, count);
    return (
      <button
        type="button"
        title={railLabel}
        aria-label={railLabel}
        onClick={() => onToggle(key)}
        className={`flex flex-col items-center gap-2 rounded-md border border-transparent py-2 text-white transition-colors hover:border-neon-cyan/40 ${RAIL_WIDTH_CLASS} ${FOCUS_RING_CLASS}`}
      >
        <NeonBadge variant="cyan" size="sm">
          {count}
        </NeonBadge>
        <span
          className={`text-xs font-semibold uppercase tracking-wide ${RAIL_LABEL_CLASS}`}
          style={{ color: TEXT_DIM }}
        >
          {column.status}
        </span>
      </button>
    );
  }
  const headerId = `board-column-${key}`;
  return (
    <section
      aria-labelledby={headerId}
      className={`flex min-h-0 flex-col ${COLUMN_WIDTH_CLASS}`}
    >
      <div className="sticky top-0 z-10 mb-3 flex shrink-0 items-center justify-between bg-bg-deep px-1">
        <h3 id={headerId} className="text-sm font-bold" style={{ color: TEXT }}>
          {column.status}
        </h3>
        <NeonBadge variant="cyan" size="sm">
          {count}
        </NeonBadge>
      </div>
      <div
        ref={(element) => setColumnRef(key, element)}
        data-testid={`${COLUMN_TEST_ID_PREFIX}${key}`}
        role="list"
        className="min-h-0 flex-1 space-y-3 overflow-y-auto pr-0.5"
      >
        {column.cards.length === 0 && (
          <p className="px-1 py-4 text-xs" style={{ color: TEXT_MUTED }}>
            {labels.emptyColumn}
          </p>
        )}
        {column.cards.map((card) => (
          <div key={card.id} role="listitem" className="space-y-1">
            <Link
              href={DASHBOARD_ROUTES.CREATE_WORKSPACE(card.id)}
              onClick={() => onCardClick(column)}
              className="block no-underline"
            >
              <NeonCard padding="sm" hover>
                <p
                  className="mb-1 text-sm font-semibold"
                  style={{ color: TEXT }}
                >
                  {card.title}
                </p>
                <p
                  className="mb-2 line-clamp-2 text-xs"
                  style={{ color: TEXT_MUTED }}
                >
                  {card.description}
                </p>
                <div className="flex items-center justify-between">
                  <NeonBadge variant="teal" size="sm">
                    {card.phaseStatus}
                  </NeonBadge>
                  {card.assignee && (
                    <span
                      className="text-[10px]"
                      style={{
                        fontFamily: "'JetBrains Mono', ui-monospace, monospace",
                        color: TEXT_DIM,
                      }}
                    >
                      {card.assignee}
                    </span>
                  )}
                </div>
              </NeonCard>
            </Link>
            {renderCardActions?.(card)}
          </div>
        ))}
      </div>
    </section>
  );
}
