/** Gherkin: frontend/tests/features/content-review-manual-fixes-ae0414.feature */
// Scenario: Copy using the other locale's emphasis can be converted
import { describe, expect, it } from "vitest";
import {
  emphasisConventionMismatch,
  normalizeEmphasis,
} from "./presentation-emphasis";

describe("per-locale emphasis convention (AE-0414 B29)", () => {
  it("flags <strong> in PT and ** in EN only", () => {
    expect(
      emphasisConventionMismatch("presentation_pt", "a <strong>b</strong>"),
    ).toBe(true);
    expect(emphasisConventionMismatch("presentation_pt", "a **b**")).toBe(
      false,
    );
    expect(emphasisConventionMismatch("presentation_en", "a **b**")).toBe(true);
    expect(
      emphasisConventionMismatch("presentation_en", "a <STRONG>b</STRONG>"),
    ).toBe(false);
  });

  it("converts emphasis to the locale's markup without touching the text", () => {
    expect(
      normalizeEmphasis(
        "presentation_pt",
        "Com <strong>limites claros</strong> e <strong>foco</strong>.",
      ),
    ).toBe("Com **limites claros** e **foco**.");
    expect(normalizeEmphasis("presentation_en", "Do the **review** now")).toBe(
      "Do the <strong>review</strong> now",
    );
    expect(normalizeEmphasis("presentation_en", "plain")).toBe("plain");
  });
});
