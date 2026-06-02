"use client";

import {
  BG_CARD,
  NEON_AMBER,
  NEON_AMBER_DIM,
  TEXT,
  TEXT_DIM,
} from "@/constants/neon";
import { EDITORIAL_WORKFLOW_STATUS } from "@/constants/editorial-workflow";

export interface ProjectSummaryCardProps {
  topic: string;
  audience: string;
  niche: string;
  currentPhase: string | null;
  workflowStatus: string | null;
}

const cardStyle = {
  background: BG_CARD,
  border: "1px solid rgba(255,255,255,0.06)",
  borderRadius: "8px",
  padding: "20px",
};

export function ProjectSummaryCard({
  topic,
  audience,
  niche,
  currentPhase,
  workflowStatus,
}: ProjectSummaryCardProps): React.ReactElement {
  const statusLabel =
    workflowStatus === EDITORIAL_WORKFLOW_STATUS.APPROVED_FOR_PUBLISH
      ? "Ready to publish"
      : currentPhase
        ? currentPhase.replace("_", " ")
        : "Draft";

  const summaryRows = [
    { label: "Topic", value: topic },
    { label: "Audience", value: audience },
    { label: "Brief", value: niche },
    { label: "Phase", value: currentPhase ?? "—" },
    { label: "Status", value: statusLabel, badge: true },
  ] as const;

  return (
    <div style={cardStyle}>
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
  );
}
