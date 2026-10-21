import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@/test/utils";
import { EDITORIAL_PHASES } from "@/constants/editorial-workflow";
import { WORKFLOW_PHASE_STATUS } from "@/constants/workflow";
import type { EditorialWorkflowState } from "@/modules/editorial";
import { OutlinePhaseReview } from "./outline-phase-review";

// Gherkin: backend/tests/features/carousel_pov_prompts.feature (AE-0375)
vi.mock("@/modules/editorial/workspace/hooks/use-save-hook", () => ({
  useSaveCarouselHook: () => ({
    mutate: vi.fn(),
    isPending: false,
    isSuccess: false,
    isError: false,
  }),
}));

function stateWith(outline: Record<string, unknown>[]): EditorialWorkflowState {
  return {
    project_id: "project-1",
    current_phase: EDITORIAL_PHASES.OUTLINE,
    phase_status: WORKFLOW_PHASE_STATUS.AWAITING_HUMAN,
    research_findings: [],
    outline,
    slide_drafts: [],
    status: "draft",
  };
}

const POV_OUTLINE = [
  {
    slide_index: 1,
    title: "Pare de pedir código pra IA",
    key_points: [],
    role: "hook",
    hook_candidates: ["Pare de pedir código pra IA", "Outro gancho"],
    outline_checks: { thesis_early: false },
  },
  { slide_index: 2, title: "Tensão", key_points: ["a"], role: "rehook" },
];

describe("OutlinePhaseReview hook picker (AE-0375)", () => {
  it("shows the hook picker for an outline with candidates", () => {
    render(
      <OutlinePhaseReview
        state={stateWith(POV_OUTLINE)}
        projectId="project-1"
      />,
    );
    expect(screen.getByTestId("hook-picker")).toBeInTheDocument();
    expect(
      screen.getByRole("radio", { name: "Outro gancho" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("note")).toBeInTheDocument();
  });

  it("hides the picker without candidates or without a project id", () => {
    const legacy = [{ slide_index: 1, title: "Titulo", key_points: [] }];
    const { rerender } = render(
      <OutlinePhaseReview state={stateWith(legacy)} projectId="project-1" />,
    );
    expect(screen.queryByTestId("hook-picker")).not.toBeInTheDocument();
    rerender(<OutlinePhaseReview state={stateWith(POV_OUTLINE)} />);
    expect(screen.queryByTestId("hook-picker")).not.toBeInTheDocument();
  });

  it("still lists the outline slides", () => {
    render(
      <OutlinePhaseReview
        state={stateWith(POV_OUTLINE)}
        projectId="project-1"
      />,
    );
    expect(screen.getByText("Tensão")).toBeInTheDocument();
  });
});
