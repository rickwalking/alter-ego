"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";
import { useSearchParams } from "next/navigation";
import { NeonTopBar } from "@/components/organisms/neon-top-bar";
import { neonButtonVariants } from "@/components/atoms/neon-button";
import { DASHBOARD_ROUTES } from "@/constants/dashboard-routes";
import { WORKFLOW_BOARD_ARCHIVED_PARAM } from "@/constants/workflow";
import { WorkflowBoardView } from "./workflow-board-view";
import { WorkflowViewSwitch } from "./workflow-view-switch";

const NEW_CAROUSEL_ICON = (
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

/**
 * The board top bar plus the board itself. The active/archived view comes
 * from the URL (`?archived=1`), so Back from a carousel restores it; in the
 * archive the top bar title reads "Arquivados". The "New carousel" action is
 * a single link styled as a button, not a button nested in a link.
 */
export function WorkflowBoardChrome(): React.ReactElement {
  const t = useTranslations("workflow");
  const searchParams = useSearchParams();
  const archived = searchParams.get(WORKFLOW_BOARD_ARCHIVED_PARAM) === "1";

  return (
    <>
      <NeonTopBar
        title={archived ? t("archive.showArchived") : t("board.title")}
        breadcrumb={[{ label: t("board.breadcrumb") }]}
        actions={
          <div className="flex items-center gap-2">
            <WorkflowViewSwitch archived={archived} />
            <Link
              href={DASHBOARD_ROUTES.CREATE}
              className={neonButtonVariants({ size: "sm" })}
            >
              <span aria-hidden="true">{NEW_CAROUSEL_ICON}</span>
              {t("board.newCard")}
            </Link>
          </div>
        }
      />
      <WorkflowBoardView key={String(archived)} archived={archived} />
    </>
  );
}
