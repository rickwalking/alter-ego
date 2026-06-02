import Link from "next/link";
import { NeonBadge } from "@/components/atoms/neon-badge";
import { NeonCard } from "@/components/molecules/neon-card";
import { DASHBOARD_ROUTES } from "@/constants/dashboard-routes";
import { TEXT, TEXT_DIM, TEXT_MUTED } from "@/constants/neon";
import type { KanbanColumn } from "@/schemas/neon-kanban";

export interface NeonKanbanBoardProps {
  columns: KanbanColumn[];
}

export function NeonKanbanBoard({
  columns,
}: NeonKanbanBoardProps): React.ReactElement {
  return (
    <div
      className="flex gap-4 overflow-x-auto pb-4"
      style={{ minHeight: "calc(100vh - 120px)" }}
    >
      {columns.map((column) => (
        <div
          key={`${column.phase}-${column.status}`}
          className="flex flex-col shrink-0"
          style={{ width: "280px" }}
        >
          <div className="flex items-center justify-between mb-3 px-1">
            <h3 className="text-sm font-bold" style={{ color: TEXT }}>
              {column.status}
            </h3>
            <NeonBadge variant="cyan" size="sm">
              {column.count ?? column.cards.length}
            </NeonBadge>
          </div>
          <div className="space-y-3 flex-1">
            {column.cards.map((card) => (
              <Link
                key={card.id}
                href={DASHBOARD_ROUTES.CREATE_WORKSPACE(card.id)}
                className="block no-underline"
              >
                <NeonCard padding="sm" hover>
                  <p
                    className="text-sm font-semibold mb-1"
                    style={{ color: TEXT }}
                  >
                    {card.title}
                  </p>
                  <p
                    className="text-xs line-clamp-2 mb-2"
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
                          fontFamily:
                            "'JetBrains Mono', ui-monospace, monospace",
                          color: TEXT_DIM,
                        }}
                      >
                        {card.assignee}
                      </span>
                    )}
                  </div>
                </NeonCard>
              </Link>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
