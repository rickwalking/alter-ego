import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { EDITORIAL_PHASES } from "@/constants/editorial-workflow";
import { WORKFLOW_PHASE_STATUS } from "@/constants/workflow";
import { EditorialWorkflowProgress } from "@/features/create/components/editorial-workflow-progress";
import type { EditorialWorkflowState } from "@/features/blog/types-ai";
import en from "@/i18n/locales/en.json";

function renderProgress(
  state: EditorialWorkflowState | null,
  loading = false,
): void {
  render(
    <NextIntlClientProvider locale="en" messages={en}>
      <EditorialWorkflowProgress state={state} loading={loading} />
    </NextIntlClientProvider>,
  );
}

describe("EditorialWorkflowProgress", () => {
  // Scenario: Progress strip active during in_progress only
  it("shows progress while generation is in progress", () => {
    const state: EditorialWorkflowState = {
      project_id: "project-1",
      current_phase: EDITORIAL_PHASES.IMAGES,
      phase_status: WORKFLOW_PHASE_STATUS.IN_PROGRESS,
      research_findings: [],
      outline: [],
      slide_drafts: [],
      image_assets: [],
      design_applied: false,
      lock_version: 1,
      status: "draft",
      phase_progress: {
        phase: "images",
        label: "Generating images",
        detail: "Slide 2 of 5",
        current: 2,
        total: 5,
      },
    };

    renderProgress(state);

    expect(screen.getByTestId("phase-progress-label")).toHaveTextContent(
      "Generating images",
    );
    expect(screen.getByText("2 / 5")).toBeInTheDocument();
  });

  // Scenario: No progress polling loop at awaiting_human gate
  it("renders nothing while awaiting human review", () => {
    const state: EditorialWorkflowState = {
      project_id: "project-1",
      current_phase: EDITORIAL_PHASES.DESIGN,
      phase_status: WORKFLOW_PHASE_STATUS.AWAITING_HUMAN,
      research_findings: [],
      outline: [],
      slide_drafts: [],
      image_assets: [],
      design_applied: true,
      lock_version: 1,
      status: "draft",
    };

    const { container } = render(
      <NextIntlClientProvider locale="en" messages={en}>
        <EditorialWorkflowProgress state={state} loading={false} />
      </NextIntlClientProvider>,
    );

    expect(container).toBeEmptyDOMElement();
  });

  // Scenario: Reload restores persisted phase progress snapshot
  it("uses persisted phase progress snapshot from workflow state", () => {
    const state: EditorialWorkflowState = {
      project_id: "project-1",
      current_phase: EDITORIAL_PHASES.IMAGES,
      phase_status: WORKFLOW_PHASE_STATUS.IN_PROGRESS,
      research_findings: [],
      outline: [],
      slide_drafts: [],
      image_assets: [],
      design_applied: false,
      lock_version: 1,
      status: "draft",
      phase_progress: {
        phase: "images",
        label: "Generating images",
        detail: "Halfway through image batch",
        current: 3,
        total: 6,
      },
    };

    renderProgress(state);

    expect(screen.getByTestId("phase-progress-label")).toHaveTextContent(
      "Generating images",
    );
    expect(screen.getByText("50%")).toBeInTheDocument();
  });
});
