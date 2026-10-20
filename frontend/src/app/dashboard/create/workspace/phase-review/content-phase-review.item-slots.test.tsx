// AE-0437 — Gherkin: frontend/tests/features/content-review-item-slots-ae0437.feature
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

const ACTIONS = [
  { icon_name: "target", title: "Teste", body: "Um comando." },
  { icon_name: "eye", title: "Leia", body: "Cada passo." },
  { icon_name: "wrench", title: "Amplie", body: "Aos poucos." },
];

const closingMissing: SlideValidationViolation = {
  code: "closing_actions_missing",
  message: "Closing slide needs at least 3 actions",
  slide_index: 6,
  locale: "pt",
  field: "body",
};

function closing(
  pt: Record<string, unknown>,
  en: Record<string, unknown>,
): LocalizedSlideReview {
  return {
    slide_index: 6,
    slide_type: "closing",
    presentation_pt: { heading: "Comece", body: "", ...pt },
    presentation_en: { heading: "Start", body: "", ...en },
  };
}

function intro(): LocalizedSlideReview {
  return {
    slide_index: 1,
    slide_type: "intro",
    presentation_pt: {
      heading: "Gancho",
      body: "Corpo.",
      tldr_strip: "Resumo",
    },
    presentation_en: { heading: "Hook", body: "Body.", tldr_strip: "Resumo" },
  };
}

function stateWith(
  slides: LocalizedSlideReview[],
  violations: SlideValidationViolation[],
): EditorialWorkflowState {
  return {
    project_id: "project-1",
    current_phase: EDITORIAL_PHASES.CONTENT,
    phase_status: WORKFLOW_PHASE_STATUS.AWAITING_HUMAN,
    research_findings: [],
    outline: [],
    slide_drafts: [],
    status: "draft",
    lock_version: 1,
    presentation_policy_version: "hero_lower_third_v4",
    localized_slides: slides,
    presentation_validation: {
      validation_status: violations.length ? "invalid" : "valid",
      validated_at: "2026-10-19T00:00:01Z",
      blocking: violations.length > 0,
      violations,
    },
  };
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

function field(id: string): HTMLTextAreaElement {
  const element = document.getElementById(id);
  if (!(element instanceof HTMLTextAreaElement)) {
    throw new Error(`missing field ${id}`);
  }
  return element;
}

describe("ContentPhaseReview — item slots (AE-0437)", () => {
  // Scenario: A closing slide without actions offers an "add action" slot
  it("offers an add-action slot instead of a raw empty extra", () => {
    render(
      <Harness
        state={stateWith(
          [closing({ actions: [] }, { actions: [] })],
          [closingMissing],
        )}
      />,
    );

    expect(screen.queryByText(/Structured field: actions/)).toBeNull();
    expect(screen.getAllByRole("button", { name: "Add Action" })).toHaveLength(
      2,
    );
  });

  // Scenario: Adding an action creates an empty slot in PT and EN
  it("adds an editable slot to PT and EN and submits it", () => {
    const onSubmit = vi.fn();
    render(
      <Harness
        state={stateWith(
          [closing({ actions: [] }, { actions: [] })],
          [closingMissing],
        )}
        manualFixes={{ onSubmit }}
      />,
    );

    fireEvent.click(screen.getAllByRole("button", { name: "Add Action" })[0]);
    const ptTitle = field("slide-6-presentation_pt-actions-0-title");
    expect(ptTitle.value).toBe("");
    expect(field("slide-6-presentation_en-actions-0-body").value).toBe("");
    fireEvent.change(ptTitle, { target: { value: "Teste" } });
    fireEvent.click(
      screen.getByRole("button", { name: "Submit manual fixes" }),
    );

    const [sent] = onSubmit.mock.calls[0] as [LocalizedSlideReview[]];
    expect(sent[0].presentation_pt.actions).toEqual([
      { icon_name: "target", title: "Teste", body: "" },
    ]);
    expect(sent[0].presentation_en.actions).toEqual([
      { icon_name: "target", title: "", body: "" },
    ]);
  });

  // Scenario: Removing an item removes the same position in PT and EN
  it("removes the same position in both columns", () => {
    render(
      <Harness
        state={stateWith(
          [closing({ actions: ACTIONS }, { actions: ACTIONS })],
          [closingMissing],
        )}
      />,
    );

    fireEvent.click(
      screen.getAllByRole("button", { name: "Remove Action 2" })[1],
    );

    expect(field("slide-6-presentation_pt-actions-1-title").value).toBe(
      "Amplie",
    );
    expect(field("slide-6-presentation_en-actions-1-title").value).toBe(
      "Amplie",
    );
    expect(
      document.getElementById("slide-6-presentation_pt-actions-2-title"),
    ).toBeNull();
  });

  // Scenario: A closing slide edits its actions, not a stray features list
  it("edits the closing actions in EN even when EN holds features", () => {
    render(
      <Harness
        state={stateWith(
          [closing({ actions: ACTIONS }, { features: ACTIONS })],
          [closingMissing],
        )}
      />,
    );

    expect(field("slide-6-presentation_en-actions-0-title").value).toBe("");
    expect(
      document.getElementById("slide-6-presentation_en-features-0-title"),
    ).toBeNull();
  });
});

describe("ContentPhaseReview — saving without a server block (AE-0437)", () => {
  // Scenario: Unsaved edits can be submitted when the server is not blocking
  it("shows the submit button for unsaved edits without the blocking hint", () => {
    const onSubmit = vi.fn();
    render(
      <Harness state={stateWith([intro()], [])} manualFixes={{ onSubmit }} />,
    );

    expect(
      screen.queryByRole("button", { name: "Submit manual fixes" }),
    ).toBeNull();
    fireEvent.change(field("slide-1-presentation_en-tldr_strip"), {
      target: { value: "Grok Bot books by phone" },
    });
    const submit = screen.getByRole("button", { name: "Submit manual fixes" });
    expect(submit).toBeEnabled();
    expect(screen.queryByRole("button", { name: "Slide 1" })).toBeNull();
    fireEvent.click(submit);

    const [sent] = onSubmit.mock.calls[0] as [LocalizedSlideReview[]];
    expect(sent[0].presentation_en.tldr_strip).toBe("Grok Bot books by phone");
  });
});
