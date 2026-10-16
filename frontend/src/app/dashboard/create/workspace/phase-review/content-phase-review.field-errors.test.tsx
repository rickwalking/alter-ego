// AE-0403 — Gherkin: frontend/tests/features/review-form-field-errors.feature
// Scenario: Manual fixes at the content step save without approving
import { fireEvent, render, screen } from "@testing-library/react";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";
import { EDITORIAL_PHASES } from "@/constants/editorial-workflow";
import { WORKFLOW_PHASE_STATUS } from "@/constants/workflow";
import type {
  EditorialWorkflowState,
  LocalizedSlideReview,
  SlideValidationViolation,
} from "@/modules/editorial";
import {
  ContentPhaseReview,
  type ContentManualFixesActions,
} from "./content-phase-review";

const EN_BODY_ID = "#slide-9-presentation_en-body";

function stateWith(
  violations: SlideValidationViolation[],
  lockVersion = 1,
): EditorialWorkflowState {
  return {
    project_id: "project-1",
    current_phase: EDITORIAL_PHASES.CONTENT,
    phase_status: WORKFLOW_PHASE_STATUS.AWAITING_HUMAN,
    research_findings: [],
    outline: [],
    slide_drafts: [],
    status: "draft",
    lock_version: lockVersion,
    localized_slides: [
      {
        slide_index: 9,
        slide_type: "content",
        presentation_pt: { heading: "Título", body: "Corpo **forte**." },
        presentation_en: { heading: "Title", body: "Body <strong>x" },
      },
    ],
    presentation_validation: {
      validation_status: violations.length ? "invalid" : "valid",
      validated_at: `2026-10-16T00:00:0${lockVersion}Z`,
      blocking: violations.length > 0,
      violations,
    },
  };
}

const emphasis: SlideValidationViolation = {
  code: "emphasis_markup_invalid",
  message: "Emphasis must use balanced <strong>...</strong> tags only",
  slide_index: 9,
  locale: "en",
  field: "body",
};

function field(selector: string): HTMLTextAreaElement {
  const element = document.querySelector<HTMLTextAreaElement>(selector);
  if (!element) {
    throw new Error(`missing field ${selector}`);
  }
  return element;
}

function Harness({
  state,
  manualFixes,
}: {
  state: EditorialWorkflowState;
  manualFixes?: ContentManualFixesActions;
}): React.ReactElement {
  const [slides, setSlides] = useState<LocalizedSlideReview[] | undefined>();
  return (
    <ContentPhaseReview
      state={state}
      editable
      slides={slides}
      onSlidesChange={setSlides}
      manualFixes={manualFixes}
    />
  );
}

describe("ContentPhaseReview field errors (AE-0403)", () => {
  it("flags the field, summarises the slide and clears the error on edit", () => {
    render(<Harness state={stateWith([emphasis])} />);

    const body = field(EN_BODY_ID);
    expect(body).toHaveAttribute("aria-invalid", "true");
    expect(
      document.getElementById(body.getAttribute("aria-describedby") ?? ""),
    ).toHaveTextContent("Emphasis must use balanced <strong>…</strong> tags");
    expect(
      screen.getByRole("list", { name: "Slide 9 errors" }),
    ).toHaveTextContent("Slide 9 · EN body: Emphasis must use balanced");

    fireEvent.change(body, { target: { value: "Body <strong>x</strong>" } });
    expect(field(EN_BODY_ID)).not.toHaveAttribute("aria-invalid");
    expect(
      screen.queryByRole("list", { name: "Slide 9 errors" }),
    ).not.toBeInTheDocument();
  });

  it("submits manual fixes with the edited slides (no approval)", () => {
    const onSubmit = vi.fn();
    render(
      <Harness state={stateWith([emphasis])} manualFixes={{ onSubmit }} />,
    );

    const submit = screen.getByRole("button", { name: "Submit manual fixes" });
    expect(submit).toBeDisabled();
    expect(screen.getByText(/does not approve the step/)).toBeInTheDocument();
    fireEvent.change(field(EN_BODY_ID), {
      target: { value: "Body <strong>x</strong>" },
    });
    fireEvent.click(
      screen.getByRole("button", { name: "Submit manual fixes" }),
    );

    expect(onSubmit).toHaveBeenCalledTimes(1);
    const [slides] = onSubmit.mock.calls[0] as [LocalizedSlideReview[]];
    expect(slides[0]?.presentation_en.body).toBe("Body <strong>x</strong>");
  });

  it("shows the new field errors and focuses them after a refused resubmit", () => {
    const onSubmit = vi.fn();
    const { rerender } = render(
      <Harness state={stateWith([emphasis])} manualFixes={{ onSubmit }} />,
    );
    fireEvent.change(field(EN_BODY_ID), {
      target: { value: "Body <strong>x</strong>" },
    });
    fireEvent.click(
      screen.getByRole("button", { name: "Submit manual fixes" }),
    );

    const heading: SlideValidationViolation = {
      ...emphasis,
      code: "heading_not_sentence_case_en",
      message: "English heading must start with an uppercase letter",
      field: "heading",
    };
    rerender(
      <Harness state={stateWith([heading], 2)} manualFixes={{ onSubmit }} />,
    );

    const headingField = field("#slide-9-presentation_en-heading");
    expect(headingField).toHaveAttribute("aria-invalid", "true");
    expect(document.activeElement).toBe(headingField);
  });

  it("brings an edited field's error back on a new validation run", () => {
    const { rerender } = render(<Harness state={stateWith([emphasis])} />);
    fireEvent.change(field(EN_BODY_ID), { target: { value: "Still bad" } });
    expect(field(EN_BODY_ID)).not.toHaveAttribute("aria-invalid");

    rerender(<Harness state={stateWith([emphasis], 2)} />);
    expect(field(EN_BODY_ID)).toHaveAttribute("aria-invalid", "true");
  });

  it("hides the manual-fixes footer when nothing blocks the step", () => {
    render(
      <Harness state={stateWith([])} manualFixes={{ onSubmit: vi.fn() }} />,
    );
    expect(
      screen.queryByRole("button", { name: "Submit manual fixes" }),
    ).not.toBeInTheDocument();
    expect(document.querySelector("[aria-invalid]")).toBeNull();
  });

  it("labels the button while the manual fixes are submitting", () => {
    render(
      <Harness
        state={stateWith([emphasis])}
        manualFixes={{ onSubmit: vi.fn(), submitting: true }}
      />,
    );
    expect(
      screen.getByRole("button", { name: "Submitting fixes…" }),
    ).toBeDisabled();
  });
});
