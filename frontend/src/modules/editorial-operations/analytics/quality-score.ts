import type { EditorialAnalyticsSummary } from "./hooks/types";

/** The ``dashboard.analytics`` translator the quality tile needs. */
type AnalyticsTranslate = (key: string, values?: { count: number }) => string;

/** What the quality score tile shows: the value and the count under it. */
export interface QualityScoreStat {
  value: string;
  detail?: string;
}

/**
 * The quality score tile: the average of the content scores with how many
 * there are, or "no data" when there is none (never a stand-in percentage).
 */
export function qualityScoreStat(
  summary: Pick<
    EditorialAnalyticsSummary,
    "quality_score_average" | "quality_score_count"
  >,
  t: AnalyticsTranslate,
): QualityScoreStat {
  if (summary.quality_score_average === null) {
    return { value: t("qualityScoreEmpty") };
  }
  return {
    value: `${summary.quality_score_average}%`,
    detail: t("qualityScoreCount", { count: summary.quality_score_count }),
  };
}
