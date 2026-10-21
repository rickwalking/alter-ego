/** Gherkin: frontend/tests/features/content-review-item-slots-ae0437.feature */
import { describe, expect, it } from "vitest";
import { STRUCTURED_LIST_MAX_ITEMS } from "@/constants/editorial-workflow";
import type { LocalizedSlideReview } from "@/modules/editorial/workspace/types-ai";
import { listStructuredExtras } from "./presentation-review-utils";
import {
  applySlideStructuredListEdit,
  canAddStructuredItem,
  editableStructuredListKey,
} from "./presentation-structured-lists";

const POINTS_PT = [
  { icon_name: "brain", title: "Um", body: "Corpo um." },
  { icon_name: "target", title: "Dois", body: "Corpo dois." },
  { icon_name: "eye", title: "Três", body: "Corpo três." },
];
const POINTS_EN = [
  { icon_name: "brain", title: "One", body: "Body one." },
  { icon_name: "target", title: "Two", body: "Body two." },
  { icon_name: "eye", title: "Three", body: "Body three." },
];

function closing(): LocalizedSlideReview {
  return {
    slide_index: 6,
    slide_type: "closing",
    presentation_pt: { heading: "Comece", body: "", actions: [] },
    presentation_en: { heading: "Start", body: "", actions: [] },
  };
}

function summary(): LocalizedSlideReview {
  return {
    slide_index: 2,
    slide_type: "summary",
    presentation_pt: { heading: "Resumo", summary_points: POINTS_PT },
    presentation_en: { heading: "Summary", summary_points: POINTS_EN },
  };
}

describe("editableStructuredListKey (AE-0437)", () => {
  // Scenario: A closing slide without actions offers an "add action" slot
  it("uses the slide type's list even when it is empty or missing", () => {
    expect(editableStructuredListKey({ actions: [] }, "closing")).toBe(
      "actions",
    );
    expect(editableStructuredListKey({}, "summary")).toBe("summary_points");
    expect(editableStructuredListKey({}, "content")).toBe("features");
  });

  // Scenario: A closing slide edits its actions, not a stray features list
  it("prefers the slide type's filled list over another filled list", () => {
    const both = { features: POINTS_EN, actions: POINTS_PT };
    expect(editableStructuredListKey(both, "closing")).toBe("actions");
  });

  it("falls back to an existing list, else none", () => {
    expect(editableStructuredListKey({ features: POINTS_PT }, "closing")).toBe(
      "features",
    );
    expect(editableStructuredListKey({ features: POINTS_PT }, "intro")).toBe(
      "features",
    );
    expect(editableStructuredListKey({}, "intro")).toBeNull();
    expect(editableStructuredListKey({}, "cta")).toBeNull();
  });

  it("never lists an empty item list as a raw structured extra", () => {
    expect(
      listStructuredExtras({ actions: [], summary_points: [], stats: [] }),
    ).toEqual([{ key: "stats", value: [] }]);
  });
});

describe("applySlideStructuredListEdit (AE-0437)", () => {
  // Scenario: Adding an action creates an empty slot in PT and EN
  it("adds an empty slot with an icon to both locales", () => {
    const [slide] = applySlideStructuredListEdit([closing()], {
      slideIndex: 6,
      listKey: "actions",
      operation: "add",
    });
    const blank = { icon_name: "target", title: "", body: "" };
    expect(slide!.presentation_pt.actions).toEqual([blank]);
    expect(slide!.presentation_en.actions).toEqual([blank]);
    const [next] = applySlideStructuredListEdit([slide!], {
      slideIndex: 6,
      listKey: "actions",
      operation: "add",
    });
    expect(
      (next!.presentation_pt.actions as Record<string, unknown>[])[1]!
        .icon_name,
    ).toBe("wrench");
  });

  it("adds to a list missing from one locale using the mirrored shape", () => {
    const slide: LocalizedSlideReview = {
      ...summary(),
      presentation_en: { heading: "Summary" },
    };
    const [edited] = applySlideStructuredListEdit([slide], {
      slideIndex: 2,
      listKey: "summary_points",
      operation: "add",
    });
    expect(edited!.presentation_pt.summary_points).toHaveLength(4);
    const en = edited!.presentation_en.summary_points as Record<
      string,
      unknown
    >[];
    expect(en).toHaveLength(4);
    expect(en[0]).toEqual({ icon_name: "brain", title: "", body: "" });
  });

  // Scenario: Removing an item removes the same position in PT and EN
  it("removes the same position in both locales", () => {
    const [slide] = applySlideStructuredListEdit([summary()], {
      slideIndex: 2,
      listKey: "summary_points",
      operation: "remove",
      itemIndex: 1,
    });
    expect(slide!.presentation_pt.summary_points).toEqual([
      POINTS_PT[0],
      POINTS_PT[2],
    ]);
    expect(slide!.presentation_en.summary_points).toEqual([
      POINTS_EN[0],
      POINTS_EN[2],
    ]);
  });

  // Scenario: A list is capped at 4 items
  it("caps a list at the maximum and leaves other slides alone", () => {
    const full = Array.from({ length: STRUCTURED_LIST_MAX_ITEMS }, () => ({
      title: "t",
      body: "b",
    }));
    expect(canAddStructuredItem(full)).toBe(false);
    expect(canAddStructuredItem(full.slice(1))).toBe(true);
    const slide: LocalizedSlideReview = {
      slide_index: 3,
      slide_type: "content",
      presentation_pt: { heading: "x", features: full },
      presentation_en: { heading: "y", features: full },
    };
    const other = summary();
    const [same, untouched] = applySlideStructuredListEdit([slide, other], {
      slideIndex: 3,
      listKey: "features",
      operation: "add",
    });
    expect(same!.presentation_pt.features).toHaveLength(4);
    expect(untouched).toBe(other);
  });
});
