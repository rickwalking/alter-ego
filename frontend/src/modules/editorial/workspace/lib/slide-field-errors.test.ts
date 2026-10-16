// AE-0403 — Gherkin: frontend/tests/features/review-form-field-errors.feature
import { afterEach, describe, expect, it } from "vitest";
import type { SlideValidationViolation } from "@/modules/editorial/workspace/types-ai";
import {
  addressViolation,
  buildSlideFieldErrors,
  fieldDomId,
  fieldErrorKey,
  firstInvalidFieldKey,
  focusInvalidField,
  invalidSlideIndexes,
  openBlockingViolations,
  slideDomId,
  violationFieldKey,
  violationLimit,
} from "./slide-field-errors";

function violation(
  overrides: Partial<SlideValidationViolation> = {},
): SlideValidationViolation {
  return {
    code: "emphasis_markup_invalid",
    message: "Emphasis must use balanced tags",
    slide_index: 9,
    locale: "en",
    field: "body",
    ...overrides,
  };
}

afterEach(() => {
  document.body.innerHTML = "";
});

describe("violation addressing", () => {
  it("keys a heading/body violation by slide, locale and field", () => {
    expect(violationFieldKey(violation())).toBe("9:presentation_en:body");
  });

  it("splits a structured-item field path from workflow state", () => {
    const addressed = addressViolation(
      violation({ locale: "pt", field: "summary_points[2].title" }),
    );
    expect(addressed).toMatchObject({
      item_list: "summary_points",
      item_index: 2,
      item_field: "title",
    });
    expect(violationFieldKey(addressed)).toBe(
      "9:presentation_pt:summary_points[2].title",
    );
  });

  it("keeps an already-addressed or plain violation unchanged", () => {
    const plain = violation();
    expect(addressViolation(plain)).toBe(plain);
    const addressed = violation({ item_index: 0, field: "features[0].body" });
    expect(addressViolation(addressed)).toBe(addressed);
  });

  it.each([
    violation({ slide_index: null }),
    violation({ locale: "fr" }),
    violation({ field: null }),
  ])("has no field key without a slide, known locale and field", (input) => {
    expect(violationFieldKey(input)).toBeNull();
  });
});

describe("field error state", () => {
  it("collects only blockers, grouped by field", () => {
    const errors = buildSlideFieldErrors([
      violation(),
      violation({ code: "dash_punctuation_forbidden" }),
      violation({ field: "heading", severity: "warning" }),
      violation({ field: null }),
    ]);
    expect([...errors.keys()]).toEqual(["9:presentation_en:body"]);
    expect(errors.get("9:presentation_en:body")).toHaveLength(2);
  });

  it("drops a cleared field but keeps field-less blockers open", () => {
    const fieldLess = violation({ field: null });
    const open = openBlockingViolations(
      [violation(), fieldLess, violation({ severity: "warning" })],
      new Set(["9:presentation_en:body"]),
    );
    expect(open).toEqual([fieldLess]);
  });

  it("lists sorted unique slide numbers", () => {
    expect(
      invalidSlideIndexes([
        violation({ slide_index: 9 }),
        violation({ slide_index: 2 }),
        violation({ slide_index: 9 }),
        violation({ slide_index: null }),
      ]),
    ).toEqual([2, 9]);
  });

  it("reads the backend max limit when present", () => {
    expect(
      violationLimit(violation({ message: "body exceeds max 220 characters" })),
    ).toBe(220);
    expect(violationLimit(violation())).toBeNull();
  });
});

describe("focus helpers", () => {
  function addField(id: string): HTMLTextAreaElement {
    const element = document.createElement("textarea");
    element.id = id;
    document.body.appendChild(element);
    return element;
  }

  it("builds id-safe DOM ids for item paths", () => {
    expect(
      fieldDomId(
        "edit",
        fieldErrorKey(3, "presentation_pt", "summary_points[0].body"),
      ),
    ).toBe("edit-3-presentation_pt-summary_points-0-body");
    expect(slideDomId("edit", 3)).toBe("edit-slide-3");
  });

  it("picks the lowest flagged slide, or the requested one", () => {
    const errors = buildSlideFieldErrors([
      violation({ slide_index: 9 }),
      violation({ slide_index: 2, field: "heading" }),
    ]);
    expect(firstInvalidFieldKey(errors)).toBe("2:presentation_en:heading");
    expect(firstInvalidFieldKey(errors, 9)).toBe("9:presentation_en:body");
    expect(firstInvalidFieldKey(errors, 5)).toBeNull();
  });

  it("focuses the first invalid field", () => {
    const body = addField("edit-9-presentation_en-body");
    focusInvalidField("edit", buildSlideFieldErrors([violation()]));
    expect(document.activeElement).toBe(body);
  });

  it("falls back to the slide card when the slide has no field error", () => {
    const card = document.createElement("div");
    card.id = "edit-slide-4";
    card.tabIndex = -1;
    document.body.appendChild(card);
    focusInvalidField("edit", buildSlideFieldErrors([]), 4);
    expect(document.activeElement).toBe(card);
  });

  it("does nothing without a field or a slide", () => {
    const before = document.activeElement;
    focusInvalidField("edit", buildSlideFieldErrors([]));
    expect(document.activeElement).toBe(before);
  });
});
