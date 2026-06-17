import { describe, expect, it } from "vitest";
import { CREATE_STEP_IDS } from "@/app/dashboard/create/step-ids";
import { EDITORIAL_PHASES } from "@/constants/editorial-workflow";
import { WORKFLOW_PHASE_STATUS } from "@/constants/workflow";
import type { EditorialWorkflowState } from "@/modules/publishing";
import { shouldShowLiveWorkflowControls } from "./create-workflow-live-controls";

const baseState: EditorialWorkflowState = {
  project_id: "project-1",
  current_phase: EDITORIAL_PHASES.OUTLINE,
  phase_status: WORKFLOW_PHASE_STATUS.AWAITING_HUMAN,
  research_findings: [],
  outline: [{ title: "Intro" }],
  slide_drafts: [],
  status: "draft",
};

describe("shouldShowLiveWorkflowControls", () => {
  it("shows controls only on the live workflow step at human gate", () => {
    expect(
      shouldShowLiveWorkflowControls({
        state: baseState,
        viewStepId: CREATE_STEP_IDS.OUTLINE,
        workflowStepId: CREATE_STEP_IDS.OUTLINE,
        awaitingHumanReview: true,
      }),
    ).toBe(true);
  });

  it("hides controls on historical steps", () => {
    expect(
      shouldShowLiveWorkflowControls({
        state: { ...baseState, current_phase: EDITORIAL_PHASES.CONTENT },
        viewStepId: CREATE_STEP_IDS.OUTLINE,
        workflowStepId: CREATE_STEP_IDS.CONTENT,
        awaitingHumanReview: true,
      }),
    ).toBe(false);
  });

  it("hides controls when not awaiting human review", () => {
    expect(
      shouldShowLiveWorkflowControls({
        state: baseState,
        viewStepId: CREATE_STEP_IDS.OUTLINE,
        workflowStepId: CREATE_STEP_IDS.OUTLINE,
        awaitingHumanReview: false,
      }),
    ).toBe(false);
  });

  it("shows controls when design phase maps to images tab", () => {
    expect(
      shouldShowLiveWorkflowControls({
        state: { ...baseState, current_phase: EDITORIAL_PHASES.DESIGN },
        viewStepId: CREATE_STEP_IDS.IMAGES,
        workflowStepId: CREATE_STEP_IDS.IMAGES,
        awaitingHumanReview: true,
      }),
    ).toBe(true);
  });
});
