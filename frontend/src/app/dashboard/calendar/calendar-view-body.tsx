"use client";

import { CalendarGrid } from "@/app/dashboard/calendar/calendar-grid";
import { CalendarLegend } from "@/app/dashboard/calendar/calendar-legend";
import { CalendarWeekView } from "@/app/dashboard/calendar/calendar-week-view";
import { CalendarDayView } from "@/app/dashboard/calendar/calendar-day-view";
import type { CalendarViewBodyProps } from "@/app/dashboard/calendar/types";

/** The month grid (with its legend), the week columns or the day list. */
export function CalendarViewBody({
  view,
  title,
  days,
  onOpenDay,
}: Readonly<CalendarViewBodyProps>): React.ReactElement | null {
  if (view === "week") {
    return <CalendarWeekView days={days} onOpenDay={onOpenDay} />;
  }
  if (view === "day") {
    const [day] = days;
    return day ? <CalendarDayView day={day} /> : null;
  }
  return (
    <>
      <CalendarGrid days={days} label={title} />
      <CalendarLegend />
    </>
  );
}
