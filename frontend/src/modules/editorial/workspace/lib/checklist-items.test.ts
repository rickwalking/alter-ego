/** Gherkin: frontend/tests/features/checklist-wysiwyg-editor-ae0543.feature */
import { describe, expect, it } from "vitest";
import { WORKFLOW_PHASE_STATUS } from "@/constants/workflow";
import type {
  EditorialWorkflowState,
  LocalizedSlideReview,
} from "@/modules/editorial/workspace/types-ai";
import { checklistItemEdit, checklistItemText } from "./checklist-items";
import {
  applySlideStructuredItemEdit,
  resolveLocalizedSlides,
} from "./presentation-slide-resolution";

function slide(index: number): LocalizedSlideReview {
  const points = [{ icon_name: "check", title: "Gerado", body: "Oculto" }];
  return {
    slide_index: index,
    slide_type: "summary",
    presentation_pt: { heading: "Salve", summary_points: points },
    presentation_en: { heading: "Save", summary_points: points },
  };
}

function state(checklist?: number[]): EditorialWorkflowState {
  return {
    project_id: "p",
    current_phase: "content",
    phase_status: WORKFLOW_PHASE_STATUS.AWAITING_HUMAN,
    research_findings: [],
    outline: [],
    slide_drafts: [],
    status: "draft",
    localized_slides: [slide(7), slide(8)],
    checklist_slide_indexes: checklist,
  };
}

describe("checklist items", () => {
  // Scenario: A checklist slide edits one line per item
  it("shows the title, else the body, like the slide", () => {
    expect(checklistItemText({ title: "Linha", body: "Oculto" })).toBe("Linha");
    expect(checklistItemText({ title: "", body: "Só corpo" })).toBe("Só corpo");
    expect(checklistItemText({})).toBe("");
  });

  // Scenario: Editing a checklist line writes the displayed field
  it.each(["presentation_pt", "presentation_en"] as const)(
    "sets the title and empties the body in %s",
    (locale) => {
      const [edited] = applySlideStructuredItemEdit(
        [slide(8)],
        checklistItemEdit({
          slideIndex: 8,
          locale,
          listKey: "summary_points",
          itemIndex: 0,
          value: "Revise o contrato",
        }),
      );
      expect(edited?.[locale].summary_points).toEqual([
        { icon_name: "check", title: "Revise o contrato", body: "" },
      ]);
    },
  );

  // Scenario: A checklist slide edits one line per item
  it("marks the slides the workflow state lists", () => {
    const resolved = resolveLocalizedSlides(state([8]));
    expect(resolved.map((item) => item.checklist)).toEqual([undefined, true]);
  });

  // Scenario: Slides that are not listed stay title-and-body
  it("marks none when the state lists none", () => {
    const resolved = resolveLocalizedSlides(state());
    expect(resolved.some((item) => item.checklist)).toBe(false);
  });
});
