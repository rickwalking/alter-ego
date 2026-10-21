/**
 * Editorial analytics hook types (colocated `types.ts`).
 *
 * Per the component-type-location convention (AE-0144,
 * `frontend/scripts/component-type-location.config.mjs`), hook contract shapes
 * live here rather than inline in the `use-*.ts` files.
 */

export interface EditorialAnalyticsSummary {
  total_posts: number;
  published_this_week: number;
  published_this_month: number;
  content_velocity_per_week: number;
  status_breakdown: Record<string, number>;
  average_views: number;
  pending_review: number;
  draft_count: number;
  quality_score_average: number;
}

export interface EditorialAnalytics {
  summary: EditorialAnalyticsSummary;
  velocity_by_week: { week_start: string; published_count: number }[];
}

/** AE-0378: `disabled` = the analytics flag is off (404) or the role has no access (403). */
export interface EditorialAnalyticsState {
  data: EditorialAnalytics | null;
  loading: boolean;
  error: string | null;
  disabled: boolean;
  refetch: () => Promise<void>;
}
