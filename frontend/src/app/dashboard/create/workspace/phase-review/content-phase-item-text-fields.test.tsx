/** Gherkin: frontend/tests/features/checklist-wysiwyg-editor-ae0543.feature */
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { SlideStructuredItemEdit } from "@/modules/editorial";
import type { LocalizedSlideReview } from "@/modules/publishing";
import { ItemTextFields } from "./content-phase-item-text-fields";

const ITEM = { icon_name: "check", title: "Gerado", body: "Editado" };

function renderItem(checklist: boolean) {
  const onItemChange = vi.fn<(edit: SlideStructuredItemEdit) => void>();
  const slide: LocalizedSlideReview = {
    slide_index: 8,
    slide_type: "summary",
    checklist,
    presentation_pt: { heading: "Salve", summary_points: [ITEM] },
    presentation_en: { heading: "Save", summary_points: [ITEM] },
  };
  render(
    <ItemTextFields
      context={{
        slide,
        localeKey: "presentation_en",
        fieldErrors: new Map(),
        onItemChange,
        onExtraChange: vi.fn(),
      }}
      listKey="summary_points"
      itemIndex={0}
      item={ITEM}
    />,
  );
  return onItemChange;
}

describe("ItemTextFields at content review", () => {
  // Scenario: A checklist slide edits one line per item
  // Scenario: Editing a checklist line writes the displayed field
  it("edits the checklist line the slide shows", () => {
    const onItemChange = renderItem(true);
    const line = screen.getByLabelText(/Checklist line/);
    expect(line).toHaveValue("Gerado");
    expect(screen.queryByLabelText("Item body")).toBeNull();
    fireEvent.change(line, { target: { value: "Review the contract" } });
    expect(onItemChange).toHaveBeenCalledWith({
      slideIndex: 8,
      locale: "presentation_en",
      listKey: "summary_points",
      itemIndex: 0,
      field: "title",
      clearFields: ["body"],
      value: "Review the contract",
    });
  });

  // Scenario: Grid and list slides edit the title and the body
  it("edits title and body on a grid slide", () => {
    renderItem(false);
    expect(screen.getByLabelText("Item title")).toHaveValue("Gerado");
    expect(screen.getByLabelText("Item body")).toHaveValue("Editado");
  });
});
