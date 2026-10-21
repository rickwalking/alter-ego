"use client";

import { useTranslations } from "next-intl";
import { usePhaseLabel } from "@/app/dashboard/create/workspace/editorial-phase-labels";
import { BG_CARD, TEXT, TEXT_DIM } from "@/constants/neon";
import { EDITORIAL_WORKFLOW_STATUS } from "@/constants/editorial-workflow";
import { WorkflowStatusBadge } from "@/app/dashboard/create/workspace/workflow-status-badge";

export interface ProjectSummaryCardProps {
  topic: string;
  audience: string;
  niche: string;
  currentPhase: string | null;
  workflowStatus: string | null;
  phaseStatus?: string | null;
}

const cardStyle = {
  background: BG_CARD,
  border: "1px solid rgba(255,255,255,0.06)",
  borderRadius: "8px",
  padding: "20px",
};

const rowStyle = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  padding: "8px 0",
  fontSize: "13px",
  borderBottom: "1px solid rgba(255,255,255,0.03)",
  gap: "12px",
} as const;

/**
 * Project summary. The status prefers the editorial "ready to publish" signal,
 * otherwise it reflects the live phase run status; a missing status resolves to
 * Draft inside the badge.
 */
export function ProjectSummaryCard({
  topic,
  audience,
  niche,
  currentPhase,
  workflowStatus,
  phaseStatus = null,
}: Readonly<ProjectSummaryCardProps>): React.ReactElement {
  const t = useTranslations("create.summary");
  const phaseLabel = usePhaseLabel();
  const effectiveStatus =
    workflowStatus === EDITORIAL_WORKFLOW_STATUS.APPROVED_FOR_PUBLISH
      ? workflowStatus
      : phaseStatus;

  const textRows = [
    { label: t("topic"), value: topic },
    { label: t("audience"), value: audience },
    { label: t("brief"), value: niche },
    { label: t("phase"), value: phaseLabel(currentPhase) },
  ] as const;

  return (
    <div style={cardStyle}>
      <h3 style={{ fontSize: "14px", fontWeight: 700, marginBottom: "12px" }}>
        {t("title")}
      </h3>
      {textRows.map((row) => (
        <div key={row.label} style={rowStyle}>
          <span style={{ color: TEXT_DIM }}>{row.label}</span>
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
        </div>
      ))}
      <div style={{ ...rowStyle, borderBottom: "none" }}>
        <span style={{ color: TEXT_DIM }}>{t("status")}</span>
        <WorkflowStatusBadge status={effectiveStatus} />
      </div>
    </div>
  );
}
