import { renderWithProviders as render, screen } from "@/test/utils";
import userEvent from "@testing-library/user-event";
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
  overrides?: Partial<ReturnType<typeof useEditorialWorkflow>>,
): ReturnType<typeof useEditorialWorkflow> {
  return {
    state,
    phaseEvents: [],
    loading: false,
    error: null,
    transportMode: EDITORIAL_WORKFLOW_TRANSPORT_MODE.SSE,
    reconnectLiveUpdates: vi.fn(),
    start: vi.fn(async () => state),
    resume: vi.fn(async () => state),
    refreshState: vi.fn(async () => state),
    approve: vi.fn(async () => state),
    revise: vi.fn(async () => state),
    awaitingHumanReview:
      state.phase_status === WORKFLOW_PHASE_STATUS.AWAITING_HUMAN,
    hasActiveWorkflow: true,
    runningAction: null,
    ...overrides,
  };
}

function renderPanel(
  state: EditorialWorkflowState,
  viewStepId: CreateStepId = CREATE_STEP_IDS.IMAGES,
  workflowStepId: CreateStepId = CREATE_STEP_IDS.IMAGES,
): void {
  render(
    <CreateWorkflowPanel
      projectId={state.project_id}
      topic="AI security"
      audience="Security leaders"
      brief="Review AI security risks"
      workflow={buildWorkflow(state)}
      viewStepId={viewStepId}
      workflowStepId={workflowStepId}
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

function gateState(
  overrides: Partial<EditorialWorkflowState>,
): EditorialWorkflowState {
  return {
    project_id: "project-1",
    current_phase: EDITORIAL_PHASES.RESEARCH,
    phase_status: WORKFLOW_PHASE_STATUS.AWAITING_HUMAN,
    research_findings: [],
    outline: [],
    slide_drafts: [],
    status: "draft",
    ...overrides,
  };
}

// Feature: Create-flow UI fixes (AE-0415) — tests/features/create-flow-ui-ae0415.feature
describe("CreateWorkflowPanel live gates (AE-0415)", () => {
  // Scenario: The live research gate shows the findings and their sources
  it("lists the research findings with their sources on the live research gate", () => {
    renderPanel(
      gateState({
        research_findings: [
          { source: "https://example.com/a", key_points: ["Point A"] },
          { source: "https://example.com/b", key_points: ["Point B"] },
        ],
      }),
      CREATE_STEP_IDS.RESEARCH,
      CREATE_STEP_IDS.RESEARCH,
    );

    expect(screen.getByText("https://example.com/a")).toBeInTheDocument();
    expect(screen.getByText("Point B")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Approve Phase" })).toBeEnabled();
  });

  // Scenario: The live outline gate shows the slide titles and key points
  it("lists the outline titles and key points on the live outline gate", () => {
    renderPanel(
      gateState({
        current_phase: EDITORIAL_PHASES.OUTLINE,
        outline: [
          { title: "Hook slide", key_points: ["Why now"] },
          { title: "Closing slide", key_points: [] },
        ],
      }),
      CREATE_STEP_IDS.OUTLINE,
      CREATE_STEP_IDS.OUTLINE,
    );

    expect(screen.getByText("Hook slide")).toBeInTheDocument();
    expect(screen.getByText("Why now")).toBeInTheDocument();
    expect(screen.getByText("Closing slide")).toBeInTheDocument();
  });

  // Scenario: A reload during a running phase keeps the running state
  it("shows the running banner and no review actions while a run executes", () => {
    renderPanel(
      gateState({
        current_phase: EDITORIAL_PHASES.CONTENT,
        phase_status: WORKFLOW_PHASE_STATUS.IN_PROGRESS,
      }),
      CREATE_STEP_IDS.CONTENT,
      CREATE_STEP_IDS.CONTENT,
    );

    expect(screen.getByTestId("run-progress-banner")).toBeInTheDocument();
    expect(screen.queryByLabelText("Feedback")).not.toBeInTheDocument();
    expect(screen.queryByTestId("auto-repair")).not.toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Approve Phase" }),
    ).toBeDisabled();
  });
});

describe("CreateWorkflowPanel persona gate (AE-0415, B01)", () => {
  const contentGate = (
    personaScores: Record<string, unknown>,
  ): EditorialWorkflowState =>
    gateState({
      current_phase: EDITORIAL_PHASES.CONTENT,
      persona_scores: personaScores,
    });

  // Scenario: A 0-10 persona score is read on the 0-100 scale
  it("does not block approval for a 0-10 score above the threshold", () => {
    renderPanel(
      contentGate({ slide_1: { overall: 84 }, slide_2: { overall: 8.7 } }),
      CREATE_STEP_IDS.CONTENT,
      CREATE_STEP_IDS.CONTENT,
    );
    expect(screen.queryByText(/Persona voice match/)).not.toBeInTheDocument();
  });

  // Scenario: An unscored slide is ignored by the persona gate
  it("ignores unscored slides", () => {
    renderPanel(
      contentGate({ slide_1: { overall: 80 }, slide_4: { overall: 0 } }),
      CREATE_STEP_IDS.CONTENT,
      CREATE_STEP_IDS.CONTENT,
    );
    expect(screen.queryByText(/Persona voice match/)).not.toBeInTheDocument();
  });

  // Scenario: The persona hint names the slides below the threshold
  it("names the slides below the threshold with their scores", () => {
    renderPanel(
      contentGate({ slide_3: { overall: 91 }, slide_2: { overall: 6.5 } }),
      CREATE_STEP_IDS.CONTENT,
      CREATE_STEP_IDS.CONTENT,
    );
    expect(
      screen.getByText(
        "Persona voice match is below 70/100 on Slide 2 (65/100). Revise these slides before approving.",
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Approve Phase" }),
    ).toBeDisabled();
  });
});

// Feature: tests/features/workflow-stream-recovery-ae0440.feature
describe("CreateWorkflowPanel live updates (AE-0440)", () => {
  function renderWithTransport(
    workflow: ReturnType<typeof useEditorialWorkflow>,
    viewStepId: CreateStepId = CREATE_STEP_IDS.IMAGES,
  ): void {
    render(
      <CreateWorkflowPanel
        projectId={stateWithPrompts.project_id}
        topic="AI security"
        audience="Security leaders"
        brief="Review AI security risks"
        workflow={workflow}
        viewStepId={viewStepId}
        workflowStepId={CREATE_STEP_IDS.IMAGES}
      />,
    );
  }

  // Scenario: Live updates disconnect after the reconnect budget is spent
  // Scenario: Retry reconnects a disconnected stream
  it("shows the disconnected state and retries on click", async () => {
    const reconnectLiveUpdates = vi.fn();
    renderWithTransport(
      buildWorkflow(stateWithPrompts, {
        transportMode: EDITORIAL_WORKFLOW_TRANSPORT_MODE.DISCONNECTED,
        reconnectLiveUpdates,
      }),
    );

    expect(screen.getByText("Live updates disconnected")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(reconnectLiveUpdates).toHaveBeenCalledTimes(1);
  });

  it("shows the disconnected state on a past step too", () => {
    renderWithTransport(
      buildWorkflow(stateWithPrompts, {
        transportMode: EDITORIAL_WORKFLOW_TRANSPORT_MODE.DISCONNECTED,
      }),
      CREATE_STEP_IDS.CONTENT,
    );

    expect(screen.getByTestId("live-updates-disconnected")).toBeInTheDocument();
  });

  it("hides the disconnected state while the stream is live", () => {
    renderWithTransport(buildWorkflow(stateWithPrompts));

    expect(
      screen.queryByTestId("live-updates-disconnected"),
    ).not.toBeInTheDocument();
  });
});
