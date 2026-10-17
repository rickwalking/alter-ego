import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { WORKFLOW_PHASE_STATUS } from "@/constants/workflow";
import type { EditorialWorkflowState } from "@/modules/publishing";
import { CreateWorkflowProgress } from "./create-workflow-progress";

function state(
  overrides: Partial<EditorialWorkflowState>,
): EditorialWorkflowState {
  return {
    project_id: "p1",
    current_phase: "final_review",
    phase_status: WORKFLOW_PHASE_STATUS.IN_PROGRESS,
    research_findings: [],
    outline: [],
    slide_drafts: [],
    status: "draft",
    phase_progress: { phase: "exporting", label: "Exporting slides…" },
    ...overrides,
  };
}

// Feature: Create-flow UI fixes (AE-0415)
describe("CreateWorkflowProgress", () => {
  // Scenario: An approved project shows no stale "in progress" panel
  it("hides a leftover progress label once the run is over", () => {
    const { container } = render(
      <CreateWorkflowProgress
        state={state({
          phase_status: WORKFLOW_PHASE_STATUS.APPROVED,
          workflow_status: "approved_for_publish",
        })}
        loading={false}
      />,
    );
    expect(container).toBeEmptyDOMElement();
  });

  // Scenario: The banner names the phase that is running
  it("shows the live progress detail once, without the legacy step list", () => {
    render(
      <CreateWorkflowProgress
        state={state({
          phase_progress: {
            phase: "drafting",
            label: "Drafting slide copy",
            current: 2,
            total: 8,
          },
        })}
        loading={false}
      />,
    );
    expect(screen.getAllByText("Drafting slide copy")).toHaveLength(1);
    expect(screen.getByText("2 / 8")).toBeInTheDocument();
    expect(screen.queryByText(/Researching topic/i)).not.toBeInTheDocument();
  });

  it("renders nothing while running without a progress label", () => {
    const { container } = render(
      <CreateWorkflowProgress
        state={state({ phase_progress: null })}
        loading
      />,
    );
    expect(container).toBeEmptyDOMElement();
  });
});
