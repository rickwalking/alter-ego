"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";
import { NeonSpinner } from "@/components/atoms/neon-spinner";
import { NeonTopBar } from "@/components/organisms/neon-top-bar";
import { NeonStatsGrid } from "@/components/organisms/neon-stats-grid";
import { NeonActivityList } from "@/components/organisms/neon-activity-list";
import { NeonCard } from "@/components/molecules/neon-card";
import { QUICK_ACTIONS } from "./constants";
import { TEXT, NEON_RED } from "@/constants/neon";
import type { NeonBadgeVariant } from "@/schemas/neon-badge";
import { useEditorialAnalytics } from "@/features/analytics/hooks/use-editorial-analytics";

const DOT_TO_BADGE: Record<string, NeonBadgeVariant> = {
  "#22c55e": "green",
  "#00d4ff": "cyan",
  "#f59e0b": "amber",
  "#ff2770": "magenta",
  "#0ac5a8": "teal",
};

const PAGE_FONT_FAMILY = "Inter, system-ui, sans-serif";

export default function DashboardPage(): React.ReactElement {
  const t = useTranslations("dashboard.overview");
  const tAnalytics = useTranslations("dashboard.analytics");
  const { data, loading, error } = useEditorialAnalytics();

  if (loading) {
    return (
      <div className="flex-1 text-white relative" style={{ fontFamily: PAGE_FONT_FAMILY }}>
        <NeonTopBar title="Dashboard" breadcrumb={[{ label: "overview" }]} />
        <div className="flex justify-center py-20">
          <NeonSpinner size="lg" />
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="flex-1 text-white relative" style={{ fontFamily: PAGE_FONT_FAMILY }}>
        <NeonTopBar title="Dashboard" breadcrumb={[{ label: "overview" }]} />
        <p className="text-center py-8" style={{ color: NEON_RED }}>
          {error ?? tAnalytics("loadFailed")}
        </p>
      </div>
    );
  }

  const { summary } = data;

  const statCards = [
    {
      label: tAnalytics("totalPosts"),
      value: String(summary.total_posts),
      icon: (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
        </svg>
      ),
      iconBg: "rgba(0,212,255,0.12)",
    },
    {
      label: tAnalytics("publishedWeek"),
      value: String(summary.published_this_week),
      icon: (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <polyline points="23 6 13.5 15.5 8.5 10.5 1 18" />
        </svg>
      ),
      iconBg: "rgba(34,197,94,0.12)",
    },
    {
      label: tAnalytics("pendingReview"),
      value: String(summary.pending_review),
      icon: (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <circle cx="12" cy="12" r="10" />
        </svg>
      ),
      iconBg: "rgba(245,158,11,0.12)",
    },
    {
      label: tAnalytics("qualityScore"),
      value: `${summary.quality_score_average}%`,
      icon: (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
        </svg>
      ),
      iconBg: "rgba(255,39,112,0.12)",
    },
  ];

  const statusActivities = Object.entries(summary.status_breakdown).map(
    ([status, count], index) => ({
      id: `status-${index}`,
      title: status.replace(/_/g, " "),
      description: `${count} items`,
      time: "Live",
      badgeVariant: (DOT_TO_BADGE["#00d4ff"] ?? "cyan") as NeonBadgeVariant,
    }),
  );

  return (
    <div
      className="flex-1 text-white relative"
      style={{ fontFamily: PAGE_FONT_FAMILY }}
    >
      <NeonTopBar title="Dashboard" breadcrumb={[{ label: "overview" }]} />

      <div style={{ padding: "28px 32px" }}>
        <div className="mb-7">
          <NeonStatsGrid cards={statCards} />
        </div>

        <div className="mb-7">
          <h2
            className="font-extrabold tracking-tight mb-4"
            style={{ fontSize: 18, color: TEXT }}
          >
            {t("quickActions.title")}
          </h2>
          <div
            className="grid gap-4"
            style={{ gridTemplateColumns: "repeat(3, 1fr)" }}
          >
            {QUICK_ACTIONS.map((action) => (
              <Link key={action.title} href={action.href} className="block no-underline">
              <NeonCard hover padding="md" className="text-center">
                <div
                  className="flex items-center justify-center mx-auto mb-3"
                  style={{
                    width: 44,
                    height: 44,
                    borderRadius: 10,
                    background: action.iconBg,
                    color: action.iconColor,
                  }}
                >
                  <svg
                    width="22"
                    height="22"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  >
                    {action.icon}
                  </svg>
                </div>
                <h4 className="text-sm font-semibold mb-1" style={{ color: TEXT }}>
                  {action.title}
                </h4>
                <p className="text-xs text-text-dim">{action.description}</p>
              </NeonCard>
              </Link>
            ))}
          </div>
        </div>

        <div className="grid gap-5" style={{ gridTemplateColumns: "1fr 1fr" }}>
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
      </div>
    </div>
  );
}
