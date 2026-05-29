"use client";

import { useTranslations } from "next-intl";
import { NeonTopBar } from "@/components/organisms/neon-top-bar";
import { NeonStatsGrid } from "@/components/organisms/neon-stats-grid";
import { NeonActivityList } from "@/components/organisms/neon-activity-list";
import { NeonCard } from "@/components/molecules/neon-card";
import {
  STAT_CARDS,
  QUICK_ACTIONS,
  RECENT_ACTIVITIES,
  UPCOMING_SCHEDULE,
} from "./constants";
import { TEXT } from "@/constants/neon";
import type { NeonBadgeVariant } from "@/schemas/neon-badge";

const DOT_TO_BADGE: Record<string, NeonBadgeVariant> = {
  "#22c55e": "green",
  "#00d4ff": "cyan",
  "#f59e0b": "amber",
  "#ff2770": "magenta",
  "#0ac5a8": "teal",
};

export default function DashboardPage(): React.ReactElement {
  const t = useTranslations("dashboard.overview");

  const statCards = STAT_CARDS.map((stat) => ({
    label: stat.label,
    value: stat.value,
    change: stat.change,
    icon: (
      <svg
        width="18"
        height="18"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        style={{ color: stat.iconColor }}
      >
        {stat.icon}
      </svg>
    ),
    iconBg: stat.iconBg,
  }));

  const recentActivities = RECENT_ACTIVITIES.map((a, i) => ({
    id: `recent-${i}`,
    title: a.title,
    description: a.description,
    time: a.time,
    badgeVariant: DOT_TO_BADGE[a.dotColor] ?? "cyan",
  }));

  const scheduleActivities = UPCOMING_SCHEDULE.map((a, i) => ({
    id: `schedule-${i}`,
    title: a.title,
    description: a.description,
    time: a.time,
    badgeVariant: DOT_TO_BADGE[a.dotColor] ?? "cyan",
  }));

  return (
    <div
      className="flex-1 text-white relative"
      style={{ fontFamily: "Inter, system-ui, sans-serif" }}
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
              <NeonCard key={action.title} hover padding="md" className="text-center">
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
            ))}
          </div>
        </div>

        <div className="grid gap-5" style={{ gridTemplateColumns: "1fr 1fr" }}>
          <NeonActivityList
            title={t("recentActivity.title")}
            activities={recentActivities}
          />
          <NeonActivityList
            title={t("upcomingSchedule.title")}
            activities={scheduleActivities}
          />
        </div>
      </div>
    </div>
  );
}
