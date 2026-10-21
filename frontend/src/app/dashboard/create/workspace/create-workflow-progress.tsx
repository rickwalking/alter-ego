"use client";

import { PHASE_PROGRESS_TAG_TO_EDITORIAL_PHASE } from "@/constants/editorial-workflow";
import { WORKFLOW_PHASES, WORKFLOW_PHASE_STATUS } from "@/constants/workflow";
import type { EditorialWorkflowState } from "@/modules/publishing";
import type { CarouselPhaseProgress } from "@/schemas/carousel";
import { PhaseProgressDetail } from "./phase-progress-detail";

interface EditorialWorkflowProgressProps {
  state: EditorialWorkflowState | null;
  loading: boolean;
}

/**
 * AE-0440: ``phase_progress`` is never cleared when its phase ends, so a
 * completed project still carries the images grid ("Generating 4 slide
 * images… 4/4"). Progress tagged with another workflow phase is history;
 * untagged progress (a live SSE progress event) or a tag that names no
 * workflow phase (a sub-step label) belongs to the running phase.
 */
function isProgressOfPhase(
  progress: CarouselPhaseProgress,
  currentPhase: string | undefined,
): boolean {
  if (!progress.phase) {
    return true;
  }
  const phase =
    PHASE_PROGRESS_TAG_TO_EDITORIAL_PHASE[progress.phase] ?? progress.phase;
  if (!(WORKFLOW_PHASES as readonly string[]).includes(phase)) {
    return true;
  }
  return phase === currentPhase;
}

/**
 * Fine-grained progress of the running editorial phase (label, counter,
 * per-slide grid) under the running banner.
 *
 * AE-0415: shown only while a run is active — a leftover `phase_progress`
 * label on an approved project is history, not work (B28) — and without the
 * legacy pipeline step list, which named stages that do not match the
 * editorial phases and repeated the label (B27). The phase itself is named by
 * the running banner.
 */
export function CreateWorkflowProgress({
  state,
  loading,
}: EditorialWorkflowProgressProps): React.JSX.Element | null {
  const isActiveWork =
    loading || state?.phase_status === WORKFLOW_PHASE_STATUS.IN_PROGRESS;
  const progress = state?.phase_progress as
    | CarouselPhaseProgress
    | null
    | undefined;
  const label = progress?.label.trim();

  if (
    !isActiveWork ||
    !progress ||
    !label ||
    !isProgressOfPhase(progress, state?.current_phase)
  ) {
    return null;
  }

  return (
    <PhaseProgressDetail
      label={label}
      detail={progress.detail}
      current={progress.current}
      total={progress.total}
      slides={progress.slides}
    />
  );
}
