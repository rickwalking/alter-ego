import type { CreateStepId } from "@/app/dashboard/create/step-ids";
import { EDITORIAL_PHASE_TO_STEP } from "@/app/dashboard/create/step-ids";
import type { EditorialWorkflowState } from "@/features/blog/types-ai";

/** True when approve/revise controls should show for the active workflow gate. */
export function shouldShowLiveWorkflowControls(
  state: EditorialWorkflowState | null | undefined,
  viewStepId: CreateStepId,
  workflowStepId: CreateStepId,
  awaitingHumanReview: boolean,
): boolean {
  const isLiveStep =
    state?.current_phase !== undefined &&
    EDITORIAL_PHASE_TO_STEP[state.current_phase] === viewStepId &&
    viewStepId === workflowStepId;
  return isLiveStep && awaitingHumanReview;
}
