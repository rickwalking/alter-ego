// AE-0309 — Gherkin: backend/tests/features/carousel_content_fail_closed.feature
// Scenario: Unrepairable slide surfaces at the content review step
//   Then the interrupt payload carries a blocking violation for that slide
//   And the content step UI shows the slide number and violation messages
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { EDITORIAL_PHASES } from "@/constants/editorial-workflow";
import { WORKFLOW_PHASE_STATUS } from "@/constants/workflow";
import type {
  EditorialWorkflowState,
  SlideValidationReport,
} from "@/modules/editorial";
import { ContentPhaseReview } from "./content-phase-review";

const baseState: EditorialWorkflowState = {
  project_id: "project-1",
  current_phase: EDITORIAL_PHASES.CONTENT,
  phase_status: WORKFLOW_PHASE_STATUS.AWAITING_HUMAN,
  research_findings: [],
  outline: [],
  slide_drafts: [],
  status: "draft",
  localized_slides: [
    {
      slide_index: 4,
      slide_type: "content",
      presentation_pt: {
        slide_type: "content",
        heading: "Fluxo editorial",
        body: "",
      },
      presentation_en: {
        slide_type: "content",
        heading: "Editorial flow",
        body: "",
      },
    },
  ],
};

const gateReport: SlideValidationReport = {
  validation_status: "invalid",
  validated_at: "2026-07-10T00:00:00.000Z",
  blocking: true,
  violations: [
    {
      code: "slide_parse_failed",
      message: "Slide copy could not be parsed from the draft output",
      slide_index: 4,
      locale: "pt",
      field: "body",
    },
  ],
};

describe("ContentPhaseReview content-gate violations (AE-0309)", () => {
  it("renders gate violations from the content interrupt payload", () => {
    const state: EditorialWorkflowState = {
      ...baseState,
      content_gate_validation: gateReport,
    };

    render(<ContentPhaseReview state={state} />);

    expect(
      screen.getByText(
        "Automatic drafting could not produce valid copy for some slides after repair and one retry. Review the violations below before approving.",
      ),
    ).toBeInTheDocument();
    expect(screen.getByText("Presentation violations")).toBeInTheDocument();
    expect(screen.getByText("slide_parse_failed")).toBeInTheDocument();
    const violation = screen.getByText("slide_parse_failed").closest("li");
    expect(violation).toHaveTextContent("Slide 4");
    expect(violation).toHaveTextContent("PT");
    expect(violation).toHaveTextContent(
      "Slide copy could not be parsed from the draft output",
    );
  });

  it("de-duplicates violations mirrored in both reports", () => {
    const state: EditorialWorkflowState = {
      ...baseState,
      presentation_validation: gateReport,
      content_gate_validation: gateReport,
    };

    render(<ContentPhaseReview state={state} />);

    expect(screen.getAllByText("slide_parse_failed")).toHaveLength(1);
  });

  it("shows no gate alert when the content gate report is absent", () => {
    render(<ContentPhaseReview state={baseState} />);

    expect(
      screen.queryByText(
        "Automatic drafting could not produce valid copy for some slides after repair and one retry. Review the violations below before approving.",
      ),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByText("Presentation violations"),
    ).not.toBeInTheDocument();
  });

  // AE-0312 — Gherkin: backend/tests/features/carousel_pt_casing_severity.feature
  // Scenario: warning-tier violations render distinctly from blockers.
  it("labels warning-severity casing violations as non-blocking warnings", () => {
    const warningReport: SlideValidationReport = {
      validation_status: "invalid",
      validated_at: "2026-07-10T00:00:00.000Z",
      blocking: false,
      violations: [
        {
          code: "heading_not_sentence_case_pt",
          message: "Portuguese heading must start with an uppercase letter",
          slide_index: 4,
          locale: "pt",
          field: "heading",
          severity: "warning",
        },
      ],
    };
    const state: EditorialWorkflowState = {
      ...baseState,
      presentation_validation: warningReport,
    };

    render(<ContentPhaseReview state={state} />);

    const violation = screen
      .getByText("heading_not_sentence_case_pt")
      .closest("li");
    expect(violation).toHaveTextContent("Warning");
    expect(violation?.className).not.toContain("destructive");
    // A non-blocking report must not raise the approval-blocked alert.
    expect(
      screen.queryByText(
        "Approval is blocked until all presentation violations are resolved.",
      ),
    ).not.toBeInTheDocument();
  });
});
