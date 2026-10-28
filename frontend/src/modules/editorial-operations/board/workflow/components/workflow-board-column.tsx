"use client";

import Link from "next/link";
import { useLocale } from "next-intl";
import { NeonBadge } from "@/components/atoms/neon-badge";
import { NeonCard } from "@/components/molecules/neon-card";
import { DASHBOARD_ROUTES } from "@/constants/dashboard-routes";
import { TEXT, TEXT_DIM, TEXT_MUTED } from "@/constants/neon";
import { WORKFLOW_PHASE_STATUS } from "@/constants/workflow";
import { formatLocaleRelative } from "@/lib/locale-format";
import { WORKFLOW_BOARD_PHASE_PUBLISHED } from "../constants";
import type { KanbanCard } from "@/schemas/neon-kanban";
import type { WorkflowBoardColumnProps } from "./types";

const COLUMN_TEST_ID_PREFIX = "workflow-column-";
const RAIL_WIDTH_CLASS = "w-11 shrink-0";
const RAIL_LABEL_CLASS = "[writing-mode:vertical-rl] rotate-180";
const FOCUS_RING_CLASS =
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-neon-cyan focus-visible:ring-offset-2 focus-visible:ring-offset-bg-deep";
const COLUMN_WIDTH_CLASS = "min-w-[232px] max-w-[320px] flex-1 basis-0";
const HEADER_ACTION_CLASS = `rounded p-1 text-xs font-semibold transition-colors hover:text-white ${FOCUS_RING_CLASS}`;

function countAwaitingOwner(cards: readonly KanbanCard[]): number {
  return cards.filter(
    (card) => card.statusKey === WORKFLOW_PHASE_STATUS.AWAITING_HUMAN,
  ).length;
}

/**
 * The published column's badge would only repeat the column header, so the
 * card shows the relative updated time instead.
 */
function CardStatus({
  card,
  locale,
}: Readonly<{ card: KanbanCard; locale: string }>): React.ReactElement {
  if (card.phase === WORKFLOW_BOARD_PHASE_PUBLISHED) {
    return (
      <span
        className="text-[11px]"
        style={{ color: TEXT_MUTED }}
        data-testid="published-updated"
      >
        {card.updatedAt ? formatLocaleRelative(card.updatedAt, locale) : ""}
      </span>
    );
  }
  return (
    <NeonBadge
      variant={card.statusVariant ?? "teal"}
      pulse={card.statusPulse}
      size="sm"
    >
      {card.phaseStatus}
    </NeonBadge>
  );
}

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
  const locale = useLocale();
  const key = column.phase;
  const count = column.count ?? column.cards.length;
  if (collapsed) {
    const railLabel = labels.expandColumn(column.status, count);
    return (
      <button
        type="button"
        title={railLabel}
        aria-label={railLabel}
        aria-expanded={false}
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
  const needYou = countAwaitingOwner(column.cards);
  return (
    <section
      aria-labelledby={headerId}
      className={`flex min-h-0 flex-col ${COLUMN_WIDTH_CLASS}`}
    >
      <div className="mb-3 flex shrink-0 items-center justify-between bg-bg-deep px-1">
        <h3 id={headerId} className="text-sm font-bold" style={{ color: TEXT }}>
          {column.status}
          {needYou > 0 && labels.needYou && (
            <span
              className="ml-2 text-xs font-semibold"
              style={{ color: TEXT_MUTED }}
              data-testid="column-need-you"
            >
              {labels.needYou(needYou)}
            </span>
          )}
        </h3>
        <div className="flex items-center gap-1">
          <NeonBadge variant="cyan" size="sm">
            {count}
          </NeonBadge>
          <button
            type="button"
            aria-label={labels.collapseColumn(column.status)}
            aria-expanded={true}
            onClick={() => onToggle(key)}
            className={HEADER_ACTION_CLASS}
            style={{ color: TEXT_DIM }}
            data-testid={`collapse-column-${key}`}
          >
            ⟨
          </button>
        </div>
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
              aria-label={`${card.title}, ${card.phaseStatus}`}
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
                  <CardStatus card={card} locale={locale} />
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
