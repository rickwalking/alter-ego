"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";
import { NeonTopBar } from "@/components/organisms/neon-top-bar";
import { NeonCard } from "@/components/molecules/neon-card";
import { QUICK_ACTIONS } from "./constants";
import { TEXT } from "@/constants/neon";
import { useEditorialAnalytics } from "@/modules/editorial-operations";
import {
  DashboardAnalyticsActivity,
  DashboardAnalyticsStats,
} from "./dashboard-analytics";
import { InstagramInsightsCard } from "./instagram-insights-card";

const PAGE_FONT_FAMILY = "Inter, system-ui, sans-serif";

/** The dashboard overview: stats, Instagram insights, quick actions and activity. */
export function DashboardHome(): React.ReactElement {
  const t = useTranslations("dashboard.overview");
  const analytics = useEditorialAnalytics();

  return (
    <div
      className="flex-1 text-white relative"
      style={{ fontFamily: PAGE_FONT_FAMILY }}
    >
      <NeonTopBar title={t("title")} breadcrumb={[{ label: "overview" }]} />

      <div className="p-4 md:p-7">
        <div className="mb-7">
          <DashboardAnalyticsStats state={analytics} />
        </div>

        <div className="mb-7">
          <InstagramInsightsCard />
        </div>

        <div className="mb-7">
          <h2
            className="font-extrabold tracking-tight mb-4"
            style={{ fontSize: 18, color: TEXT }}
          >
            {t("quickActions.title")}
          </h2>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {QUICK_ACTIONS.map((action) => (
              <Link
                key={action.title}
                href={action.href}
                className="block no-underline"
              >
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
                  <h4
                    className="text-sm font-semibold mb-1"
                    style={{ color: TEXT }}
                  >
                    {action.title}
                  </h4>
                  <p className="text-xs text-text-dim">{action.description}</p>
                </NeonCard>
              </Link>
            ))}
          </div>
        </div>

        <DashboardAnalyticsActivity state={analytics} />
      </div>
    </div>
  );
}
