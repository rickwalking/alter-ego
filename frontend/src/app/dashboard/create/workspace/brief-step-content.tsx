"use client";

import { BG_CARD, TEXT_DIM } from "@/constants/neon";
import { CreateDraftBlogPreview } from "./create-draft-blog-preview";
import { CreateMaterialsGate } from "./create-materials-gate";
import { CreateSourceMaterials } from "./create-source-materials";
import type { ContentSource } from "@/modules/publishing";
import type { CarouselProjectResponse } from "@/schemas/carousel";
import type { useEditorialWorkflow } from "@/features/create/hooks/use-editorial-workflow";

export interface BriefStepContentProps {
  project: CarouselProjectResponse;
  projectId: string;
  sourceCount: number;
  workflowStarted: boolean;
  onStartWorkflow: (withMaterials: boolean) => Promise<void>;
  onSourcesChange: (sources: ContentSource[]) => void;
  editorialWorkflow: ReturnType<typeof useEditorialWorkflow>;
}

const briefCardStyle = {
  background: BG_CARD,
  border: "1px solid rgba(255,255,255,0.06)",
  borderRadius: "8px",
  padding: "20px",
};

export function BriefStepContent({
  project,
  projectId,
  sourceCount,
  workflowStarted,
  onStartWorkflow,
  onSourcesChange,
  editorialWorkflow,
}: BriefStepContentProps): React.ReactElement {
  const showGate = !workflowStarted && !editorialWorkflow.hasActiveWorkflow;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
      <div style={briefCardStyle}>
        <h3 style={{ fontSize: "14px", fontWeight: 700, marginBottom: "12px" }}>
          Topic & Brief
        </h3>
        <p style={{ fontSize: "15px", fontWeight: 600, margin: "0 0 8px" }}>
          {project.topic}
        </p>
        <p style={{ fontSize: "13px", color: TEXT_DIM, margin: "0 0 12px" }}>
          {project.audience}
        </p>
        <p style={{ fontSize: "13px", margin: 0, lineHeight: 1.5 }}>
          {project.niche}
        </p>
      </div>

      <CreateDraftBlogPreview projectId={projectId} />

      <CreateSourceMaterials
        projectId={projectId}
        onSourcesChange={onSourcesChange}
      />

      {showGate && (
        <CreateMaterialsGate
          sourceCount={sourceCount}
          loading={editorialWorkflow.loading}
          onStartWithMaterials={() => void onStartWorkflow(true)}
          onStartWithoutMaterials={() => void onStartWorkflow(false)}
        />
      )}

      {workflowStarted && editorialWorkflow.loading && (
        <p
          style={{ fontSize: "13px", color: TEXT_DIM, margin: 0 }}
          role="status"
          data-testid="workflow-starting"
        >
          Starting editorial workflow…
        </p>
      )}

      {editorialWorkflow.error && (
        <p
          style={{ fontSize: "13px", color: "#f87171", margin: 0 }}
          role="alert"
        >
          {editorialWorkflow.error}
        </p>
      )}
    </div>
  );
}
