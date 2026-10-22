"use client";

import { useLocale, useTranslations } from "next-intl";
import { CalendarSvgIcon } from "@/modules/editorial-operations";
import {
  CALENDAR_COLORS,
  CALENDAR_MONO_FONT,
  calendarWeekdayHeaders,
} from "@/modules/editorial-operations";
import { NEON_BORDER_SUBTLE } from "@/constants/neon";
import type { CalendarDay } from "@/modules/editorial-operations";
import { CalendarDayCell } from "./calendar-day-cell";
import type { CalendarGridProps } from "@/app/dashboard/calendar/types";

const DAYS_PER_WEEK = 7;
const ROW_STYLE = { display: "contents" } as const;

function CalendarEmptyMonth(): React.ReactElement {
  const t = useTranslations("workflow.calendar");
  return (
    <div
      role="cell"
      aria-colspan={DAYS_PER_WEEK}
      style={{
        gridColumn: "1 / -1",
        padding: "60px 20px",
        textAlign: "center",
        color: CALENDAR_COLORS.tD,
      }}
    >
      <CalendarSvgIcon name="cal" size={48} />
      <p style={{ fontSize: 15, color: CALENDAR_COLORS.tM, margin: 0 }}>
        {t("emptyMonth")}
      </p>
      <p style={{ fontSize: 12, marginTop: 8, color: CALENDAR_COLORS.tD }}>
        {t("emptyMonthHint")}
      </p>
    </div>
  );
}

/** The month's day cells split into week rows of seven. */
function weeksOf(days: CalendarDay[]): CalendarDay[][] {
  const weeks: CalendarDay[][] = [];
  for (let start = 0; start < days.length; start += DAYS_PER_WEEK) {
    weeks.push(days.slice(start, start + DAYS_PER_WEEK));
  }
  return weeks;
}

/**
 * Keeps the month view and scroll-snaps horizontally on small screens so cells
 * stay about 91px wide or more (min-w 640 / 7) instead of crushing. Exposed as
 * an ARIA table named by the month: a header row of weekday column headers and
 * one row per week (rows use `display: contents`, so the CSS grid is unchanged).
 * It is read-only, so the cells are not tab stops.
 */
export function CalendarGrid({
  days,
  label,
}: Readonly<CalendarGridProps>): React.ReactElement {
  const locale = useLocale();
  const weekdayHeaders = calendarWeekdayHeaders(locale);
  const hasCurrentDays = days.filter((day) => day.cur).length > 0;
  return (
    <div className="overflow-x-auto [overscroll-behavior-x:contain]">
      <div
        role="table"
        aria-label={label}
        className="grid min-w-[640px] snap-x snap-mandatory grid-cols-7"
        style={{
          gap: 1,
          background: CALENDAR_COLORS.cG,
          borderRadius: 8,
          overflow: "hidden",
          border: `1px solid ${NEON_BORDER_SUBTLE}`,
        }}
      >
        <div role="row" style={ROW_STYLE}>
          {weekdayHeaders.map((header) => (
            <div
              key={header}
              role="columnheader"
              className="snap-start"
              style={{
                padding: 10,
                textAlign: "center",
                fontFamily: CALENDAR_MONO_FONT,
                fontSize: 10,
                textTransform: "uppercase",
                letterSpacing: 2,
                color: CALENDAR_COLORS.tD,
                background: "rgba(6,10,18,0.5)",
                fontWeight: 700,
              }}
            >
              {header}
            </div>
          ))}
        </div>
        {hasCurrentDays ? (
          weeksOf(days).map((week) => (
            <div key={week[0]?.iso} role="row" style={ROW_STYLE}>
              {week.map((cell) => (
                <CalendarDayCell key={cell.iso} cell={cell} />
              ))}
            </div>
          ))
        ) : (
          <div role="row" style={ROW_STYLE}>
            <CalendarEmptyMonth />
          </div>
        )}
      </div>
    </div>
  );
}
