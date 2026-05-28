"use client";

import { useTranslations } from "next-intl";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Spinner,
} from "@/components/ui";
import { useEditorialAnalytics } from "@/features/analytics/hooks/use-editorial-analytics";

export default function AnalyticsPage() {
  const t = useTranslations("dashboard.analytics");
  const { data, loading, error } = useEditorialAnalytics();

  if (loading) {
    return (
      <div className="flex justify-center py-12">
        <Spinner />
      </div>
    );
  }

  if (error || !data) {
    return (
      <p className="text-center text-red-500 py-8">
        {error ?? t("loadFailed")}
      </p>
    );
  }

  const { summary, velocity_by_week } = data;

  return (
    <div className="container mx-auto py-8 px-4">
      <h1 className="text-3xl font-bold mb-2">{t("title")}</h1>
      <p className="text-muted-foreground mb-8">{t("subtitle")}</p>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4 mb-8">
        <StatCard label={t("totalPosts")} value={summary.total_posts} />
        <StatCard
          label={t("publishedWeek")}
          value={summary.published_this_week}
        />
        <StatCard label={t("pendingReview")} value={summary.pending_review} />
        <StatCard
          label={t("qualityScore")}
          value={`${summary.quality_score_average}%`}
        />
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">{t("velocityTitle")}</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {velocity_by_week.map((week) => (
              <div
                key={week.week_start}
                className="flex items-center gap-3 text-sm"
              >
                <span className="w-28 text-muted-foreground">
                  {week.week_start}
                </span>
                <div
                  className="h-4 bg-primary rounded"
                  style={{
                    width: `${Math.max(week.published_count * 24, 4)}px`,
                  }}
                />
                <span>{week.published_count}</span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: string | number }) {
  return (
    <Card>
      <CardContent className="pt-6">
        <p className="text-sm text-muted-foreground">{label}</p>
        <p className="text-2xl font-bold">{value}</p>
      </CardContent>
    </Card>
  );
}
