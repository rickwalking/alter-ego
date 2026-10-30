"use client";

import { useLocale, useTranslations } from "next-intl";
import { TEXT, TEXT_MUTED } from "@/constants/neon";
import { formatMetric } from "./instagram-insights-helpers";

export interface InstagramKpiTile {
  key: string;
  value: number | null;
}

/**
 * The summed KPI tiles shared by the dashboard card and the analytics-page
 * section; a metric no post reports shows "n/d", never 0.
 */
export function InstagramKpiTiles({
  tiles,
}: Readonly<{
  tiles: readonly InstagramKpiTile[];
}>): React.ReactElement {
  const t = useTranslations("dashboard.instagram");
  const locale = useLocale();
  const nd = t("notAvailable");

  return (
    <dl className="grid grid-cols-2 gap-3 sm:grid-cols-4 mb-5">
      {tiles.map((tile) => (
        <div key={tile.key} data-testid={`ig-kpi-${tile.key}`}>
          <dt className="text-xs" style={{ color: TEXT_MUTED }}>
            {t(`kpi.${tile.key}`)}
          </dt>
          <dd className="text-lg font-bold" style={{ color: TEXT }}>
            {formatMetric(tile.value, nd, locale)}
          </dd>
        </div>
      ))}
    </dl>
  );
}
