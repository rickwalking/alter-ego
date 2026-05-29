import {
  NEON_AMBER,
  NEON_CYAN,
  NEON_MAGENTA,
  NEON_RED,
  NEON_TEAL,
} from "@/constants/neon";

export const RUBRIC_COLORS = {
  cyan: NEON_CYAN,
  magenta: NEON_MAGENTA,
  teal: NEON_TEAL,
  amber: NEON_AMBER,
  red: NEON_RED,
} as const;

export type RubricColorKey = keyof typeof RUBRIC_COLORS;

export interface CriterionRow {
  name: string;
  description: string;
  excellent: string;
  good: string;
  poor: string;
}

export interface RubricData {
  badge: string;
  badgeColor: RubricColorKey;
  title: string;
  weight: string;
  status: "active" | "inactive";
  criteria: CriterionRow[];
}

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

export type ScoreLevel = "excellent" | "good" | "poor";

export const RUBRIC_ROW_BORDER = "rgba(255,255,255,0.03)";
export const RUBRIC_HEADER_HOVER_BG = "rgba(255,255,255,0.02)";
export const RUBRIC_HEADER_BORDER = "rgba(255,255,255,0.04)";
export const RUBRIC_TABLE_HEADER_BG = "rgba(0,0,0,0.15)";
