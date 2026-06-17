"use client";

import { CalendarSvgIcon } from "@/modules/editorial-operations";
import {
  CALENDAR_BTN_GHOST,
  CALENDAR_COLORS,
  CALENDAR_FLEX_CENTER,
  CALENDAR_VIEW_MODES,
} from "@/modules/editorial-operations";

export function CalendarToolbar(): React.ReactElement {
  return (
    <div
      style={{
        ...CALENDAR_FLEX_CENTER,
        justifyContent: "space-between",
        marginBottom: 20,
      }}
    >
      <div style={{ ...CALENDAR_FLEX_CENTER, gap: 12 }}>
        <button
          type="button"
          aria-label="Previous month"
          style={{
            ...CALENDAR_BTN_GHOST,
            padding: 8,
            lineHeight: 0,
            justifyContent: "center",
          }}
        >
          <CalendarSvgIcon name="left" />
        </button>
        <h2
          style={{
            fontSize: 20,
            fontWeight: 800,
            color: CALENDAR_COLORS.txt,
            letterSpacing: "-0.02em",
            margin: 0,
          }}
        >
          May 2026
        </h2>
        <button
          type="button"
          aria-label="Next month"
          style={{
            ...CALENDAR_BTN_GHOST,
            padding: 8,
            lineHeight: 0,
            justifyContent: "center",
          }}
        >
          <CalendarSvgIcon name="right" />
        </button>
        <button type="button" style={{ ...CALENDAR_BTN_GHOST, marginLeft: 8 }}>
          Today
        </button>
      </div>
      <div style={{ display: "flex", gap: 8 }}>
        {CALENDAR_VIEW_MODES.map((viewMode) => (
          <button
            key={viewMode}
            type="button"
            style={{
              ...CALENDAR_BTN_GHOST,
              background:
                viewMode === "Month" ? CALENDAR_COLORS.cD : "transparent",
            }}
          >
            {viewMode}
          </button>
        ))}
      </div>
    </div>
  );
}
