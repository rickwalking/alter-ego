"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";
import { DASHBOARD_ROUTES } from "@/constants/dashboard-routes";
import { NeonButton } from "@/components/atoms/neon-button";
import { NeonSpinner } from "@/components/atoms/neon-spinner";
import { NeonTopBar } from "@/components/organisms/neon-top-bar";
import { NEON_RED } from "@/constants/neon";
import {
  NeonKanbanBoard,
  mapApiWorkflowKanbanToNeon,
} from "@/modules/editorial-operations";
import { useWorkflowKanban } from "@/modules/editorial";
import { localizeBoardColumns } from "@/app/dashboard/workflow/localize-board";

const NEW_CARD_ICON = (
  <svg
    width="14"
    height="14"
    fill="none"
    stroke="currentColor"
    strokeWidth="2.5"
    viewBox="0 0 24 24"
    aria-hidden="true"
  >
    <path d="M12 5v14" strokeLinecap="round" />
    <path d="M5 12h14" strokeLinecap="round" />
  </svg>
);

const PAGE_FONT_FAMILY = "Inter, system-ui, sans-serif";

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

export default function WorkflowBoardPage(): React.ReactElement {
  const t = useTranslations("workflow");
  const tPhase = useTranslations("create.phases");
  const tStatus = useTranslations("create.status");
  const { board, loading, error, refetch } = useWorkflowKanban();

  return (
    <div
      className="flex-1 text-white relative"
      style={{ fontFamily: PAGE_FONT_FAMILY }}
    >
      <NeonTopBar
        title={t("board.title")}
        breadcrumb={[{ label: t("board.breadcrumb") }]}
        actions={
          <Link href={DASHBOARD_ROUTES.CREATE}>
            <NeonButton size="sm" icon={NEW_CARD_ICON}>
              {t("board.newCard")}
            </NeonButton>
          </Link>
        }
      />
      <div className="p-6">
        {loading && (
          <div className="flex justify-center py-12">
            <NeonSpinner size="lg" />
          </div>
        )}
        {error && !loading && (
          <div className="text-center py-8">
            <p style={{ color: NEON_RED }}>{error}</p>
            <NeonButton
              variant="secondary"
              onClick={() => void refetch()}
              className="mt-4"
            >
              {t("kanban.retry")}
            </NeonButton>
          </div>
        )}
        {board && (
          <NeonKanbanBoard
            columns={localizeBoardColumns(mapApiWorkflowKanbanToNeon(board), {
              phase: tPhase,
              status: tStatus,
              knownPhases: BOARD_PHASES,
              rejectedColumn: t("board.rejectedColumn"),
            })}
          />
        )}
      </div>
    </div>
  );
}
