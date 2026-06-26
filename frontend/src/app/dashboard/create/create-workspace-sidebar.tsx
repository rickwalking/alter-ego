"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";
import { BG_CARD, CYAN_GRADIENT, TEXT_DIM } from "@/constants/neon";
import { DASHBOARD_ROUTES } from "@/constants/dashboard-routes";
import { EDITORIAL_WORKFLOW_STATUS } from "@/constants/editorial-workflow";
import type { CarouselProjectResponse } from "@/schemas/carousel";
import type { EditorialWorkflowState } from "@/modules/publishing";
import { CREATE_STEP_IDS } from "@/app/dashboard/create/step-ids";
import { CreateWorkflowArtifacts } from "@/app/dashboard/create/workspace/create-workflow-artifacts";
import { ProjectSummaryCard } from "@/app/dashboard/create/workspace/project-summary-card";
import { WorkflowStatusBadge } from "@/app/dashboard/create/workspace/workflow-status-badge";

const sidebarCardStyle = {
  background: BG_CARD,
  border: "1px solid rgba(255,255,255,0.06)",
  borderRadius: "8px",
  padding: "20px",
};

export interface CreateWorkspaceSidebarProps {
  project: CarouselProjectResponse;
  workflowState: EditorialWorkflowState | null;
  activeStepId: string;
  projectId: string;
}

export function CreateWorkspaceSidebar({
  project,
  workflowState,
  activeStepId,
  projectId,
}: CreateWorkspaceSidebarProps): React.ReactElement {
  const t = useTranslations("create");

  const showPublishCta =
    workflowState?.workflow_status ===
      EDITORIAL_WORKFLOW_STATUS.APPROVED_FOR_PUBLISH ||
    activeStepId === CREATE_STEP_IDS.PUBLISH;

  return (
    <div
      style={{
        position: "sticky",
        top: "84px",
        alignSelf: "start",
        display: "flex",
        flexDirection: "column",
        gap: "16px",
      }}
    >
      <ProjectSummaryCard
        topic={project.topic}
        audience={project.audience}
        niche={project.niche}
        currentPhase={workflowState?.current_phase ?? null}
        workflowStatus={workflowState?.workflow_status ?? null}
        phaseStatus={workflowState?.phase_status ?? null}
      />

      {showPublishCta && (
        <Link
          href={DASHBOARD_ROUTES.CREATE_PUBLISH(projectId)}
          style={{
            display: "block",
            width: "100%",
            padding: "12px",
            borderRadius: "6px",
            border: "none",
            background: CYAN_GRADIENT,
            color: "#060a12",
            fontSize: "13px",
            fontWeight: 700,
            textAlign: "center",
            textDecoration: "none",
          }}
        >
          {t("publishCta")}
        </Link>
      )}

      {workflowState?.current_phase && (
        <div style={sidebarCardStyle}>
          <h3
            style={{ fontSize: "14px", fontWeight: 700, marginBottom: "8px" }}
          >
            Workflow
          </h3>
          <div className="flex items-center gap-2">
            <span style={{ fontSize: "12px", color: TEXT_DIM }}>
              Active phase
            </span>
            <WorkflowStatusBadge
              status={workflowState.phase_status ?? null}
              label={workflowState.current_phase}
            />
          </div>
        </div>
      )}

      <CreateWorkflowArtifacts state={workflowState} />
    </div>
  );
}
