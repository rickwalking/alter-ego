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

/** One criterion of a rubric card, as the API stores it. */
export interface CriterionRow {
  name: string;
  description: string;
  /** The criterion's weight in the rubric (0–1). */
  weight: number;
  /** The minimum threshold as a whole percentage of the scale. */
  thresholdPercent: number;
  /** The scoring-scale key (e.g. "0-100"); the page translates it. */
  scoringScale: string;
}

/** A content type the rubric applies to, with its badge colour. */
export interface RubricContentTypeTag {
  /** The content-type key (e.g. "carousel"); the page translates it. */
  type: string;
  color: RubricColorKey;
}

/** What a rubric card shows: only fields the rubrics API returns. */
export interface RubricData {
  title: string;
  contentTypes: RubricContentTypeTag[];
  isDefault: boolean;
  criteria: CriterionRow[];
}

export const RUBRIC_ROW_BORDER = "rgba(255,255,255,0.03)";
export const RUBRIC_HEADER_BORDER = "rgba(255,255,255,0.04)";
export const RUBRIC_TABLE_HEADER_BG = "rgba(0,0,0,0.15)";
