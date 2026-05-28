import { describe, it, expect, vi, beforeEach } from "vitest";
import { readFileSync } from "node:fs";
import path from "node:path";
import { render, screen, fireEvent, waitFor, act } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import {
  EDITORIAL_PHASES,
  EDITORIAL_WORKFLOW_STATUS,
} from "@/constants/editorial-workflow";
import { WORKFLOW_PHASE_STATUS } from "@/constants/workflow";
import { EditorialWorkflowPanel } from "@/features/create/components/editorial-workflow-panel";
import type { EditorialWorkflowState } from "@/features/blog/types-ai";
import en from "@/i18n/locales/en.json";

const mockRevise = vi.fn().mockImplementation(() => Promise.resolve());
const mockApprove = vi.fn().mockResolvedValue(undefined);
const mockStart = vi.fn().mockResolvedValue(undefined);

const finalReviewState: EditorialWorkflowState = {
  project_id: "project-1",
  current_phase: EDITORIAL_PHASES.FINAL_REVIEW,
  phase_status: WORKFLOW_PHASE_STATUS.AWAITING_HUMAN,
  research_findings: [],
  outline: [],
  slide_drafts: [],
  image_assets: [],
  design_applied: false,
  lock_version: 1,
  status: "draft",
};

function renderPanel(
  state: EditorialWorkflowState | null = finalReviewState,
): void {
  render(
    <NextIntlClientProvider locale="en" messages={en}>
      <EditorialWorkflowPanel
        projectId="project-1"
        topic="Topic"
        audience="Audience"
        brief="Brief"
        workflow={{
          state,
          phaseEvents: [EDITORIAL_PHASES.FINAL_REVIEW],
          loading: false,
          error: null,
          transportMode: "sse",
          start: mockStart,
          resume: vi.fn(),
          refreshState: vi.fn(),
          approve: mockApprove,
          revise: mockRevise,
          awaitingHumanReview:
            state?.phase_status === WORKFLOW_PHASE_STATUS.AWAITING_HUMAN,
          hasActiveWorkflow: Boolean(state?.current_phase),
        }}
      />
    </NextIntlClientProvider>,
  );
}

describe("EditorialWorkflowPanel final review send-back", () => {
  beforeEach(() => {
    mockRevise.mockClear();
    mockApprove.mockClear();
  });

  // Scenario: Send final review back to content phase
  it("shows send-back phase picker at final review gate", () => {
    renderPanel();
    expect(
      screen.getByLabelText(en.editorialWorkflow.sendBack.label),
    ).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "Content" })).toBeInTheDocument();
  });

  it("submits structured_feedback.target_phase when requesting revision", async () => {
    renderPanel();

    fireEvent.change(screen.getByLabelText(en.editorialWorkflow.sendBack.label), {
      target: { value: EDITORIAL_PHASES.CONTENT },
    });
    fireEvent.change(screen.getByLabelText(en.editorialWorkflow.feedback.label), {
      target: { value: "Intro slide needs a personal anecdote" },
    });

    await act(async () => {
      fireEvent.click(
        screen.getByRole("button", {
          name: en.editorialWorkflow.actions.requestRevision,
        }),
      );
    });

    await waitFor(() => {
      expect(mockRevise).toHaveBeenCalledWith(
        "Intro slide needs a personal anecdote",
        { targetPhase: EDITORIAL_PHASES.CONTENT },
      );
    });
  });

  // Scenario: Request revision requires feedback text
  it("blocks revision when feedback is empty", async () => {
    renderPanel();

    fireEvent.click(
      screen.getByRole("button", {
        name: en.editorialWorkflow.actions.requestRevision,
      }),
    );

    expect(mockRevise).not.toHaveBeenCalled();
    expect(
      await screen.findByText(en.editorialWorkflow.feedback.required),
    ).toBeInTheDocument();
  });
});

describe("EditorialWorkflowPanel persona and publish gating", () => {
  // Scenario: Content approve disabled when persona score below threshold
  it("disables approve when persona score is below threshold", () => {
    const contentState: EditorialWorkflowState = {
      project_id: "project-1",
      current_phase: EDITORIAL_PHASES.CONTENT,
      phase_status: WORKFLOW_PHASE_STATUS.AWAITING_HUMAN,
      research_findings: [],
      outline: [],
      slide_drafts: [{ title: "Intro", draft_text: "Body" }],
      image_assets: [],
      design_applied: false,
      lock_version: 1,
      status: "draft",
      persona_scores: { default: { overall: 65 } },
    };

    render(
      <NextIntlClientProvider locale="en" messages={en}>
        <EditorialWorkflowPanel
          projectId="project-1"
          topic="Topic"
          audience="Audience"
          brief="Brief"
          workflow={{
            state: contentState,
            phaseEvents: [EDITORIAL_PHASES.CONTENT],
            loading: false,
            error: null,
            transportMode: "sse",
            start: mockStart,
            resume: vi.fn(),
            refreshState: vi.fn(),
            approve: mockApprove,
            revise: mockRevise,
            awaitingHumanReview: true,
            hasActiveWorkflow: true,
          }}
        />
      </NextIntlClientProvider>,
    );

    expect(
      screen.getByRole("button", { name: en.editorialWorkflow.actions.approve }),
    ).toBeDisabled();
    expect(
      screen.getByText(en.editorialWorkflow.persona.belowThreshold),
    ).toBeInTheDocument();
  });

  // Scenario: Publish panel appears after final review approval
  it("shows publish-ready guidance when workflow is approved for publish", () => {
    render(
      <NextIntlClientProvider locale="en" messages={en}>
        <EditorialWorkflowPanel
          projectId="project-1"
          topic="Topic"
          audience="Audience"
          brief="Brief"
          workflow={{
            state: {
              ...finalReviewState,
              workflow_status: EDITORIAL_WORKFLOW_STATUS.APPROVED_FOR_PUBLISH,
            },
            phaseEvents: [EDITORIAL_PHASES.FINAL_REVIEW],
            loading: false,
            error: null,
            transportMode: "sse",
            start: mockStart,
            resume: vi.fn(),
            refreshState: vi.fn(),
            approve: mockApprove,
            revise: mockRevise,
            awaitingHumanReview: false,
            hasActiveWorkflow: true,
          }}
        />
      </NextIntlClientProvider>,
    );

    expect(
      screen.getByText(en.editorialWorkflow.publishReady),
    ).toBeInTheDocument();
  });
});

describe("Editorial workflow legacy constants", () => {
  // Scenario: Create workspace does not reference legacy stream constants
  it("uses workflow stream endpoint only in api constants", () => {
    const apiConstantsPath = path.resolve(process.cwd(), "src/constants/api.ts");
    const progressSource = readFileSync(
      path.resolve(
        process.cwd(),
        "src/features/create/components/editorial-workflow-progress.tsx",
      ),
      "utf8",
    );
    const hookSource = readFileSync(
      path.resolve(
        process.cwd(),
        "src/features/create/hooks/use-editorial-workflow.ts",
      ),
      "utf8",
    );
    const apiSource = readFileSync(apiConstantsPath, "utf8");

    expect(apiSource).not.toContain("CAROUSEL_STREAM");
    expect(apiSource).not.toContain("CAROUSEL_GENERATE");
    expect(apiSource).toContain("CAROUSEL_WORKFLOW_STREAM");
    expect(progressSource).not.toContain("CAROUSEL_STREAM");
    expect(hookSource).toContain("CAROUSEL_WORKFLOW_STREAM");
  });
});
