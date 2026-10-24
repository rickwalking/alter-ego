/** Gherkin: frontend/tests/features/checklist-wysiwyg-editor-ae0543.feature */
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { CHECKLIST_ITEM_LIST_KEYS, checklistLines } from "./checklist-items";
import { PRESENTATION_STRUCTURED_ITEM_LIST_KEYS } from "./presentation-review-utils";

const SAVE_CHECKLIST_TEMPLATE = resolve(
  process.cwd(),
  "../backend/src/rag_backend/application/services/carousel_template/strategies/save_checklist.py",
);

function templateItemKeys(): string[] {
  const source = readFileSync(SAVE_CHECKLIST_TEMPLATE, "utf-8");
  const keys = /^_ITEM_KEYS = \(([^)]*)\)/m.exec(source)?.[1] ?? "";
  return [...keys.matchAll(/"([a-z_]+)"/g)].map((match) => match[1] ?? "");
}

function item(title: string, body = ""): Record<string, unknown> {
  return { icon_name: "check", title, body };
}

describe("checklistLines", () => {
  /** Scenario: The checklist editor offers the lines the slide draws */
  it("reads the lists in the backend checklist template's order", () => {
    expect([...CHECKLIST_ITEM_LIST_KEYS]).toEqual(templateItemKeys());
  });

  /** Scenario: Grid and list slides edit the title and the body */
  it("keeps the grid and list order (features before actions)", () => {
    expect([...PRESENTATION_STRUCTURED_ITEM_LIST_KEYS]).toEqual([
      "summary_points",
      "features",
      "actions",
    ]);
  });

  /** Scenario: The checklist editor offers the lines the slide draws */
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

  /** Scenario: The checklist editor offers the lines the slide draws */
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

  /** Scenario: The checklist editor offers the lines the slide draws */
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
