import { describe, it, expect } from "vitest";
import {
  mapRubricToCardProps,
  thresholdLabel,
} from "@/modules/editorial-operations/board/rubrics/adapters/rubric-adapter";

describe("mapRubricToCardProps", () => {
  it("maps rubric fields to NeonRubricCard props", () => {
    const result = mapRubricToCardProps({
      title: "Voice Match",
      category: "Persona",
      score: 82,
      maxScore: 100,
      criteria: ["Tone", "Clarity"],
    });
    expect(result.title).toBe("Voice Match");
    expect(result.criteria).toHaveLength(2);
  });
});

describe("thresholdLabel", () => {
  // Scenario: A criterion threshold shows as a percentage of its scale
  it.each([
    [0.7, "0-100", "≥ 70% (0-100)"],
    [0.8, "1-10", "≥ 80% (1-10)"],
    [1, "pass_fail", "≥ 100% (pass_fail)"],
    [0.655, "0-100", "≥ 66% (0-100)"],
  ])("shows %s on %s as %s", (threshold, scale, label) => {
    expect(thresholdLabel(threshold, scale)).toBe(label);
  });
});
