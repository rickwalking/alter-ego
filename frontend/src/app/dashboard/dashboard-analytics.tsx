"use client";

import { useTranslations } from "next-intl";
import { NeonSpinner } from "@/components/atoms/neon-spinner";
import { NeonCard } from "@/components/molecules/neon-card";
import {
  NeonStatsGrid,
  type NeonStatsGridProps,
} from "@/components/organisms/neon-stats-grid";
import { NeonActivityList } from "@/components/organisms/neon-activity-list";
import { NEON_RED, TEXT, TEXT_MUTED } from "@/constants/neon";
import type { NeonBadgeVariant } from "@/schemas/neon-badge";
import type {
  EditorialAnalyticsState,
  EditorialAnalyticsSummary,
} from "@/modules/editorial-operations";

const DOT_TO_BADGE: Record<string, NeonBadgeVariant> = {
  "#22c55e": "green",
  "#00d4ff": "cyan",
  "#f59e0b": "amber",
  "#ff2770": "magenta",
  "#0ac5a8": "teal",
};

export interface DashboardAnalyticsProps {
  state: EditorialAnalyticsState;
}

/**
 * The editorial-analytics stats. A flag-off (404) or no-access (403)
 * route shows a "disabled" card and a failed load shows an inline message;
 * neither replaces the rest of the dashboard any more.
 */
export function DashboardAnalyticsStats({
  state,
}: Readonly<DashboardAnalyticsProps>): React.ReactElement {
  const tAnalytics = useTranslations("dashboard.analytics");

  if (state.loading) {
    return (
      <div className="flex justify-center py-10">
        <NeonSpinner size="lg" />
      </div>
    );
  }
  if (state.disabled) {
    return (
      <NeonCard padding="md" data-testid="analytics-disabled">
        <h2 className="text-sm font-semibold mb-1" style={{ color: TEXT }}>
          {tAnalytics("disabledTitle")}
        </h2>
        <p className="text-xs" style={{ color: TEXT_MUTED }}>
          {tAnalytics("disabledBody")}
        </p>
      </NeonCard>
    );
  }
  if (state.error || !state.data) {
    return (
      <p className="text-center py-8" style={{ color: NEON_RED }}>
        {tAnalytics("loadFailed")}
      </p>
    );
  }
  return <NeonStatsGrid cards={statCardsFor(state.data.summary, tAnalytics)} />;
}

/** The status breakdown and the drafts/velocity lists (only with data). */
export function DashboardAnalyticsActivity({
  state,
}: Readonly<DashboardAnalyticsProps>): React.ReactElement | null {
  const t = useTranslations("dashboard.overview");
  if (!state.data) {
    return null;
  }
  const { summary } = state.data;
  const statusActivities = Object.entries(summary.status_breakdown).map(
    ([status, count], index) => ({
      id: `status-${index}`,
      title: status.replace(/_/g, " "),
      description: `${count} items`,
      time: "Live",
      badgeVariant: DOT_TO_BADGE["#00d4ff"] ?? "cyan",
    }),
  );

  return (
    <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
      <NeonActivityList
        title={t("recentActivity.title")}
        activities={statusActivities}
      />
      <NeonActivityList
        title={t("upcomingSchedule.title")}
        activities={[
          {
            id: "drafts",
            title: "Drafts",
            description: `${summary.draft_count} in progress`,
            time: "Today",
            badgeVariant: "amber",
          },
          {
            id: "velocity",
            title: "Weekly velocity",
            description: `${summary.content_velocity_per_week} posts/week`,
            time: "Trend",
            badgeVariant: "teal",
          },
        ]}
      />
    </div>
  );
}

function statCardsFor(
  summary: EditorialAnalyticsSummary,
  tAnalytics: (key: string) => string,
): NeonStatsGridProps["cards"] {
  return [
    {
      label: tAnalytics("totalPosts"),
      value: String(summary.total_posts),
      icon: (
        <svg
          width="18"
          height="18"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
        >
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
        </svg>
      ),
      iconBg: "rgba(0,212,255,0.12)",
    },
    {
      label: tAnalytics("publishedWeek"),
      value: String(summary.published_this_week),
      icon: (
        <svg
          width="18"
          height="18"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
        >
          <polyline points="23 6 13.5 15.5 8.5 10.5 1 18" />
        </svg>
      ),
      iconBg: "rgba(34,197,94,0.12)",
    },
    {
      label: tAnalytics("pendingReview"),
      value: String(summary.pending_review),
      icon: (
        <svg
          width="18"
          height="18"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
        >
          <circle cx="12" cy="12" r="10" />
        </svg>
      ),
      iconBg: "rgba(245,158,11,0.12)",
    },
    {
      label: tAnalytics("qualityScore"),
      value: `${summary.quality_score_average}%`,
      icon: (
        <svg
          width="18"
          height="18"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
        >
          <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
        </svg>
      ),
      iconBg: "rgba(255,39,112,0.12)",
    },
  ];
}
