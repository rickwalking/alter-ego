import type { CSSProperties } from "react";
import type { CalendarContentType, CalendarStatusType } from "./types";

export const CALENDAR_COLORS = {
  cyan: "#00d4ff",
  cD: "rgba(0,212,255,0.12)",
  cG: "rgba(0,212,255,0.08)",
  magenta: "#ff2770",
  teal: "#0ac5a8",
  amber: "#f59e0b",
  purple: "#a855f7",
  green: "#22c55e",
  aD: "rgba(245,158,11,0.12)",
  pD: "rgba(168,85,247,0.12)",
  bg: "#060a12",
  card: "#0d1324",
  txt: "rgba(255,255,255,0.88)",
  tM: "rgba(255,255,255,0.55)",
  tD: "rgba(255,255,255,0.3)",
  bdr: "rgba(0,212,255,0.06)",
} as const;

export const CALENDAR_CONTENT_META: Record<
  CalendarContentType,
  { c: string; d: string; l: string }
> = {
  carousel: { c: CALENDAR_COLORS.cyan, d: CALENDAR_COLORS.cD, l: "carousel" },
  blog: { c: CALENDAR_COLORS.teal, d: "rgba(10,197,168,0.12)", l: "blog" },
  meeting: { c: CALENDAR_COLORS.amber, d: CALENDAR_COLORS.aD, l: "meeting" },
  management: {
    c: CALENDAR_COLORS.purple,
    d: CALENDAR_COLORS.pD,
    l: "management",
  },
};

export const CALENDAR_STATUS_META: Record<
  CalendarStatusType,
  { c: string; b: string; l: string }
> = {
  published: { c: "#27ae60", b: "rgba(46,204,113,0.15)", l: "published" },
  approved: { c: CALENDAR_COLORS.cyan, b: "rgba(0,212,255,0.15)", l: "approved" },
  in_progress: {
    c: CALENDAR_COLORS.cyan,
    b: "rgba(0,212,255,0.15)",
    l: "in_progress",
  },
  awaiting_human: {
    c: "#ec3768",
    b: "rgba(236,56,153,0.15)",
    l: "awaiting_human",
  },
};

export const CALENDAR_WEEKDAY_HEADERS = [
  "Sun",
  "Mon",
  "Tue",
  "Wed",
  "Thu",
  "Fri",
  "Sat",
] as const;

export const CALENDAR_LEGEND = [
  { l: "Carousel", c: CALENDAR_COLORS.cyan },
  { l: "Blog Post", c: CALENDAR_COLORS.teal },
  { l: "Draft", c: CALENDAR_COLORS.magenta },
  { l: "Meeting", c: CALENDAR_COLORS.amber },
  { l: "Review", c: CALENDAR_COLORS.purple },
  { l: "Published", c: CALENDAR_COLORS.green },
] as const;

export const CALENDAR_VIEW_MODES = ["Month", "Week", "Day"] as const;

export const CALENDAR_TODAY = 28;

export const CALENDAR_BTN_GHOST: CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  gap: 8,
  padding: "6px 12px",
  borderRadius: 6,
  fontSize: 12,
  fontWeight: 600,
  lineHeight: 1,
  cursor: "pointer",
  border: "1px solid rgba(0,212,255,0.25)",
  background: "transparent",
  color: CALENDAR_COLORS.cyan,
  fontFamily: "inherit",
};

export const CALENDAR_FLEX_CENTER: CSSProperties = {
  display: "flex",
  alignItems: "center",
};

export const CALENDAR_MONO_FONT = "'JetBrains Mono', ui-monospace, monospace";

export const CALENDAR_RESPONSIVE_STYLE =
  "@media(max-width:768px){div[role=\"gridcell\"]{min-height:60px!important;padding:4px!important}div[role=\"gridcell\"]>div:first-child{font-size:11px!important}}";
