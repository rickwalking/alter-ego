"use client";

import { useTranslations } from "next-intl";
import { NeonBadge } from "@/components/atoms/neon-badge";
import { NeonButton } from "@/components/atoms/neon-button";
import { NeonCard, NeonCardContent, NeonCardHeader, NeonCardTitle } from "@/components/molecules/neon-card";
import { NeonSpinner } from "@/components/atoms/neon-spinner";
import { useWorkflowKanban } from "@/features/workflow/hooks/use-workflow-kanban";
import Link from "next/link";

function formatPhase(phase: string): string {
  return phase.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export function WorkflowKanbanBoard() {
  const t = useTranslations("workflow");
  const { board, loading, error, refetch } = useWorkflowKanban();

  if (loading) {
    return (
      <div className="flex justify-center py-12">
        <NeonSpinner />
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-8 text-red-500">
        <p>{error}</p>
        <NeonButton
          variant="outline"
          onClick={() => void refetch()}
          className="mt-4"
        >
          {t("kanban.retry")}
        </NeonButton>
      </div>
    );
  }

  if (!board) {
    return null;
  }

  return (
    <div className="overflow-x-auto pb-4 md:overflow-visible">
      <div className="flex flex-col md:flex-row gap-4 md:min-w-max">
        {board.columns.map((column) => (
          <NeonCard key={column.phase} className="w-full md:w-72 shrink-0">
            <NeonCardHeader className="pb-2">
              <NeonCardTitle className="text-sm font-medium flex items-center justify-between">
                {formatPhase(column.phase)}
                <NeonBadge variant="secondary">{column.cards.length}</NeonBadge>
              </NeonCardTitle>
            </NeonCardHeader>
            <NeonCardContent className="space-y-2">
              {column.cards.length === 0 && (
                <p className="text-xs text-muted-foreground">
                  {t("board.noProjects")}
                </p>
              )}
              {column.cards.map((card) => (
                <Link
                  key={card.id}
                  href={`/create/${card.id}`}
                  className="block rounded-md border p-3 hover:bg-muted/50 transition-colors"
                >
                  <p className="font-medium text-sm truncate">{card.title}</p>
                  <p className="text-xs text-muted-foreground truncate">
                    {card.topic}
                  </p>
                  <NeonBadge variant="outline" className="mt-2 text-xs">
                    {card.phase_status}
                  </NeonBadge>
                </Link>
              ))}
            </NeonCardContent>
          </NeonCard>
        ))}
      </div>
    </div>
  );
}
