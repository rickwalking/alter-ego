import type { CreateStepId } from "@/app/dashboard/create/step-ids";

export type StepVisualState = "active" | "done" | "pending";

export function resolveStepState(
  stepId: CreateStepId,
  activeStepId: CreateStepId,
  completedStepIds: readonly CreateStepId[],
): StepVisualState {
  if (stepId === activeStepId) {
    return "active";
  }
  if (completedStepIds.includes(stepId)) {
    return "done";
  }
  return "pending";
}
