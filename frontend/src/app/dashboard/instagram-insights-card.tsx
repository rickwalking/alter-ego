"use client";

import { useLocale, useTranslations } from "next-intl";
import { NEON_AMBER, TEXT, TEXT_MUTED } from "@/constants/neon";
import {
  useInstagramInsights,
  type InstagramInsights,
} from "@/modules/editorial-operations";
import {
  INSTAGRAM_KPI_KEYS,
  RECENT_POSTS_SHOWN,
  formatMetric,
  sumMetric,
} from "./instagram-insights-helpers";
import { InstagramKpiTiles } from "./instagram-kpi-tiles";
import { InsightsCardShell } from "./insights-card-shell";

/**
 * The dashboard's Instagram KPIs — totals over the recent published
 * posts, follows per post and shares per 100 views, then the latest posts.
 * A metric Graph did not return shows "n/d".
 */
export function InstagramInsightsCard(): React.ReactElement {
  const t = useTranslations("dashboard.instagram");
  const { data, isLoading, isError } = useInstagramInsights();

  return (
    <InsightsCardShell
      title={t("title")}
      subtitle={t("subtitle")}
      loadFailed={t("loadFailed")}
      isLoading={isLoading}
      isError={isError}
    >
      {data && <InsightsBody data={data} />}
    </InsightsCardShell>
  );
}

function InsightsBody({
  data,
}: Readonly<{
  data: InstagramInsights;
}>): React.ReactElement {
  const t = useTranslations("dashboard.instagram");
  const locale = useLocale();
  const nd = t("notAvailable");

  if (data.items.length === 0) {
    return <p className="text-sm text-text-dim">{t("empty")}</p>;
  }
  const tiles = [
    ...INSTAGRAM_KPI_KEYS.map((key) => ({
      key,
      value: sumMetric(data.items, key),
    })),
    { key: "followsPerPost", value: data.follows_per_post },
    { key: "sharesPer100Views", value: data.shares_per_100_views },
  ];

  return (
    <div>
      {!data.configured && (
        <p className="text-xs mb-3" style={{ color: NEON_AMBER }}>
          {t("notConfigured")}
        </p>
      )}
      <InstagramKpiTiles tiles={tiles} />
      <ul className="space-y-2">
        {data.items.slice(0, RECENT_POSTS_SHOWN).map((item) => (
          <li
            key={item.media_id}
            className="flex flex-wrap items-center justify-between gap-2 text-xs"
            style={{ color: TEXT_MUTED }}
          >
            <span className="font-semibold truncate" style={{ color: TEXT }}>
              {item.topic ?? item.media_id}
            </span>
            <span>
              {t("postLine", {
                views: formatMetric(item.views, nd, locale),
                shares: formatMetric(item.shares, nd, locale),
                saves: formatMetric(item.saved, nd, locale),
                follows: formatMetric(item.follows, nd, locale),
              })}
            </span>
            {item.stale && (
              <span style={{ color: NEON_AMBER }}>{t("stale")}</span>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
