"use client";

import { useTranslations } from "next-intl";
import { CalendarSvgIcon } from "@/modules/editorial-operations";
import {
  CALENDAR_BTN_GHOST,
  CALENDAR_COLORS,
  CALENDAR_MONO_FONT,
} from "@/modules/editorial-operations";

/**
 * `pl-14` clears the layout-level mobile hamburger; layout and z-index use
 * Tailwind (stacking-map aligned) while the neon surface styling stays inline.
 * Like NeonTopBar it wraps on narrow screens: the breadcrumb hides below `sm`
 * and the actions take their own full-width row, so nothing is clipped.
 */
export function CalendarHeader({
  loading,
}: Readonly<{
  loading: boolean;
}>): React.ReactElement {
  const t = useTranslations("workflow.calendar");
  return (
    <div
      className="sticky top-0 z-50 flex min-h-14 flex-wrap items-center justify-between gap-x-3 gap-y-2 py-2 pr-4 pl-14 md:py-0 md:pr-8 lg:pl-8"
      style={{
        borderBottom: `1px solid ${CALENDAR_COLORS.bdr}`,
        background: "rgba(6,10,18,0.6)",
        backdropFilter: "blur(12px)",
        opacity: loading ? 0.5 : 1,
      }}
    >
      <div className="flex min-w-0 items-center gap-3">
        <h1
          style={{
            fontSize: 16,
            fontWeight: 700,
            color: CALENDAR_COLORS.txt,
            letterSpacing: "-0.02em",
          }}
        >
          {t("heading")}
        </h1>
        <span
          className="hidden sm:inline"
          style={{
            fontFamily: CALENDAR_MONO_FONT,
            fontSize: 11,
            color: CALENDAR_COLORS.tD,
          }}
        >
          / <span style={{ color: CALENDAR_COLORS.tM }}>content calendar</span>
        </span>
      </div>
      <div className="flex w-full flex-wrap items-center justify-end gap-2 sm:w-auto sm:gap-4">
        <button type="button" style={CALENDAR_BTN_GHOST}>
          <CalendarSvgIcon name="sync" size={14} /> Sync
        </button>
        <button
          type="button"
          style={{
            ...CALENDAR_BTN_GHOST,
            border: "none",
            background: `linear-gradient(135deg,${CALENDAR_COLORS.cyan} 0%,#0090b0 100%)`,
            color: CALENDAR_COLORS.bg,
            boxShadow: `0 0 16px ${CALENDAR_COLORS.cD}`,
          }}
        >
          <CalendarSvgIcon name="plus" size={14} /> Schedule Post
        </button>
      </div>
    </div>
  );
}
