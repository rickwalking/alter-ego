import { describe, it, expect } from "vitest";
import {
  mapQualityRubricToPanelData,
  mapRubricToCardProps,
  thresholdPercent,
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

const CRITERION = {
  id: "c-1",
  name: "Hook strength",
  description: "Does slide 1 stop the scroll?",
  weight: 0.35,
  evaluation_method: "ai_auto",
  min_threshold: 0.655,
  scoring_scale: "pass_fail",
  prompt_template: "Score {content}",
};

const RUBRIC = {
  id: "r-1",
  name: "Carousel quality",
  description: null,
  criteria: [CRITERION],
  applicable_content_types: ["carousel", "blog_post", "newsletter"],
  is_default: true,
  created_at: "2026-10-21T00:00:00Z",
  updated_at: "2026-10-21T00:00:00Z",
  version: 1,
};

describe("thresholdPercent", () => {
  // Scenario: A criterion threshold shows as a percentage of its scale
  it.each([
    [0.7, 70],
    [0.8, 80],
    [1, 100],
    [0.655, 66],
  ])("shows %s as %s%%", (threshold, percent) => {
    expect(thresholdPercent(threshold)).toBe(percent);
  });
});

describe("mapQualityRubricToPanelData", () => {
  // Scenario: The card shows every content type the rubric applies to
  it("keeps every content type, each with its colour", () => {
    expect(mapQualityRubricToPanelData(RUBRIC).contentTypes).toEqual([
      { type: "carousel", color: "cyan" },
      { type: "blog_post", color: "magenta" },
      { type: "newsletter", color: "teal" },
    ]);
  });

  // Scenario: The card shows only the data the API returns
  it("carries the API's weights, scale key and default flag", () => {
    const data = mapQualityRubricToPanelData(RUBRIC);
    expect(data.title).toBe("Carousel quality");
    expect(data.isDefault).toBe(true);
    expect(data.criteria).toEqual([
      {
        name: "Hook strength",
        description: "Does slide 1 stop the scroll?",
        weight: 0.35,
        thresholdPercent: 66,
        scoringScale: "pass_fail",
      },
    ]);
    expect(Object.keys(data)).not.toContain("status");
  });

  it("maps a rubric without content types to no badges", () => {
    const data = mapQualityRubricToPanelData({
      ...RUBRIC,
      applicable_content_types: [],
      is_default: false,
    });
    expect(data.contentTypes).toEqual([]);
    expect(data.isDefault).toBe(false);
  });
});
