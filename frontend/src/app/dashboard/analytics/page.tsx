"use client";

import { useTranslations } from "next-intl";
import {
  NeonCard,
  NeonCardContent,
  NeonCardHeader,
  NeonCardTitle,
} from "@/components/molecules/neon-card";
import { NeonSpinner } from "@/components/atoms/neon-spinner";
import { NeonTopBar } from "@/components/organisms/neon-top-bar";
import { NeonStatsGrid } from "@/components/organisms/neon-stats-grid";
import {
  NEON_CYAN,
  NEON_GLOW_CYAN_SOFT,
  NEON_RED,
  TEXT,
  TEXT_MUTED,
} from "@/constants/neon";
import { useEditorialAnalytics } from "@/modules/editorial-operations";

export default function AnalyticsPage(): React.ReactElement {
  const t = useTranslations("dashboard.analytics");
  const { data, loading, error } = useEditorialAnalytics();

  if (loading) {
    return (
      <div className="flex-1">
        <NeonTopBar title={t("title")} breadcrumb={[{ label: "analytics" }]} />
        <div className="flex justify-center py-20">
          <NeonSpinner size="lg" />
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="flex-1">
        <NeonTopBar title={t("title")} breadcrumb={[{ label: "analytics" }]} />
        <p className="text-center py-8" style={{ color: NEON_RED }}>
          {error ?? t("loadFailed")}
        </p>
      </div>
    );
  }

  const { summary, velocity_by_week } = data;

  const statCards = [
    { label: t("totalPosts"), value: summary.total_posts },
    { label: t("publishedWeek"), value: summary.published_this_week },
    { label: t("pendingReview"), value: summary.pending_review },
    {
      label: t("qualityScore"),
      value: `${summary.quality_score_average}%`,
    },
  ];

  return (
    <div className="flex-1">
      <NeonTopBar title={t("title")} breadcrumb={[{ label: "analytics" }]} />
      <div className="py-8 px-8">
        <p className="mb-8" style={{ color: TEXT_MUTED }}>
          {t("subtitle")}
        </p>

        <div className="mb-8">
          <NeonStatsGrid cards={statCards} />
        </div>

        <NeonCard padding="md">
          <NeonCardHeader>
            <NeonCardTitle className="text-base">
              {t("velocityTitle")}
            </NeonCardTitle>
          </NeonCardHeader>
          <NeonCardContent>
            <div className="space-y-2">
              {velocity_by_week.map((week) => (
                <div
                  key={week.week_start}
                  className="flex min-w-0 items-center gap-3 text-sm"
                >
                  <span
                    className="w-20 shrink-0 sm:w-28"
                    style={{ color: TEXT_MUTED }}
                  >
                    {week.week_start}
                  </span>
                  {/* Bar in a min-w-0 scroll track: a long bar scrolls within
                      the row instead of overflowing the page on mobile. */}
                  <div className="min-w-0 flex-1 overflow-x-auto">
                    <div
                      className="h-4 rounded"
                      style={{
                        width: `${Math.max(week.published_count * 24, 4)}px`,
                        background: NEON_CYAN,
                        boxShadow: NEON_GLOW_CYAN_SOFT,
                      }}
                    />
                  </div>
                  <span className="shrink-0" style={{ color: TEXT }}>
                    {week.published_count}
                  </span>
                </div>
              ))}
            </div>
          </NeonCardContent>
        </NeonCard>
      </div>
    </div>
  );
}
