"use client";

import { Suspense } from "react";
import { NeonSpinner } from "@/components/atoms/neon-spinner";
import {
  CALENDAR_COLORS,
  CALENDAR_RESPONSIVE_STYLE,
} from "@/modules/editorial-operations";
import { NEON_RED } from "@/constants/neon";
import { useCalendarDays } from "@/app/dashboard/calendar/use-calendar-days";
import { useCalendarView } from "@/app/dashboard/calendar/use-calendar-view";
import { useClientToday } from "@/app/dashboard/calendar/use-client-today";
import { CalendarHeader } from "@/app/dashboard/calendar/calendar-header";
import { CalendarToolbar } from "@/app/dashboard/calendar/calendar-toolbar";
import { CalendarViewBody } from "@/app/dashboard/calendar/calendar-view-body";

function CalendarScreen(): React.ReactElement {
  const today = useClientToday();
  const calendarView = useCalendarView(today);
  const { view, focus, title, goPrev, goNext, goToday, setView, openDay } =
    calendarView;
  const { days, loading, error } = useCalendarDays(view, focus, today);

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
      {(loading || !focus) && (
        <div className="flex justify-center py-12">
          <NeonSpinner size="lg" />
        </div>
      )}
      <CalendarHeader loading={loading} />

      <div className="p-4 md:p-7">
        <CalendarToolbar
          title={title}
          view={view}
          onPrev={goPrev}
          onNext={goNext}
          onToday={goToday}
          onViewChange={setView}
        />
        {focus ? (
          <CalendarViewBody
            view={view}
            title={title}
            days={days}
            onOpenDay={openDay}
          />
        ) : null}
      </div>

      <style>{CALENDAR_RESPONSIVE_STYLE}</style>
    </div>
  );
}

/**
 * The toolbar state lives in the URL (`useSearchParams`), which needs a
 * Suspense boundary for the static prerender of this route.
 */
export default function CalendarPage(): React.ReactElement {
  return (
    <Suspense fallback={<NeonSpinner size="lg" />}>
      <CalendarScreen />
    </Suspense>
  );
}
