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

export const RUBRIC_ROW_BORDER = "rgba(255,255,255,0.03)";
export const RUBRIC_HEADER_HOVER_BG = "rgba(255,255,255,0.02)";
export const RUBRIC_HEADER_BORDER = "rgba(255,255,255,0.04)";
export const RUBRIC_TABLE_HEADER_BG = "rgba(0,0,0,0.15)";
