import type { CreateStepId } from "@/app/dashboard/create/step-ids";
import type { EditorialWorkflowState } from "@/features/blog/types-ai";

/** True when approve/revise controls should show for the active workflow gate. */
export function shouldShowLiveWorkflowControls(
  viewPhase: string | undefined,
  state: EditorialWorkflowState | null | undefined,
  viewStepId: CreateStepId,
  workflowStepId: CreateStepId,
  awaitingHumanReview: boolean,
): boolean {
  const isLiveStep =
    viewPhase !== undefined &&
    state?.current_phase === viewPhase &&
    viewStepId === workflowStepId;
  return isLiveStep && awaitingHumanReview;
}
