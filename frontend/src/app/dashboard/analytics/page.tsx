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
import { CHANNEL_BLOG, CHANNEL_CAROUSEL } from "@/constants/analytics";
import { NEON_RED, TEXT_MUTED } from "@/constants/neon";
import {
  qualityScoreStat,
  useEditorialAnalytics,
  type ChannelPublishingSummary,
} from "@/modules/editorial-operations";
import { InstagramInsightsSection } from "./instagram-insights-section";
import { VelocityChart } from "./velocity-chart";

function publishedTotals(
  channels: ChannelPublishingSummary[],
): Record<string, number> {
  return Object.fromEntries(
    channels.map((c) => [c.channel, c.published_total]),
  );
}

/**
 * Shows a disabled state when the analytics flag is off (404) or the role has
 * no access (403). Weekly bars sit in a min-w-0 scroll track so a long bar
 * scrolls within its row instead of overflowing the page on mobile.
 */
export default function AnalyticsPage(): React.ReactElement {
  const t = useTranslations("dashboard.analytics");
  const { data, loading, error, disabled } = useEditorialAnalytics();

  if (loading) {
    return (
      <div className="flex-1">
        <NeonTopBar
          title={t("title")}
          breadcrumb={[{ label: t("breadcrumb") }]}
        />
        <div className="flex justify-center py-20">
          <NeonSpinner size="lg" />
        </div>
      </div>
    );
  }

  if (disabled) {
    return (
      <div className="flex-1">
        <NeonTopBar
          title={t("title")}
          breadcrumb={[{ label: t("breadcrumb") }]}
        />
        <div className="text-center py-8" data-testid="analytics-disabled">
          <p className="font-semibold" style={{ color: TEXT_MUTED }}>
            {t("disabledTitle")}
          </p>
          <p className="text-xs mt-1" style={{ color: TEXT_MUTED }}>
            {t("disabledBody")}
          </p>
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="flex-1">
        <NeonTopBar
          title={t("title")}
          breadcrumb={[{ label: t("breadcrumb") }]}
        />
        <p className="text-center py-8" style={{ color: NEON_RED }}>
          {t("loadFailed")}
        </p>
      </div>
    );
  }

  const { summary, velocity_by_week } = data;

  const statCards = [
    { label: t("totalPosts"), value: summary.total_posts },
    { label: t("publishedWeek"), value: summary.published_this_week },
    { label: t("pendingReview"), value: summary.pending_review },
    { label: t("qualityScore"), ...qualityScoreStat(summary, t) },
  ];

  const publishedByChannel = publishedTotals(summary.channels);

  return (
    <div className="flex-1">
      <NeonTopBar
        title={t("title")}
        breadcrumb={[{ label: t("breadcrumb") }]}
      />
      <div className="py-8 px-8">
        <p className="mb-8" style={{ color: TEXT_MUTED }}>
          {t("subtitle")}
        </p>

        <div className="mb-8">
          <NeonStatsGrid cards={statCards} />
        </div>

        <NeonCard padding="md" className="mb-8">
          <NeonCardHeader>
            <NeonCardTitle className="text-base">
              {t("velocityTitle")}
            </NeonCardTitle>
            <p className="text-xs mt-1" style={{ color: TEXT_MUTED }}>
              {t("publishedByChannel", {
                blog: publishedByChannel[CHANNEL_BLOG] ?? 0,
                carousels: publishedByChannel[CHANNEL_CAROUSEL] ?? 0,
              })}
            </p>
          </NeonCardHeader>
          <NeonCardContent>
            <VelocityChart weeks={velocity_by_week} />
          </NeonCardContent>
        </NeonCard>

        <InstagramInsightsSection />
      </div>
    </div>
  );
}
