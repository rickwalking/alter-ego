import { EDITORIAL_PHASES } from "@/constants/editorial-workflow";

/** Tab identifiers for the neon create workspace (7 steps). */
export const CREATE_STEP_IDS = {
  BRIEF: "brief",
  RESEARCH: "research",
  OUTLINE: "outline",
  CONTENT: "content",
  IMAGES: "images",
  REVIEW: "review",
  PUBLISH: "publish",
} as const;

export type CreateStepId =
  (typeof CREATE_STEP_IDS)[keyof typeof CREATE_STEP_IDS];

export const CREATE_STEP_ORDER: readonly CreateStepId[] = [
  CREATE_STEP_IDS.BRIEF,
  CREATE_STEP_IDS.RESEARCH,
  CREATE_STEP_IDS.OUTLINE,
  CREATE_STEP_IDS.CONTENT,
  CREATE_STEP_IDS.IMAGES,
  CREATE_STEP_IDS.REVIEW,
  CREATE_STEP_IDS.PUBLISH,
];

/** Maps workflow phase → create tab (design rolls into images tab). */
export const EDITORIAL_PHASE_TO_STEP: Record<string, CreateStepId> = {
  [EDITORIAL_PHASES.RESEARCH]: CREATE_STEP_IDS.RESEARCH,
  [EDITORIAL_PHASES.OUTLINE]: CREATE_STEP_IDS.OUTLINE,
  [EDITORIAL_PHASES.CONTENT]: CREATE_STEP_IDS.CONTENT,
  [EDITORIAL_PHASES.DESIGN]: CREATE_STEP_IDS.IMAGES,
  [EDITORIAL_PHASES.IMAGES]: CREATE_STEP_IDS.IMAGES,
  [EDITORIAL_PHASES.FINAL_REVIEW]: CREATE_STEP_IDS.REVIEW,
  [EDITORIAL_PHASES.PUBLISHED]: CREATE_STEP_IDS.PUBLISH,
};

export const CREATE_STEP_TO_EDITORIAL_PHASE: Partial<
  Record<CreateStepId, string>
> = {
  [CREATE_STEP_IDS.RESEARCH]: EDITORIAL_PHASES.RESEARCH,
  [CREATE_STEP_IDS.OUTLINE]: EDITORIAL_PHASES.OUTLINE,
  [CREATE_STEP_IDS.CONTENT]: EDITORIAL_PHASES.CONTENT,
  [CREATE_STEP_IDS.IMAGES]: EDITORIAL_PHASES.IMAGES,
  [CREATE_STEP_IDS.REVIEW]: EDITORIAL_PHASES.FINAL_REVIEW,
};

export function isCreateStepId(value: string): value is CreateStepId {
  return (CREATE_STEP_ORDER as readonly string[]).includes(value);
}

export function parseCreateStepId(
  value: string | null | undefined,
): CreateStepId {
  if (value && isCreateStepId(value)) {
    return value;
  }
  return CREATE_STEP_IDS.BRIEF;
}

export function stepIndex(stepId: CreateStepId): number {
  return CREATE_STEP_ORDER.indexOf(stepId);
}

export function resolveStepFromWorkflowPhase(
  currentPhase: string | undefined,
): CreateStepId {
  if (!currentPhase) {
    return CREATE_STEP_IDS.BRIEF;
  }
  return EDITORIAL_PHASE_TO_STEP[currentPhase] ?? CREATE_STEP_IDS.BRIEF;
}

export function completedStepsBefore(
  activeStepId: CreateStepId,
): CreateStepId[] {
  const index = stepIndex(activeStepId);
  if (index <= 0) {
    return [];
  }
  return CREATE_STEP_ORDER.slice(0, index);
}

/** True when the viewed tab is strictly before the workflow's current tab. */
export function isHistoricalCreateStep(
  viewStepId: CreateStepId,
  workflowStepId: CreateStepId,
): boolean {
  return stepIndex(viewStepId) < stepIndex(workflowStepId);
}

/** True when the viewed tab is ahead of the workflow's current tab. */
export function isFutureCreateStep(
  viewStepId: CreateStepId,
  workflowStepId: CreateStepId,
): boolean {
  return stepIndex(viewStepId) > stepIndex(workflowStepId);
}
