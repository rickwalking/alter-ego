import { renderHook } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { CREATE_STEP_IDS, type CreateStepId } from "./step-ids";
import { useFollowWorkflowStep } from "./use-follow-workflow-step";

interface Props {
  activeStepId: CreateStepId;
  workflowStepId: CreateStepId;
  hasActiveWorkflow: boolean;
}

function setup(initial: Props) {
  const onFollow = vi.fn();
  const hook = renderHook(
    (props: Props) => useFollowWorkflowStep({ ...props, onFollow }),
    { initialProps: initial },
  );
  return { ...hook, onFollow };
}

// Feature: Create-flow UI fixes (AE-0415) — B26 auto-advance
describe("useFollowWorkflowStep", () => {
  // Scenario: The page follows the workflow to the next gate
  it("follows the workflow from the live step to the new gate", () => {
    const { rerender, onFollow } = setup({
      activeStepId: CREATE_STEP_IDS.RESEARCH,
      workflowStepId: CREATE_STEP_IDS.RESEARCH,
      hasActiveWorkflow: true,
    });
    expect(onFollow).not.toHaveBeenCalled();

    rerender({
      activeStepId: CREATE_STEP_IDS.RESEARCH,
      workflowStepId: CREATE_STEP_IDS.OUTLINE,
      hasActiveWorkflow: true,
    });
    expect(onFollow).toHaveBeenCalledWith(CREATE_STEP_IDS.OUTLINE);
  });

  it("follows when the owner was on a step ahead of the workflow", () => {
    const { rerender, onFollow } = setup({
      activeStepId: CREATE_STEP_IDS.IMAGES,
      workflowStepId: CREATE_STEP_IDS.RESEARCH,
      hasActiveWorkflow: true,
    });
    rerender({
      activeStepId: CREATE_STEP_IDS.IMAGES,
      workflowStepId: CREATE_STEP_IDS.OUTLINE,
      hasActiveWorkflow: true,
    });
    expect(onFollow).toHaveBeenCalledWith(CREATE_STEP_IDS.OUTLINE);
  });

  // Scenario: A historical step chosen by the owner is not overridden
  it("leaves a historical step the owner opened", () => {
    const { rerender, onFollow } = setup({
      activeStepId: CREATE_STEP_IDS.RESEARCH,
      workflowStepId: CREATE_STEP_IDS.OUTLINE,
      hasActiveWorkflow: true,
    });
    rerender({
      activeStepId: CREATE_STEP_IDS.RESEARCH,
      workflowStepId: CREATE_STEP_IDS.CONTENT,
      hasActiveWorkflow: true,
    });
    expect(onFollow).not.toHaveBeenCalled();
  });

  it("does not move when only the viewed step changes", () => {
    const { rerender, onFollow } = setup({
      activeStepId: CREATE_STEP_IDS.OUTLINE,
      workflowStepId: CREATE_STEP_IDS.OUTLINE,
      hasActiveWorkflow: true,
    });
    rerender({
      activeStepId: CREATE_STEP_IDS.RESEARCH,
      workflowStepId: CREATE_STEP_IDS.OUTLINE,
      hasActiveWorkflow: true,
    });
    expect(onFollow).not.toHaveBeenCalled();
  });

  it("does nothing without an active workflow or on the publish step", () => {
    const { rerender, onFollow } = setup({
      activeStepId: CREATE_STEP_IDS.PUBLISH,
      workflowStepId: CREATE_STEP_IDS.BRIEF,
      hasActiveWorkflow: false,
    });
    rerender({
      activeStepId: CREATE_STEP_IDS.PUBLISH,
      workflowStepId: CREATE_STEP_IDS.REVIEW,
      hasActiveWorkflow: true,
    });
    rerender({
      activeStepId: CREATE_STEP_IDS.PUBLISH,
      workflowStepId: CREATE_STEP_IDS.PUBLISH,
      hasActiveWorkflow: true,
    });
    expect(onFollow).not.toHaveBeenCalled();
  });
});
