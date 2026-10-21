import type { InstagramPostInsights } from "@/modules/editorial-operations";

/** The per-post counts the dashboard sums (Section-13 KPIs). */
export type InstagramMetricKey =
  | "views"
  | "reach"
  | "shares"
  | "saved"
  | "follows"
  | "profile_visits";

export const INSTAGRAM_KPI_KEYS: readonly InstagramMetricKey[] = [
  "views",
  "reach",
  "shares",
  "saved",
  "follows",
  "profile_visits",
];

export const RECENT_POSTS_SHOWN = 5;
const RATIO_DIGITS = 2;

/** Sum over the posts that report the metric; null when none does. */
export function sumMetric(
  items: readonly InstagramPostInsights[],
  key: InstagramMetricKey,
): number | null {
  const known = items
    .map((item) => item[key])
    .filter((value): value is number => value !== null);
  if (known.length === 0) {
    return null;
  }
  return known.reduce((total, value) => total + value, 0);
}

/** A count or ratio for display; "n/d" (never 0) when Graph did not return it. */
export function formatMetric(
  value: number | null,
  notAvailable: string,
  locale: string,
): string {
  if (value === null) {
    return notAvailable;
  }
  return new Intl.NumberFormat(locale, {
    maximumFractionDigits: RATIO_DIGITS,
  }).format(value);
}
