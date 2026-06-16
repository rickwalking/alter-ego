"use client";

import { useTranslations } from "next-intl";
import { CarouselProgress } from "@/app/dashboard/create/workspace/create-carousel-progress";
import { EDITORIAL_TO_PIPELINE_PHASE } from "@/constants/editorial-workflow";
import { WORKFLOW_PHASE_STATUS } from "@/constants/workflow";
import type { EditorialWorkflowState } from "@/modules/publishing";
import type { CarouselPhaseProgress } from "@/schemas/carousel";

interface EditorialWorkflowProgressProps {
  state: EditorialWorkflowState | null;
  loading: boolean;
}

function resolvePipelinePhase(currentPhase: string): string {
  return EDITORIAL_TO_PIPELINE_PHASE[currentPhase] ?? currentPhase;
}

function buildSyntheticProgress(
  pipelinePhase: string,
  labels: Record<string, string>,
): CarouselPhaseProgress {
  const editorialPhase =
    Object.entries(EDITORIAL_TO_PIPELINE_PHASE).find(
      ([, mapped]) => mapped === pipelinePhase,
    )?.[0] ?? pipelinePhase;
  return {
    phase: pipelinePhase,
    label: labels[editorialPhase] ?? labels.processing ?? "Processing…",
  };
}

export function CreateWorkflowProgress({
  state,
  loading,
}: EditorialWorkflowProgressProps): React.JSX.Element | null {
  const t = useTranslations("editorialWorkflow.progress");
  const currentPhase = state?.current_phase ?? "";
  const phaseStatus = state?.phase_status ?? "";

  const editorialProgress = state?.phase_progress as
    | CarouselPhaseProgress
    | null
    | undefined;

  const hasPersistedProgressLabel = Boolean(editorialProgress?.label?.trim());

  const isActiveWork =
    loading ||
    phaseStatus === WORKFLOW_PHASE_STATUS.IN_PROGRESS ||
    hasPersistedProgressLabel;

  if (!isActiveWork) {
    return null;
  }

  const labels: Record<string, string> = {
    research: t("research"),
    outline: t("outline"),
    content: t("content"),
    design: t("design"),
    images: t("images"),
    final_review: t("finalReview"),
    processing: t("processing"),
  };

  const phaseProgress =
    editorialProgress ??
    buildSyntheticProgress(
      currentPhase ? resolvePipelinePhase(currentPhase) : "pending",
      labels,
    );

  const pipelinePhase =
    phaseProgress?.phase ??
    (currentPhase ? resolvePipelinePhase(currentPhase) : "pending");

  return (
    <CarouselProgress
      currentPhase={pipelinePhase}
      isComplete={false}
      hasError={false}
      phaseProgress={phaseProgress}
    />
  );
}
