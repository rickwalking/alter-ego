/**
 * Editorial analytics hook types (colocated `types.ts`).
 *
 * Per the component-type-location convention (
 * `frontend/scripts/component-type-location.config.mjs`), hook contract shapes
 * live here rather than inline in the `use-*.ts` files.
 */

export interface ChannelPublishingSummary {
  channel: string;
  published_total: number;
  published_this_week: number;
  published_this_month: number;
}

export interface EditorialAnalyticsSummary {
  total_posts: number;
  published_this_week: number;
  published_this_month: number;
  content_velocity_per_week: number;
  status_breakdown: Record<string, number>;
  channels: ChannelPublishingSummary[];
  pending_review: number;
  draft_count: number;
  /** Average content rubric score (0-100); null when there is none. */
  quality_score_average: number | null;
  /** How many content rubric scores the average is built from. */
  quality_score_count: number;
}

export interface AnalyticsVelocityWeek {
  week_start: string;
  published_count: number;
  channels: Record<string, number>;
}

export interface EditorialAnalytics {
  summary: EditorialAnalyticsSummary;
  velocity_by_week: AnalyticsVelocityWeek[];
}

/** `disabled` = the analytics flag is off (404) or the role has no access (403). */
export interface EditorialAnalyticsState {
  data: EditorialAnalytics | null;
  loading: boolean;
  error: string | null;
  disabled: boolean;
  refetch: () => Promise<void>;
}
