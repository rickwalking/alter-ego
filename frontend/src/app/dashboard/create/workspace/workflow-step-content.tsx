"use client";

import { useTranslations } from "next-intl";
import { TEXT_DIM, BG_CARD } from "@/constants/neon";
import { CarouselPreview } from "./create-carousel-preview";
import { CreateWorkflowPanel } from "./create-workflow-panel";
import {
  isFutureCreateStep,
  resolveStepFromWorkflowPhase,
  type CreateStepId,
} from "@/app/dashboard/create/step-ids";
import type { CarouselProjectResponse } from "@/schemas/carousel";
import type { useEditorialWorkflow } from "@/modules/editorial";

export interface WorkflowStepContentProps {
  project: CarouselProjectResponse;
  projectId: string;
  activeStepId: CreateStepId;
  sources: Array<{ title: string; content: string; source_type?: string }>;
  workflowStarted: boolean;
  editorialWorkflow: ReturnType<typeof useEditorialWorkflow>;
  publishedProject: CarouselProjectResponse | null;
  onPublished: (project: CarouselProjectResponse) => void;
}

export function WorkflowStepContent({
  project,
  projectId,
  activeStepId,
  sources,
  workflowStarted,
  editorialWorkflow,
  publishedProject,
  onPublished,
}: WorkflowStepContentProps): React.ReactElement {
  const t = useTranslations("create");
  const workflowStepId = resolveStepFromWorkflowPhase(
    editorialWorkflow.state?.current_phase,
  );
  const showWorkflow = workflowStarted || editorialWorkflow.hasActiveWorkflow;
  const isFutureStep = isFutureCreateStep(activeStepId, workflowStepId);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
      {showWorkflow && isFutureStep ? (
        <p
          style={{
            fontSize: "13px",
            color: TEXT_DIM,
            margin: 0,
            padding: "12px 16px",
            background: BG_CARD,
            borderRadius: "8px",
            border: "1px solid rgba(255,255,255,0.06)",
          }}
        >
          {t("futureStep", {
            phase: editorialWorkflow.state?.current_phase ?? "—",
          })}
        </p>
      ) : null}

      {showWorkflow && !isFutureStep ? (
        <CreateWorkflowPanel
          projectId={projectId}
          topic={project.topic}
          audience={project.audience}
          brief={project.niche}
          sources={sources}
          autoStart={workflowStarted && !editorialWorkflow.hasActiveWorkflow}
          onPublished={() => onPublished(project)}
          workflow={editorialWorkflow}
          viewStepId={activeStepId}
          workflowStepId={workflowStepId}
        />
      ) : (
        <p style={{ fontSize: "13px", color: TEXT_DIM }}>
          {t("startWorkflowHint")}
        </p>
      )}

      {publishedProject && <CarouselPreview project={publishedProject} />}
    </div>
  );
}
