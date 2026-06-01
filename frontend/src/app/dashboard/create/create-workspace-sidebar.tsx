"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";
import {
  BG_CARD,
  CYAN_GRADIENT,
  NEON_AMBER,
  NEON_AMBER_DIM,
  NEON_CYAN,
  TEXT,
  TEXT_DIM,
} from "@/constants/neon";
import { DASHBOARD_ROUTES } from "@/constants/dashboard-routes";
import { EDITORIAL_WORKFLOW_STATUS } from "@/constants/editorial-workflow";
import type { CarouselProjectResponse } from "@/schemas/carousel";
import type { EditorialWorkflowState } from "@/features/blog/types-ai";
import { CREATE_STEP_IDS } from "@/app/dashboard/create/step-ids";
import { CreateWorkflowArtifacts } from "@/app/dashboard/create/workspace/create-workflow-artifacts";

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
  const statusLabel =
    workflowState?.workflow_status ===
    EDITORIAL_WORKFLOW_STATUS.APPROVED_FOR_PUBLISH
      ? "Ready to publish"
      : workflowState?.current_phase
        ? workflowState.current_phase.replace("_", " ")
        : "Draft";

  const summaryRows = [
    { label: "Topic", value: project.topic },
    { label: "Audience", value: project.audience },
    { label: "Brief", value: project.niche },
    { label: "Phase", value: workflowState?.current_phase ?? "—" },
    { label: "Status", value: statusLabel, badge: true },
  ] as const;

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
      <div style={sidebarCardStyle}>
        <h3 style={{ fontSize: "14px", fontWeight: 700, marginBottom: "12px" }}>
          Project Summary
        </h3>
        {summaryRows.map((row) => (
          <div
            key={row.label}
            style={{
              display: "flex",
              justifyContent: "space-between",
              padding: "8px 0",
              fontSize: "13px",
              borderBottom: "1px solid rgba(255,255,255,0.03)",
              gap: "12px",
            }}
          >
            <span style={{ color: TEXT_DIM }}>{row.label}</span>
            {"badge" in row && row.badge ? (
              <span
                style={{
                  padding: "2px 6px",
                  borderRadius: "4px",
                  fontSize: "11px",
                  fontWeight: 600,
                  background: NEON_AMBER_DIM,
                  color: NEON_AMBER,
                  textTransform: "capitalize",
                }}
              >
                {row.value}
              </span>
            ) : (
              <span
                style={{
                  color: TEXT,
                  fontWeight: 600,
                  textAlign: "right",
                  maxWidth: "60%",
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                }}
              >
                {row.value}
              </span>
            )}
          </div>
        ))}
      </div>

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
          <h3 style={{ fontSize: "14px", fontWeight: 700, marginBottom: "8px" }}>
            Workflow
          </h3>
          <p style={{ fontSize: "12px", color: TEXT_DIM, margin: 0 }}>
            Active phase:{" "}
            <span style={{ color: NEON_CYAN, fontWeight: 600 }}>
              {workflowState.current_phase}
            </span>
          </p>
        </div>
      )}

      <CreateWorkflowArtifacts state={workflowState} />
    </div>
  );
}
