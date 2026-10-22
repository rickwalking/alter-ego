"use client";

import { NeonSpinner } from "@/components/atoms/neon-spinner";
import {
  CALENDAR_COLORS,
  CALENDAR_RESPONSIVE_STYLE,
} from "@/modules/editorial-operations";
import { NEON_RED } from "@/constants/neon";
import { useCalendarDays } from "@/app/dashboard/calendar/use-calendar-days";
import { useCalendarMonth } from "@/app/dashboard/calendar/use-calendar-month";
import { useClientToday } from "@/app/dashboard/calendar/use-client-today";
import { CalendarHeader } from "@/app/dashboard/calendar/calendar-header";
import { CalendarToolbar } from "@/app/dashboard/calendar/calendar-toolbar";
import { CalendarGrid } from "@/app/dashboard/calendar/calendar-grid";
import { CalendarLegend } from "@/app/dashboard/calendar/calendar-legend";

export default function CalendarPage(): React.ReactElement {
  const today = useClientToday();
  const { anchor, title, goPrev, goNext, goToday } = useCalendarMonth(today);
  const { days, loading, error } = useCalendarDays(anchor, today);

  return (
    <div
      style={{
        fontFamily: "'Inter', system-ui, -apple-system, sans-serif",
        color: CALENDAR_COLORS.txt,
        background: CALENDAR_COLORS.bg,
        minHeight: "100vh",
      }}
    >
      {error && (
        <p className="text-center py-4" style={{ color: NEON_RED }}>
          {error}
        </p>
      )}
      {(loading || !anchor) && (
        <div className="flex justify-center py-12">
          <NeonSpinner size="lg" />
        </div>
      )}
      <CalendarHeader loading={loading} />

      <div className="p-4 md:p-7">
        <CalendarToolbar
          title={title}
          onPrev={goPrev}
          onNext={goNext}
          onToday={goToday}
        />
        {anchor ? <CalendarGrid days={days} /> : null}
        <CalendarLegend />
      </div>

      <style>{CALENDAR_RESPONSIVE_STYLE}</style>
    </div>
  );
}
