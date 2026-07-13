// AE-0310 — Gherkin: backend/tests/features/carousel_design_phase_recovery.feature
// Scenario: Reviewer edits the flagged slide in place at design
// Scenario: Reviewer sends the workflow back to content from design
// Scenario: Plain design revise re-validates instead of looping
//   And the re-interrupt payload carries a client-displayable hint
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import {
  DESIGN_VALIDATION_RECOVERY_HINT,
  EDITORIAL_PHASES,
} from "@/constants/editorial-workflow";
import { WORKFLOW_PHASE_STATUS } from "@/constants/workflow";
import type {
  EditorialWorkflowState,
  SlideValidationReport,
} from "@/modules/editorial";
import { DesignPhaseReview } from "./design-phase-review";
import type { DesignRecoveryActions } from "./design-recovery-panel";

const blockingReport: SlideValidationReport = {
  validation_status: "invalid",
  validated_at: "2026-07-07T00:00:00.000Z",
  blocking: true,
  violations: [
    {
      code: "drafting_scaffold_present",
      message: "Slide copy still contains drafting scaffold labels",
      slide_index: 4,
      locale: "pt",
      field: "body",
    },
  ],
};

const baseState: EditorialWorkflowState = {
  project_id: "38affb3e",
  current_phase: EDITORIAL_PHASES.DESIGN,
  phase_status: WORKFLOW_PHASE_STATUS.AWAITING_HUMAN,
  research_findings: [],
  outline: [],
  slide_drafts: [],
  status: "draft",
  design_applied: true,
  localized_slides: [
    {
      slide_index: 1,
      slide_type: "intro",
      presentation_pt: { heading: "Titulo 1", body: "Corpo 1" },
      presentation_en: { heading: "Title 1", body: "Body 1" },
    },
    {
      slide_index: 4,
      slide_type: "hero_content",
      presentation_pt: { heading: "Titulo 4", body: "SLIDE 4: rascunho" },
      presentation_en: { heading: "Title 4", body: "Body 4" },
    },
  ],
  presentation_validation: blockingReport,
  design_recovery_hint: DESIGN_VALIDATION_RECOVERY_HINT,
};

function recoveryActions(): DesignRecoveryActions {
  return {
    onSubmitEditedSlides: vi.fn(),
    onSendBackToContent: vi.fn(),
  };
}

describe("DesignPhaseReview recovery (AE-0310)", () => {
  it("renders violations and the backend hint while blocking", () => {
    render(
      <DesignPhaseReview state={baseState} recovery={recoveryActions()} />,
    );

    expect(
      screen.getByText("Content violations are blocking the design step"),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Fix these violations by editing the slide copy/),
    ).toBeInTheDocument();
    expect(screen.getByText("Presentation violations")).toBeInTheDocument();
    expect(screen.getByText("drafting_scaffold_present")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Edit slide copy" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Send back to content" }),
    ).toBeInTheDocument();
  });

  it("hides the recovery panel when no blocking report exists", () => {
    const cleanState: EditorialWorkflowState = {
      ...baseState,
      presentation_validation: {
        ...blockingReport,
        blocking: false,
        validation_status: "valid",
        violations: [],
      },
      design_recovery_hint: null,
    };

    render(
      <DesignPhaseReview state={cleanState} recovery={recoveryActions()} />,
    );

    expect(
      screen.queryByRole("button", { name: "Edit slide copy" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByText("Content violations are blocking the design step"),
    ).not.toBeInTheDocument();
  });

  it("submits edited copy for the flagged slide only", async () => {
    const user = userEvent.setup();
    const recovery = recoveryActions();

    render(<DesignPhaseReview state={baseState} recovery={recovery} />);

    await user.click(screen.getByRole("button", { name: "Edit slide copy" }));

    // Only the flagged slide (4) is editable — slide 1 has no editor.
    expect(
      screen.getByLabelText("Body", {
        selector: "#recovery-4-presentation_pt-body",
      }),
    ).toBeInTheDocument();
    expect(
      document.querySelector("#recovery-1-presentation_pt-body"),
    ).not.toBeInTheDocument();

    const bodyInput = screen.getByLabelText("Body", {
      selector: "#recovery-4-presentation_pt-body",
    });
    await user.clear(bodyInput);
    await user.type(bodyInput, "Corpo corrigido");
    await user.click(
      screen.getByRole("button", { name: "Submit edited copy" }),
    );

    expect(recovery.onSubmitEditedSlides).toHaveBeenCalledTimes(1);
    const submitted = vi.mocked(recovery.onSubmitEditedSlides).mock.calls[0][0];
    const slideFour = submitted.find((slide) => slide.slide_index === 4);
    expect(slideFour?.presentation_pt.body).toBe("Corpo corrigido");
  });

  it("requires feedback before sending back to content", async () => {
    const user = userEvent.setup();
    const recovery = recoveryActions();

    render(<DesignPhaseReview state={baseState} recovery={recovery} />);

    await user.click(
      screen.getByRole("button", { name: "Send back to content" }),
    );
    await user.click(screen.getByRole("button", { name: "Send back" }));

    expect(recovery.onSendBackToContent).not.toHaveBeenCalled();
    expect(
      screen.getByText(
        "Feedback is required to send the workflow back to content.",
      ),
    ).toBeInTheDocument();
  });

  it("sends back to content with the typed feedback", async () => {
    const user = userEvent.setup();
    const recovery = recoveryActions();

    render(<DesignPhaseReview state={baseState} recovery={recovery} />);

    await user.click(
      screen.getByRole("button", { name: "Send back to content" }),
    );
    await user.type(
      screen.getByLabelText("Feedback for content regeneration"),
      "Remove scaffold text from slide 4",
    );
    await user.click(screen.getByRole("button", { name: "Send back" }));

    expect(recovery.onSendBackToContent).toHaveBeenCalledWith(
      "Remove scaffold text from slide 4",
    );
  });
});
