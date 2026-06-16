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
      shouldShowLiveWorkflowControls(
        baseState,
        CREATE_STEP_IDS.OUTLINE,
        CREATE_STEP_IDS.OUTLINE,
        true,
      ),
    ).toBe(true);
  });

  it("hides controls on historical steps", () => {
    expect(
      shouldShowLiveWorkflowControls(
        { ...baseState, current_phase: EDITORIAL_PHASES.CONTENT },
        CREATE_STEP_IDS.OUTLINE,
        CREATE_STEP_IDS.CONTENT,
        true,
      ),
    ).toBe(false);
  });

  it("hides controls when not awaiting human review", () => {
    expect(
      shouldShowLiveWorkflowControls(
        baseState,
        CREATE_STEP_IDS.OUTLINE,
        CREATE_STEP_IDS.OUTLINE,
        false,
      ),
    ).toBe(false);
  });

  it("shows controls when design phase maps to images tab", () => {
    expect(
      shouldShowLiveWorkflowControls(
        { ...baseState, current_phase: EDITORIAL_PHASES.DESIGN },
        CREATE_STEP_IDS.IMAGES,
        CREATE_STEP_IDS.IMAGES,
        true,
      ),
    ).toBe(true);
  });
});
