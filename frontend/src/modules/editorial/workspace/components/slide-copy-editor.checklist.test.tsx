/** Gherkin: frontend/tests/features/checklist-wysiwyg-editor-ae0543.feature */
import { fireEvent, render } from "@testing-library/react";
import { createElement } from "react";
import { describe, expect, it, vi } from "vitest";
import type { SlideStructuredItemEdit } from "@/modules/editorial/workspace/lib/presentation-slide-resolution";
import type { LocalizedSlideReview } from "@/modules/editorial/workspace/types-ai";
import { SlideCopyEditor } from "./slide-copy-editor";

vi.mock("next-intl", () => ({
  useTranslations: vi.fn(() => (key: string) => key),
}));

function slide(checklist: boolean): LocalizedSlideReview {
  return {
    slide_index: 8,
    slide_type: "summary",
    checklist,
    presentation_pt: {
      heading: "Salve",
      summary_points: [
        { title: "Gerado", body: "Editado pelo dono" },
        { title: "", body: "Só corpo" },
      ],
    },
    presentation_en: {
      heading: "Save",
      summary_points: [{ title: "Generated", body: "Owner edit" }],
    },
  };
}

function renderEditor(checklist: boolean) {
  const onStructuredItemChange =
    vi.fn<(edit: SlideStructuredItemEdit) => void>();
  const view = render(
    createElement(SlideCopyEditor, {
      slides: [slide(checklist)],
      idPrefix: "publish-edit",
      onCopyChange: vi.fn(),
      onStructuredItemChange,
    }),
  );
  return { ...view, onStructuredItemChange };
}

function fields(container: HTMLElement, label: string): HTMLTextAreaElement[] {
  return [
    ...container.querySelectorAll<HTMLTextAreaElement>(
      `textarea[aria-label="${label}"]`,
    ),
  ];
}

describe("SlideCopyEditor structured items", () => {
  // Scenario: A checklist slide edits one line per item
  it("shows one line per checklist item, holding the text on the slide", () => {
    const { container } = renderEditor(true);
    expect(fields(container, "checklistItemLabel").map((f) => f.value)).toEqual(
      ["Gerado", "Só corpo", "Generated"],
    );
    expect(fields(container, "structuredItemLabel")).toHaveLength(0);
  });

  // Scenario: Editing a checklist line writes the displayed field
  it("writes the title and clears the body when a line is edited", () => {
    const { container, onStructuredItemChange } = renderEditor(true);
    const [first] = fields(container, "checklistItemLabel");
    fireEvent.change(first!, { target: { value: "Revise o contrato" } });
    expect(onStructuredItemChange).toHaveBeenCalledWith({
      slideIndex: 8,
      locale: "presentation_pt",
      listKey: "summary_points",
      itemIndex: 0,
      field: "title",
      clearFields: ["body"],
      value: "Revise o contrato",
    });
  });

  // Scenario: Grid and list slides edit the title and the body
  it("edits title and body on a grid slide", () => {
    const { container, onStructuredItemChange } = renderEditor(false);
    const titles = fields(container, "structuredItemTitleLabel");
    expect(titles.map((f) => f.value)).toEqual(["Gerado", "", "Generated"]);
    expect(fields(container, "structuredItemLabel")).toHaveLength(3);
    fireEvent.change(titles[0]!, { target: { value: "Novo título" } });
    expect(onStructuredItemChange).toHaveBeenCalledWith(
      expect.objectContaining({ field: "title", value: "Novo título" }),
    );
    expect(
      onStructuredItemChange.mock.calls[0]?.[0].clearFields,
    ).toBeUndefined();
  });

  // Scenario: The checklist editor offers the lines the slide draws
  it("skips a blank item and still edits the right item", () => {
    const blank: LocalizedSlideReview = {
      ...slide(true),
      presentation_pt: {
        heading: "Salve",
        summary_points: [
          { title: "", body: "" },
          { title: "Segunda", body: "" },
        ],
      },
    };
    const onStructuredItemChange =
      vi.fn<(edit: SlideStructuredItemEdit) => void>();
    const { container } = render(
      createElement(SlideCopyEditor, {
        slides: [blank],
        idPrefix: "publish-edit",
        onCopyChange: vi.fn(),
        onStructuredItemChange,
      }),
    );
    const [first] = fields(container, "checklistItemLabel");
    expect(first?.value).toBe("Segunda");
    fireEvent.change(first!, { target: { value: "Nova" } });
    expect(onStructuredItemChange).toHaveBeenCalledWith(
      expect.objectContaining({ itemIndex: 1, value: "Nova" }),
    );
  });
});
