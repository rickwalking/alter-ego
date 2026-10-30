"use client";

import { Suspense } from "react";
import { NeonSpinner } from "@/components/atoms/neon-spinner";
import { DASHBOARD_PAGE_FONT_FAMILY } from "@/constants/dashboard-page";
import { WorkflowBoardChrome } from "./workflow-board-chrome";

/**
 * The board view state lives in the URL (`?archived=1` and the toolbar
 * filters via `useSearchParams`), which needs a Suspense boundary for the
 * static prerender of this route.
 */
export default function WorkflowBoardPage(): React.ReactElement {
  return (
    <div
      className="flex-1 text-white relative"
      style={{ fontFamily: DASHBOARD_PAGE_FONT_FAMILY }}
    >
      <Suspense fallback={<NeonSpinner size="lg" />}>
        <WorkflowBoardChrome />
      </Suspense>
    </div>
  );
}
