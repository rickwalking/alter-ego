"use client";

import { useTranslations } from "next-intl";
import { cn } from "@/lib/utils";
import { STAT_CARDS, QUICK_ACTIONS, RECENT_ACTIVITIES, UPCOMING_SCHEDULE } from "./constants";

export default function DashboardPage() {
  const t = useTranslations("dashboard.overview");

  return (
    <div className="flex-1 text-white relative" style={{ fontFamily: "Inter, system-ui, sans-serif" }}>
      {/* Top Bar */}
      <div style={{ height: "56px", display: "flex", alignItems: "center", justifyContent: "space-between", padding: "0 32px", borderBottom: "1px solid rgba(0,212,255,0.06)", background: "rgba(6,10,18,0.6)", backdropFilter: "blur(12px)", position: "sticky", top: 0, zIndex: 30 }}>
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <h1 style={{ fontSize: "16px", fontWeight: 700, color: "rgba(255,255,255,0.88)", letterSpacing: "-0.02em" }}>Dashboard</h1>
          <div style={{ fontFamily: "'JetBrains Mono', ui-monospace, monospace", fontSize: "11px", color: "rgba(255,255,255,0.3)" }}>/ <span style={{ color: "rgba(255,255,255,0.55)" }}>overview</span></div>
        </div>
      </div>

      <div style={{ padding: "28px 32px" }}>
      {/* Stats Grid — auto-fit, same as shell .stats-grid */}
      <div
        className="grid gap-4 mb-7"
        style={{ gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))" }}
      >
        {STAT_CARDS.map((stat) => (
          <StatCard key={stat.label} {...stat} />
        ))}
      </div>

      {/* Quick Actions */}
      <div className="mb-7">
        <div className="flex items-center justify-between mb-4">
          <h2
            className="font-extrabold tracking-tight"
            style={{ fontSize: 18, color: "var(--text, rgba(255,255,255,0.88))" }}
          >
            {t("quickActions.title")}
          </h2>
        </div>
        <div
          className="grid gap-4"
          style={{ gridTemplateColumns: "repeat(3, 1fr)" }}
        >
          {QUICK_ACTIONS.map((action) => (
            <QuickActionCard key={action.title} {...action} />
          ))}
        </div>
      </div>

      {/* Recent Activity + Upcoming Schedule */}
      <div
        className="grid gap-5"
        style={{ gridTemplateColumns: "1fr 1fr" }}
      >
        {/* Recent Activity */}
        <div
          className="overflow-hidden"
          style={{
            background: "#0d1324",
            border: "1px solid rgba(255,255,255,0.06)",
            borderRadius: 8,
          }}
        >
          <div
            className="flex items-center justify-between"
            style={{
              padding: "16px 20px",
              borderBottom: "1px solid rgba(255,255,255,0.04)",
            }}
          >
            <h3
              style={{ fontSize: 14, fontWeight: 700, color: "rgba(255,255,255,0.88)" }}
            >
              {t("recentActivity.title")}
            </h3>
            <span
              className="inline-flex items-center gap-[5px] font-mono font-semibold"
              style={{
                padding: "3px 9px",
                borderRadius: 4,
                fontSize: 10,
                background: "rgba(0,212,255,0.12)",
                color: "#00d4ff",
                letterSpacing: "0.3px",
              }}
            >
              <span
                className="rounded-full"
                style={{ width: 5, height: 5, background: "currentColor" }}
              />
              {t("recentActivity.live")}
            </span>
          </div>
          <div style={{ padding: "8px 20px" }}>
            {RECENT_ACTIVITIES.map((activity) => (
              <ActivityItem key={activity.title} {...activity} />
            ))}
          </div>
        </div>

        {/* Upcoming Schedule */}
        <div
          className="overflow-hidden"
          style={{
            background: "#0d1324",
            border: "1px solid rgba(255,255,255,0.06)",
            borderRadius: 8,
          }}
        >
          <div
            className="flex items-center justify-between"
            style={{
              padding: "16px 20px",
              borderBottom: "1px solid rgba(255,255,255,0.04)",
            }}
          >
            <h3
              style={{ fontSize: 14, fontWeight: 700, color: "rgba(255,255,255,0.88)" }}
            >
              {t("upcomingSchedule.title")}
            </h3>
            <button
              type="button"
              className="inline-flex items-center gap-2 font-semibold cursor-pointer transition-all duration-200"
              style={{
                padding: "6px 12px",
                borderRadius: 6,
                fontSize: 12,
                lineHeight: 1,
                background: "transparent",
                color: "#00d4ff",
                border: "1px solid rgba(0,212,255,0.25)",
                fontFamily: "inherit",
              }}
            >
              {t("upcomingSchedule.viewAll")}
            </button>
          </div>
          <div style={{ padding: "8px 20px" }}>
            {UPCOMING_SCHEDULE.map((item) => (
              <ActivityItem key={item.title} {...item} />
            ))}
          </div>
        </div>
      </div>
      </div>
    </div>
  );
}

