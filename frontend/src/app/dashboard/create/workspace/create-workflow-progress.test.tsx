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

/**
 * Scenarios: tests/features/workflow-stream-recovery-ae0440.feature.
 * In production phase_progress was never cleared when the images phase ended.
 */
describe("CreateWorkflowProgress stale phase progress (AE-0440)", () => {
  const imagesProgress = {
    phase: "generating_images",
    label: "Generating 4 slide images in parallel",
    current: 4,
    total: 4,
    slides: [{ number: 1, status: "done" as const }],
  };

  // Scenario: Image progress of a past phase is not shown as live work
  it("hides image progress while a later send-back runs the content phase", () => {
    const { container } = render(
      <CreateWorkflowProgress
        state={state({
          current_phase: "content",
          phase_progress: imagesProgress,
        })}
        loading={false}
      />,
    );
    expect(container).toBeEmptyDOMElement();
  });

  it("hides image progress while an approval of final review is loading", () => {
    const { container } = render(
      <CreateWorkflowProgress
        state={state({
          phase_status: WORKFLOW_PHASE_STATUS.AWAITING_HUMAN,
          phase_progress: imagesProgress,
        })}
        loading
      />,
    );
    expect(container).toBeEmptyDOMElement();
  });

  it("hides progress tagged with another editorial phase", () => {
    const { container } = render(
      <CreateWorkflowProgress
        state={state({
          current_phase: "content",
          phase_progress: { phase: "outline", label: "Outlining" },
        })}
        loading={false}
      />,
    );
    expect(container).toBeEmptyDOMElement();
  });

  // Scenario: Image progress is shown while the images phase runs
  it("shows image progress while the images phase runs", () => {
    render(
      <CreateWorkflowProgress
        state={state({
          current_phase: "images",
          phase_progress: imagesProgress,
        })}
        loading={false}
      />,
    );
    expect(
      screen.getByText("Generating 4 slide images in parallel"),
    ).toBeInTheDocument();
    expect(screen.getByText("4 / 4")).toBeInTheDocument();
  });

  // Scenario: Progress without a phase tag is shown for the running phase
  it("shows untagged progress for the running phase", () => {
    render(
      <CreateWorkflowProgress
        state={state({
          current_phase: "images",
          phase_progress: { label: "Generating images", current: 1, total: 4 },
        })}
        loading={false}
      />,
    );
    expect(screen.getByText("Generating images")).toBeInTheDocument();
  });
});

/** `phase_progress` is untyped JSON from the API/SSE. */
describe("CreateWorkflowProgress malformed phase progress (AE-0446)", () => {
  it("renders nothing, instead of crashing, when the label is missing", () => {
    const { container } = render(
      <CreateWorkflowProgress
        state={state({ phase_progress: { phase: "exporting", current: 1 } })}
        loading={false}
      />,
    );
    expect(container).toBeEmptyDOMElement();
  });

  it("renders nothing when the label is not a string", () => {
    const { container } = render(
      <CreateWorkflowProgress
        state={state({ phase_progress: { label: 42 } })}
        loading={false}
      />,
    );
    expect(container).toBeEmptyDOMElement();
  });
});
