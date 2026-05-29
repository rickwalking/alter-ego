import type { RubricData } from "@/features/dashboard/rubrics/types";

/** @deprecated Static demo data — production uses useRubrics() API. */
export const RUBRICS: RubricData[] = [
  {
    badge: "Carousel",
    badgeColor: "cyan",
    title: "Content Quality Rubric",
    weight: "1.0",
    status: "active",
    criteria: [
      {
        name: "Technical Accuracy",
        description: "Facts, data, and claims are verifiable",
        excellent: "No errors",
        good: "Minor issues",
        poor: "Major errors",
      },
      {
        name: "Tone Alignment",
        description: "Matches persona voice and brand",
        excellent: "Fully aligned",
        good: "Mostly aligned",
        poor: "Off voice",
      },
      {
        name: "Visual Cohesion",
        description: "Design consistency across slides",
        excellent: "Seamless",
        good: "Minor inconsistencies",
        poor: "Breaks theme",
      },
      {
        name: "Engagement",
        description: "Hook, pacing, call to action",
        excellent: "Compelling",
        good: "Solid",
        poor: "Flat",
      },
      {
        name: "Forbidden Phrases",
        description: "No banned words or AI-isms",
        excellent: "Zero matches",
        good: "1-2 minor",
        poor: "3+ matches",
      },
    ],
  },
  {
    badge: "Blog",
    badgeColor: "magenta",
    title: "Blog Post Quality Rubric",
    weight: "1.0",
    status: "active",
    criteria: [
      {
        name: "Depth & Research",
        description: "Substance and sources",
        excellent: "Thorough",
        good: "Adequate",
        poor: "Shallow",
      },
      {
        name: "Readability",
        description: "Structure and flow",
        excellent: "Clear flow",
        good: "Readable",
        poor: "Hard to follow",
      },
      {
        name: "Originality",
        description: "Fresh perspective",
        excellent: "Novel insight",
        good: "Solid take",
        poor: "Generic",
      },
    ],
  },
];

export type { RubricData, CriterionRow, RubricColorKey } from "@/features/dashboard/rubrics/types";
export {
  RUBRIC_ROW_BORDER,
  RUBRIC_HEADER_HOVER_BG,
  RUBRIC_HEADER_BORDER,
  RUBRIC_TABLE_HEADER_BG,
} from "@/features/dashboard/rubrics/types";
export type ScoreLevel = "excellent" | "good" | "poor";
