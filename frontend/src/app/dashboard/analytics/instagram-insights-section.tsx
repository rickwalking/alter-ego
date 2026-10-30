"use client";

import { useMemo } from "react";
import { useLocale, useTranslations } from "next-intl";
import { NEON_AMBER, TEXT_MUTED } from "@/constants/neon";
import {
  INSTAGRAM_KPI_KEYS,
  formatMetric,
  sumMetric,
} from "@/app/dashboard/instagram-insights-helpers";
import { InstagramKpiTiles } from "@/app/dashboard/instagram-kpi-tiles";
import { InsightsCardShell } from "@/app/dashboard/insights-card-shell";
import {
  useInstagramInsights,
  type InstagramConnector,
  type InstagramInsights,
} from "@/modules/editorial-operations";

/**
 * Instagram insights on the analytics page: totals over the published
 * posts, per-post rows with the fetch time, and the connector state
 * (name, last sync, error) instead of silent zeros.
 */
export function InstagramInsightsSection(): React.ReactElement {
  const t = useTranslations("dashboard.analyticsInstagram");
  const { data, isLoading, isError } = useInstagramInsights();

  return (
    <InsightsCardShell
      title={t("title")}
      subtitle={t("subtitle")}
      loadFailed={t("loadFailed")}
      isLoading={isLoading}
      isError={isError}
    >
      {data && <InsightsContent data={data} />}
    </InsightsCardShell>
  );
}

function InsightsContent({
  data,
}: Readonly<{
  data: InstagramInsights;
}>): React.ReactElement {
  const tIg = useTranslations("dashboard.instagram");
  if (data.items.length === 0) {
    return (
      <div>
        <ConnectorBanner connector={data.connector} />
        <p className="text-sm text-text-dim">{tIg("empty")}</p>
      </div>
    );
  }
  return (
    <div>
      <ConnectorBanner connector={data.connector} />
      <InstagramKpiTiles
        tiles={INSTAGRAM_KPI_KEYS.map((key) => ({
          key,
          value: sumMetric(data.items, key),
        }))}
      />
      <PostTable data={data} />
    </div>
  );
}

function ConnectorBanner({
  connector,
}: Readonly<{
  connector: InstagramConnector;
}>): React.ReactElement | null {
  const t = useTranslations("dashboard.analyticsInstagram");
  const locale = useLocale();
  const dateTimeFormat = useMemo(
    () =>
      new Intl.DateTimeFormat(locale, {
        dateStyle: "medium",
        timeStyle: "short",
      }),
    [locale],
  );

  if (!connector.configured) {
    return (
      <p className="text-xs mb-3" style={{ color: NEON_AMBER }}>
        {t("notConfigured", { channel: connector.channel })}
      </p>
    );
  }
  const messages: string[] = [];
  if (connector.error) {
    messages.push(t("syncError", { error: connector.error }));
  }
  if (connector.stale && connector.last_sync_at) {
    messages.push(
      t("stale", {
        lastSync: dateTimeFormat.format(new Date(connector.last_sync_at)),
      }),
    );
  }
  if (messages.length === 0) {
    return null;
  }
  return (
    <div className="mb-3 space-y-1">
      {messages.map((message) => (
        <p key={message} className="text-xs" style={{ color: NEON_AMBER }}>
          {message}
        </p>
      ))}
    </div>
  );
}

function PostTable({
  data,
}: Readonly<{
  data: InstagramInsights;
}>): React.ReactElement {
  const t = useTranslations("dashboard.analyticsInstagram");
  const tIg = useTranslations("dashboard.instagram");
  const locale = useLocale();
  const nd = tIg("notAvailable");
  const dateTimeFormat = useMemo(
    () =>
      new Intl.DateTimeFormat(locale, {
        dateStyle: "medium",
        timeStyle: "short",
      }),
    [locale],
  );

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-xs">
        <thead>
          <tr style={{ color: TEXT_MUTED }}>
            <th scope="col" className="py-2 pr-3 font-semibold">
              {t("postColumn")}
            </th>
            {INSTAGRAM_KPI_KEYS.map((key) => (
              <th key={key} scope="col" className="py-2 pr-3 font-semibold">
                {tIg(`kpi.${key}`)}
              </th>
            ))}
            <th scope="col" className="py-2 pr-3 font-semibold">
              {t("fetchedColumn")}
            </th>
          </tr>
        </thead>
        <tbody>
          {data.items.map((item) => (
            <tr key={item.media_id} style={{ color: TEXT_MUTED }}>
              <td className="py-2 pr-3">
                <PostTitle mediaId={item.media_id} item={item} />
              </td>
              {INSTAGRAM_KPI_KEYS.map((key) => (
                <td key={key} className="py-2 pr-3">
                  {formatMetric(item[key], nd, locale)}
                </td>
              ))}
              <td className="py-2 pr-3">
                {item.fetched_at
                  ? dateTimeFormat.format(new Date(item.fetched_at))
                  : nd}
                {item.stale && (
                  <span className="ml-2" style={{ color: NEON_AMBER }}>
                    {tIg("stale")}
                  </span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function PostTitle({
  mediaId,
  item,
}: Readonly<{
  mediaId: string;
  item: InstagramInsights["items"][number];
}>): React.ReactElement {
  const label = item.topic ?? mediaId;
  if (!item.permalink) {
    return <span>{label}</span>;
  }
  return (
    <a
      href={item.permalink}
      target="_blank"
      rel="noreferrer"
      className="font-semibold text-neon-cyan underline-offset-2 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-neon-cyan focus-visible:ring-offset-2 focus-visible:ring-offset-bg-deep"
    >
      {label}
    </a>
  );
}
