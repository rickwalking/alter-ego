"use client";

import { NeonButton } from "@/components/atoms/neon-button";
import { NeonKanbanBoard } from "@/components/organisms/neon-kanban-board";
import { NeonTopBar } from "@/components/organisms/neon-top-bar";
import { WORKFLOW_COLUMNS } from "@/features/dashboard/workflow/constants";
import { mapWorkflowColumnDataToKanban } from "@/features/dashboard/workflow/adapters/workflow-adapter";

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

export default function WorkflowBoardPage(): React.ReactElement {
  return (
    <div
      className="flex-1 text-white relative"
      style={{ fontFamily: "Inter, system-ui, sans-serif" }}
    >
      <NeonTopBar
        title="Workflow Board"
        breadcrumb={[{ label: "pipeline" }]}
        actions={
          <NeonButton size="sm" icon={NEW_CARD_ICON}>
            New Card
          </NeonButton>
        }
      />
      <div className="p-6">
        <NeonKanbanBoard
          columns={mapWorkflowColumnDataToKanban(WORKFLOW_COLUMNS)}
        />
      </div>
    </div>
  );
}
