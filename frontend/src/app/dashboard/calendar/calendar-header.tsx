"use client";

import { CalendarSvgIcon } from "@/modules/editorial-operations";
import {
  CALENDAR_BTN_GHOST,
  CALENDAR_COLORS,
  CALENDAR_FLEX_CENTER,
  CALENDAR_MONO_FONT,
} from "@/modules/editorial-operations";

export function CalendarHeader({
  loading,
}: {
  loading: boolean;
}): React.ReactElement {
  return (
    <div
      style={{
        height: 56,
        ...CALENDAR_FLEX_CENTER,
        justifyContent: "space-between",
        padding: "0 32px",
        borderBottom: `1px solid ${CALENDAR_COLORS.bdr}`,
        background: "rgba(6,10,18,0.6)",
        backdropFilter: "blur(12px)",
        position: "sticky",
        top: 0,
        zIndex: 50,
        opacity: loading ? 0.5 : 1,
      }}
    >
      <div style={{ ...CALENDAR_FLEX_CENTER, gap: 12 }}>
        <span
          style={{
            fontSize: 16,
            fontWeight: 700,
            color: CALENDAR_COLORS.txt,
            letterSpacing: "-0.02em",
          }}
        >
          Calendar
        </span>
        <span
          style={{
            fontFamily: CALENDAR_MONO_FONT,
            fontSize: 11,
            color: CALENDAR_COLORS.tD,
          }}
        >
          / <span style={{ color: CALENDAR_COLORS.tM }}>content calendar</span>
        </span>
      </div>
      <div style={{ ...CALENDAR_FLEX_CENTER, gap: 16 }}>
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