/* ── Sub-components ── */

interface StatCardProps {
  label: string;
  value: string;
  change?: { value: string; trend: "up" | "down" };
  icon: React.ReactNode;
  iconBg: string;
  iconColor: string;
  valueColor: string;
  valueGlow: string;
}

function StatCard({
  label,
  value,
  change,
  icon,
  iconBg,
  iconColor,
  valueColor,
  valueGlow,
}: StatCardProps) {
  return (
    <div
      className="transition-all duration-200"
      style={{
        background: "#0d1324",
        border: "1px solid rgba(255,255,255,0.06)",
        borderRadius: 8,
        padding: 20,
      }}
    >
      <div
        className="flex items-center justify-center"
        style={{
          width: 36,
          height: 36,
          borderRadius: 8,
          background: iconBg,
          color: iconColor,
          marginBottom: 12,
        }}
      >
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          {icon}
        </svg>
      </div>
      <p
        className="font-mono font-bold uppercase"
        style={{
          fontSize: 10,
          letterSpacing: "2px",
          color: "rgba(255,255,255,0.3)",
          marginBottom: 8,
        }}
      >
        {label}
      </p>
      <p
        className="font-black leading-none tracking-tighter"
        style={{
          fontSize: 28,
          color: valueColor,
          textShadow: valueGlow,
          letterSpacing: "-0.03em",
        }}
      >
        {value}
      </p>
      {change && (
        <p
          className="font-mono"
          style={{
            fontSize: 11,
            marginTop: 6,
            color: change.trend === "up" ? "#22c55e" : "#ef4444",
          }}
        >
          {change.value}
        </p>
      )}
    </div>
  );
}

interface QuickActionCardProps {
  title: string;
  description: string;
  icon: React.ReactNode;
  iconBg: string;
  iconColor: string;
}

function QuickActionCard({
  title,
  description,
  icon,
  iconBg,
  iconColor,
}: QuickActionCardProps) {
  return (
    <button
      type="button"
      className="flex flex-col items-center text-center cursor-pointer transition-all duration-200 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#00d4ff]"
      style={{
        background: "#0d1324",
        border: "1px solid rgba(255,255,255,0.06)",
        borderRadius: 8,
        padding: 20,
        gap: 12,
        fontFamily: "inherit",
      }}
      onMouseEnter={(e) => {
        const el = e.currentTarget;
        el.style.borderColor = "rgba(0,212,255,0.2)";
        el.style.transform = "translateY(-2px)";
        el.style.boxShadow = "0 0 20px rgba(0,212,255,0.04)";
      }}
      onMouseLeave={(e) => {
        const el = e.currentTarget;
        el.style.borderColor = "rgba(255,255,255,0.06)";
        el.style.transform = "translateY(0)";
        el.style.boxShadow = "none";
      }}
      onMouseDown={(e) => {
        e.currentTarget.style.transform = "translateY(-1px)";
      }}
    >
      <div
        className="flex items-center justify-center"
        style={{
          width: 44,
          height: 44,
          borderRadius: 10,
          background: iconBg,
          color: iconColor,
        }}
      >
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          {icon}
        </svg>
      </div>
      <h4 style={{ fontSize: 13, fontWeight: 600, color: "rgba(255,255,255,0.88)" }}>
        {title}
      </h4>
      <p style={{ fontSize: 11, color: "rgba(255,255,255,0.3)", lineHeight: 1.4 }}>
        {description}
      </p>
    </button>
  );
}

interface ActivityItemProps {
  dotColor: string;
  title: string;
  description: string;
  time: string;
}

function ActivityItem({ dotColor, title, description, time }: ActivityItemProps) {
  return (
    <div
      className="flex items-start"
      style={{
        gap: 12,
        padding: "12px 0",
        borderBottom: "1px solid rgba(255,255,255,0.03)",
      }}
    >
      <span
        className="rounded-full flex-shrink-0"
        style={{
          width: 8,
          height: 8,
          marginTop: 5,
          background: dotColor,
        }}
      />
      <div className="flex-1" style={{ minWidth: 0 }}>
        <div style={{ fontSize: 13, fontWeight: 500, color: "rgba(255,255,255,0.88)" }}>
          {title}
        </div>
        <div style={{ fontSize: 12, color: "rgba(255,255,255,0.3)", marginTop: 2 }}>
          {description}
        </div>
        <div
          className="font-mono"
          style={{ fontSize: 10, color: "rgba(255,255,255,0.3)", marginTop: 4 }}
        >
          {time}
        </div>
      </div>
      </div>
    );
  }
