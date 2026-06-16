import { describe, it, expect } from "vitest";
import { mapRubricToCardProps } from "@/modules/editorial-operations/board/rubrics/adapters/rubric-adapter";

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
