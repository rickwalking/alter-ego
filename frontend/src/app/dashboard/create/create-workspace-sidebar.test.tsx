import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { CreateWorkspaceSidebar } from "./create-workspace-sidebar";
import { WORKFLOW_PHASE_STATUS } from "@/constants/workflow";
import { NEON_CYAN, NEON_RED } from "@/constants/neon";
import type { CarouselProjectResponse } from "@/schemas/carousel";
import type { EditorialWorkflowState } from "@/modules/publishing";

/** The active-phase status badge renders the phase name as its label. */
function phaseBadge(): HTMLElement | undefined {
  return screen
    .getAllByRole("status")
    .find((badge) => badge.textContent === "content");
}

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
  // Scenario: Sidebar shows failure via the red status badge (AE-0284 v2)
  //   Given the editorial workflow has phase_status "failed"
  //   When the sidebar renders
  //   Then the active-phase status badge uses the red (error) variant
  it("shows the current phase as a red (failed) status badge when failed", () => {
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

    const badge = phaseBadge();
    expect(badge).toBeDefined();
    expect(badge).toHaveStyle({ color: NEON_RED });
  });

  // Scenario: Non-failed workflow shows the live (cyan) state, not the error red
  //   Given the editorial workflow is in "in_progress"
  //   When the sidebar renders
  //   Then the active-phase status badge uses the cyan (live) variant
  it("shows the in-progress phase as a cyan (live) badge, not red", () => {
    render(
      <CreateWorkspaceSidebar
        project={project}
        workflowState={baseState}
        activeStepId="outline"
        projectId="p1"
      />,
    );

    const badge = phaseBadge();
    expect(badge).toBeDefined();
    expect(badge).toHaveStyle({ color: NEON_CYAN });
  });
});
