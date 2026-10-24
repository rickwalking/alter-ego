/** Gherkin: frontend/tests/features/checklist-wysiwyg-editor-ae0543.feature */
import { describe, expect, it } from "vitest";
import { checklistLines } from "./checklist-items";

function item(title: string, body = ""): Record<string, unknown> {
  return { icon_name: "check", title, body };
}

describe("checklistLines", () => {
  // Scenario: The checklist editor offers the lines the slide draws
  it("drops blank items and keeps each line's item index", () => {
    expect(
      checklistLines({
        summary_points: [
          item(""),
          item("Um"),
          item("  ", "oculto"),
          item("", "Dois"),
        ],
      }),
    ).toEqual({
      listKey: "summary_points",
      lines: [
        { itemIndex: 1, text: "Um" },
        { itemIndex: 3, text: "Dois" },
      ],
    });
  });

  // Scenario: The checklist editor offers the lines the slide draws
  it("offers at most five lines", () => {
    const items = ["1", "2", "3", "4", "5", "6"].map((text) => item(text));
    const shown = checklistLines({ summary_points: items });
    expect(shown?.lines.map((line) => line.text)).toEqual([
      "1",
      "2",
      "3",
      "4",
      "5",
    ]);
  });

  // Scenario: The checklist editor offers the lines the slide draws
  it("reads the lists in the template's order, skipping blank lists", () => {
    expect(
      checklistLines({
        summary_points: [item("")],
        features: [item("Feature")],
        actions: [item("Ação")],
      })?.listKey,
    ).toBe("actions");
    expect(checklistLines({ features: [item("Feature")] })?.listKey).toBe(
      "features",
    );
    expect(checklistLines({ summary_points: [item("")] })).toBeNull();
  });
});
