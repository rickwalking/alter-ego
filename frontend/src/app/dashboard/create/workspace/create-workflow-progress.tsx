"use client";

import { WORKFLOW_PHASE_STATUS } from "@/constants/workflow";
import type { EditorialWorkflowState } from "@/modules/publishing";
import type { CarouselPhaseProgress } from "@/schemas/carousel";
import { PhaseProgressDetail } from "./phase-progress-detail";

interface EditorialWorkflowProgressProps {
  state: EditorialWorkflowState | null;
  loading: boolean;
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
  const label = progress?.label?.trim();

  if (!isActiveWork || !progress || !label) {
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
