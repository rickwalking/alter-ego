import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import {
  CREATE_STEP_IDS,
  type CreateStepId,
} from "@/app/dashboard/create/step-ids";
import {
  EDITORIAL_PHASES,
  EDITORIAL_WORKFLOW_TRANSPORT_MODE,
} from "@/constants/editorial-workflow";
import { WORKFLOW_PHASE_STATUS } from "@/constants/workflow";
import type { EditorialWorkflowState } from "@/modules/publishing";
import type { useEditorialWorkflow } from "@/modules/editorial";
import { CreateWorkflowPanel } from "./create-workflow-panel";

const stateWithPrompts: EditorialWorkflowState = {
  project_id: "project-1",
  current_phase: EDITORIAL_PHASES.IMAGES,
  phase_status: WORKFLOW_PHASE_STATUS.AWAITING_HUMAN,
  research_findings: [],
  outline: [],
  slide_drafts: [],
  slide_image_prompts: [
    {
      slide_index: 1,
      title: "AI security hook",
      image_prompt: "Cybersecurity analyst reviewing AI risk dashboard",
    },
    {
      slide_index: 2,
      title: "Risk pattern",
      image_prompt: "Layered threat model diagram with clear contrast",
    },
  ],
  status: "draft",
};

function buildWorkflow(
  state: EditorialWorkflowState,
): ReturnType<typeof useEditorialWorkflow> {
  return {
    state,
    phaseEvents: [],
    loading: false,
    error: null,
    transportMode: EDITORIAL_WORKFLOW_TRANSPORT_MODE.SSE,
    start: vi.fn(async () => state),
    resume: vi.fn(async () => state),
    refreshState: vi.fn(async () => state),
    approve: vi.fn(async () => state),
    revise: vi.fn(async () => state),
    awaitingHumanReview: true,
    hasActiveWorkflow: true,
  };
}

function renderPanel(
  state: EditorialWorkflowState,
  viewStepId: CreateStepId = CREATE_STEP_IDS.IMAGES,
): void {
  render(
    <CreateWorkflowPanel
      projectId={state.project_id}
      topic="AI security"
      audience="Security leaders"
      brief="Review AI security risks"
      workflow={buildWorkflow(state)}
      viewStepId={viewStepId}
      workflowStepId={CREATE_STEP_IDS.IMAGES}
    />,
  );
}

describe("CreateWorkflowPanel image prompts", () => {
  it("shows image prompts and prompt artifact count on the images tab", () => {
    renderPanel(stateWithPrompts);

    expect(screen.getByText("2 image prompts ready")).toBeInTheDocument();
    expect(screen.getByText("Slide image prompts")).toBeInTheDocument();
    expect(screen.getByLabelText("Image prompt for slide 1")).toHaveValue(
      "Cybersecurity analyst reviewing AI risk dashboard",
    );
  });

  it("hides image prompts outside the images tab", () => {
    renderPanel(stateWithPrompts, CREATE_STEP_IDS.CONTENT);

    expect(screen.queryByText("Slide image prompts")).not.toBeInTheDocument();
  });
});
