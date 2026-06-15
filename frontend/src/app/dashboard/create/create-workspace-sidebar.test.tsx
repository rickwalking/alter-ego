import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { CreateWorkspaceSidebar } from "./create-workspace-sidebar";
import { WORKFLOW_PHASE_STATUS } from "@/constants/workflow";
import type { CarouselProjectResponse } from "@/schemas/carousel";
import type { EditorialWorkflowState } from "@/features/blog/types-ai";

const project = {
  topic: "AI safety",
  audience: "Engineers",
  niche: "Security",
} as unknown as CarouselProjectResponse;

const baseState: EditorialWorkflowState = {
  project_id: "p1",
  current_phase: "content",
  phase_status: WORKFLOW_PHASE_STATUS.IN_PROGRESS,
  research_findings: [],
  outline: [],
  slide_drafts: [],
  status: "draft",
};

// Feature: Workflow Error Feedback & Retry (AE-0009)
describe("CreateWorkspaceSidebar", () => {
  // Scenario: Sidebar shows failure badge
  //   Given the editorial workflow has phase_status "failed"
  //   When the sidebar renders
  //   Then a "(failed)" badge is shown next to the current phase name
  it("shows a (failed) badge next to the current phase when failed", () => {
    render(
      <CreateWorkspaceSidebar
        project={project}
        workflowState={{
          ...baseState,
          phase_status: WORKFLOW_PHASE_STATUS.FAILED,
        }}
        activeStepId="outline"
        projectId="p1"
      />,
    );

    expect(screen.getByText("(failed)")).toBeInTheDocument();
    expect(screen.getAllByText("content").length).toBeGreaterThan(0);
  });

  // Scenario: Non-failed workflow shows existing behavior
  //   Given the editorial workflow is in "in_progress"
  //   When the sidebar renders
  //   Then no failure badge is shown
  it("does not show the failed badge when the phase is in progress", () => {
    render(
      <CreateWorkspaceSidebar
        project={project}
        workflowState={baseState}
        activeStepId="outline"
        projectId="p1"
      />,
    );

    expect(screen.queryByText("(failed)")).not.toBeInTheDocument();
  });
});
