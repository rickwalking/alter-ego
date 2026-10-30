"use client";

import { useLocale, useTranslations } from "next-intl";
import { NeonButton } from "@/components/atoms/neon-button";
import { NeonSpinner } from "@/components/atoms/neon-spinner";
import { NEON_RED } from "@/constants/neon";
import {
  NeonKanbanBoard,
  mapApiWorkflowKanbanToNeon,
} from "@/modules/editorial-operations";
import { useWorkflowKanban, type WorkflowKanban } from "@/modules/editorial";
import { localizeBoardColumns } from "@/app/dashboard/workflow/localize-board";
import {
  countBoardStatusBuckets,
  filterBoardColumns,
} from "@/app/dashboard/workflow/board-filters";
import { useBoardFilters } from "@/app/dashboard/workflow/use-board-filters";
import { WorkflowToolbar } from "@/app/dashboard/workflow/workflow-toolbar";
import { CardArchiveAction } from "./card-archive-action";
import { QueueSummarySection } from "./queue-summary-link";
import type { BoardFeedbackProps, WorkflowBoardViewProps } from "./types";

/** Phase ids with a `create.phases` name (board columns). */
const BOARD_PHASES: ReadonlySet<string> = new Set([
  "brief",
  "research",
  "outline",
  "content",
  "design",
  "images",
  "final_review",
  "published",
]);

/** The first-load spinner, and a failed load with retry. */
function BoardFeedback({
  loading,
  error,
  onRetry,
}: Readonly<BoardFeedbackProps>): React.ReactElement | null {
  const t = useTranslations("workflow");
  if (loading) {
    return (
      <div className="flex justify-center py-12">
        <NeonSpinner size="lg" />
      </div>
    );
  }
  if (!error) return null;
  return (
    <div className="text-center py-8">
      <p style={{ color: NEON_RED }}>{error}</p>
      <NeonButton variant="secondary" onClick={onRetry} className="mt-4">
        {t("kanban.retry")}
      </NeonButton>
    </div>
  );
}

/** True when the board has no card in any column. */
function isEmptyBoard(board: WorkflowKanban): boolean {
  return board.columns.every((column) => column.cards.length === 0);
}

/** The active or the archived board, with the archive control on each card. */
export function WorkflowBoardView({
  archived,
}: Readonly<WorkflowBoardViewProps>): React.ReactElement {
  const t = useTranslations("workflow");
  const tPhase = useTranslations("create.phases");
  const tStatus = useTranslations("create.status");
  const locale = useLocale();
  const { filters, setFilters } = useBoardFilters();
  const { board, loading, error, refetch } = useWorkflowKanban(archived);
  const refresh = (): void => void refetch();
  const showEmpty = archived && board !== null && isEmptyBoard(board);
  const localizedColumns =
    board === null
      ? []
      : localizeBoardColumns(mapApiWorkflowKanbanToNeon(board), {
          phase: tPhase,
          status: tStatus,
          knownPhases: BOARD_PHASES,
          rejectedColumn: t("board.rejectedColumn"),
          untitled: t("queue.untitled"),
        });
  const visibleColumns = filterBoardColumns(localizedColumns, filters, locale);
  const counts = countBoardStatusBuckets(localizedColumns);

  return (
    <div
      data-testid="workflow-board-view"
      className="flex h-[calc(100dvh-3.5rem)] flex-col gap-4 overflow-hidden p-6"
    >
      {!archived && <QueueSummarySection />}
      <div className="shrink-0">
        <WorkflowToolbar
          filters={filters}
          counts={counts}
          onChange={setFilters}
        />
      </div>
      <BoardFeedback loading={loading} error={error} onRetry={refresh} />
      {showEmpty && (
        <p className="py-8 text-center text-sm">{t("archive.emptyArchived")}</p>
      )}
      {board && !showEmpty && (
        <div className="min-h-0 flex-1">
          <NeonKanbanBoard
            columns={visibleColumns}
            labels={{
              emptyColumn: t("board.noProjects"),
              expandColumn: (name: string, count: number) =>
                t("board.expandColumn", { name, count }),
              collapseColumn: (name: string) =>
                t("board.collapseColumn", { name }),
              needYou: (count: number) => t("board.needYou", { count }),
              columnCount: (count: number) => t("board.columnCount", { count }),
            }}
            viewKey={archived ? "archived" : "active"}
            renderCardActions={(card, tabbable) => (
              <CardArchiveAction
                card={card}
                archived={archived}
                onChanged={refresh}
                tabbable={tabbable}
              />
            )}
          />
        </div>
      )}
    </div>
  );
}
