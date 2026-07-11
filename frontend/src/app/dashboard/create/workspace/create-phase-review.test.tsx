// Gherkin: backend/tests/features/carousel_deterministic_repair.feature
// Scenario: the "Fix issues automatically" button is rendered alongside the
// content-phase and design-phase violation panels.
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { EditorialWorkflowState } from "@/modules/publishing";
import { EDITORIAL_PHASES } from "@/constants/editorial-workflow";
import { CreatePhaseReview } from "./create-phase-review";

vi.mock("@/modules/editorial", () => ({
  AutoRepairButton: ({ projectId }: { projectId: string }) => (
    <div data-testid="auto-repair-button">{projectId}</div>
  ),
}));

vi.mock("./phase-review/research-phase-review", () => ({
  ResearchPhaseReview: () => <div>research</div>,
}));
vi.mock("./phase-review/outline-phase-review", () => ({
  OutlinePhaseReview: () => <div>outline</div>,
}));
vi.mock("./phase-review/content-phase-review", () => ({
  ContentPhaseReview: () => <div>content</div>,
}));
vi.mock("./phase-review/design-phase-review", () => ({
  DesignPhaseReview: () => <div>design</div>,
}));
vi.mock("./phase-review/images-phase-review", () => ({
  ImagesPhaseReview: () => <div>images</div>,
}));
vi.mock("./phase-review/final-review-phase-review", () => ({
  FinalReviewPhaseReview: () => <div>final</div>,
}));

const state = (phase: string): EditorialWorkflowState =>
  ({ current_phase: phase }) as EditorialWorkflowState;

describe("CreatePhaseReview auto-repair wiring", () => {
  it("renders the repair button alongside the content panel", () => {
    render(
      <CreatePhaseReview
        projectId="p1"
        state={state(EDITORIAL_PHASES.CONTENT)}
      />,
    );
    expect(screen.getByTestId("auto-repair-button")).toHaveTextContent("p1");
  });

  it("renders the repair button alongside the design panel", () => {
    render(
      <CreatePhaseReview
        projectId="p2"
        state={state(EDITORIAL_PHASES.DESIGN)}
      />,
    );
    expect(screen.getByTestId("auto-repair-button")).toHaveTextContent("p2");
  });

  it("does not render the repair button on the research panel", () => {
    render(
      <CreatePhaseReview
        projectId="p3"
        state={state(EDITORIAL_PHASES.RESEARCH)}
      />,
    );
    expect(screen.queryByTestId("auto-repair-button")).not.toBeInTheDocument();
  });
});
