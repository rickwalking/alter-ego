import { RUBRIC_COLORS, type RubricColorKey } from "@/features/dashboard/rubrics/types";

export type ScoreLevel = "excellent" | "good" | "poor";

export function dimColor(hex: string): string {
  return `${hex}1F`;
}

export function getScoreClass(level: ScoreLevel): { bg: string; color: string } {
  const map: Record<ScoreLevel, { bg: string; color: string }> = {
    excellent: { bg: dimColor(RUBRIC_COLORS.teal), color: RUBRIC_COLORS.teal },
    good: { bg: dimColor(RUBRIC_COLORS.cyan), color: RUBRIC_COLORS.cyan },
    poor: { bg: dimColor(RUBRIC_COLORS.red), color: RUBRIC_COLORS.red },
  };
  return map[level];
}

export function getRubricColor(color: RubricColorKey): string {
  return RUBRIC_COLORS[color];
}
