"use client";

import { CalendarSvgIcon } from "@/modules/editorial-operations";
import {
  CALENDAR_BTN_GHOST,
  CALENDAR_COLORS,
  CALENDAR_FLEX_CENTER,
  CALENDAR_VIEW_MODES,
} from "@/modules/editorial-operations";

export interface CalendarToolbarProps {
  title: string;
  onPrev: () => void;
  onNext: () => void;
  onToday: () => void;
}

export function CalendarToolbar({
  title,
  onPrev,
  onNext,
  onToday,
}: CalendarToolbarProps): React.ReactElement {
  return (
    <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
      <div style={{ ...CALENDAR_FLEX_CENTER, gap: 12 }}>
        <button
          type="button"
          aria-label="Previous month"
          onClick={onPrev}
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
          {title}
        </h2>
        <button
          type="button"
          aria-label="Next month"
          onClick={onNext}
          style={{
            ...CALENDAR_BTN_GHOST,
            padding: 8,
            lineHeight: 0,
            justifyContent: "center",
          }}
        >
          <CalendarSvgIcon name="right" />
        </button>
        <button
          type="button"
          onClick={onToday}
          style={{ ...CALENDAR_BTN_GHOST, marginLeft: 8 }}
        >
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
