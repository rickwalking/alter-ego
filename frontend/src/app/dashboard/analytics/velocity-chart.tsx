"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { cn } from "@/lib/utils";
import {
  CHANNEL_BLOG,
  CHANNEL_CAROUSEL,
  CHANNEL_FILTER_ALL,
} from "@/constants/analytics";
import {
  NEON_CYAN,
  NEON_GLOW_CYAN_SOFT,
  TEXT,
  TEXT_MUTED,
} from "@/constants/neon";
import type { AnalyticsVelocityWeek } from "@/modules/editorial-operations";

const BAR_WIDTH_PER_PUBLISH = 24;
const BAR_MIN_WIDTH = 4;

interface VelocityChartProps {
  weeks: AnalyticsVelocityWeek[];
}

/**
 * The weekly publish-velocity bars with a channel picker (all, blog,
 * carousels). The picker is a button group: every option is reachable by
 * keyboard and shows a focus ring; the selected channel is exposed with
 * `aria-pressed`, never by colour alone.
 */
export function VelocityChart({
  weeks,
}: Readonly<VelocityChartProps>): React.ReactElement {
  const t = useTranslations("dashboard.analytics");
  const [channel, setChannel] = useState<string>(CHANNEL_FILTER_ALL);

  const options = [
    { value: CHANNEL_FILTER_ALL, label: t("channelAll") },
    { value: CHANNEL_BLOG, label: t("channelBlog") },
    { value: CHANNEL_CAROUSEL, label: t("channelCarousels") },
  ];

  return (
    <div className="space-y-4">
      <div
        role="group"
        aria-label={t("channelPickerLabel")}
        className="flex flex-wrap gap-2"
      >
        {options.map((option) => (
          <button
            key={option.value}
            type="button"
            aria-pressed={channel === option.value}
            onClick={() => setChannel(option.value)}
            className={cn(
              "rounded border px-3 py-1 text-xs font-semibold",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-neon-cyan focus-visible:ring-offset-2 focus-visible:ring-offset-bg-deep",
              channel === option.value
                ? "border-neon-cyan text-neon-cyan"
                : "border-transparent text-text-dim",
            )}
          >
            {option.label}
          </button>
        ))}
      </div>
      <div className="space-y-2">
        {weeks.map((week) => (
          <VelocityRow key={week.week_start} week={week} channel={channel} />
        ))}
      </div>
    </div>
  );
}

function VelocityRow({
  week,
  channel,
}: Readonly<{
  week: AnalyticsVelocityWeek;
  channel: string;
}>): React.ReactElement {
  const count =
    channel === CHANNEL_FILTER_ALL
      ? week.published_count
      : (week.channels[channel] ?? 0);

  return (
    <div className="flex min-w-0 items-center gap-3 text-sm">
      <span className="w-20 shrink-0 sm:w-28" style={{ color: TEXT_MUTED }}>
        {week.week_start}
      </span>
      <div className="min-w-0 flex-1 overflow-x-auto">
        <div
          className="h-4 rounded"
          style={{
            width: `${Math.max(count * BAR_WIDTH_PER_PUBLISH, BAR_MIN_WIDTH)}px`,
            background: NEON_CYAN,
            boxShadow: NEON_GLOW_CYAN_SOFT,
          }}
        />
      </div>
      <span className="shrink-0" style={{ color: TEXT }}>
        {count}
      </span>
    </div>
  );
}
