"use client";

import { useEffect, useRef } from "react";
import {
  CREATE_STEP_IDS,
  isFutureCreateStep,
  type CreateStepId,
} from "@/app/dashboard/create/step-ids";

export interface FollowWorkflowStepOptions {
  /** The step the owner is looking at (`?step=`). */
  activeStepId: CreateStepId;
  /** The step of the workflow's current phase. */
  workflowStepId: CreateStepId;
  hasActiveWorkflow: boolean;
  /** Navigate (replace) to the given step. */
  onFollow: (stepId: CreateStepId) => void;
}

/**
 * When the workflow moves to a new gate, the page follows it if
 * the owner was looking at the previous live step (or a step ahead of it). A
 * historical step the owner opened stays put: its id differs from the previous
 * live step, and a step chosen after the move sees no further change.
 */
export function useFollowWorkflowStep({
  activeStepId,
  workflowStepId,
  hasActiveWorkflow,
  onFollow,
}: FollowWorkflowStepOptions): void {
  const previousWorkflowStepRef = useRef<CreateStepId | null>(null);

  useEffect(() => {
    if (!hasActiveWorkflow) {
      return;
    }
    const previous = previousWorkflowStepRef.current;
    previousWorkflowStepRef.current = workflowStepId;
    if (previous === null || previous === workflowStepId) {
      return;
    }
    const wasOnLiveStep = activeStepId === previous;
    const wasAhead = isFutureCreateStep(activeStepId, previous);
    if (
      (wasOnLiveStep || wasAhead) &&
      activeStepId !== CREATE_STEP_IDS.PUBLISH
    ) {
      onFollow(workflowStepId);
    }
  }, [activeStepId, hasActiveWorkflow, onFollow, workflowStepId]);
}
