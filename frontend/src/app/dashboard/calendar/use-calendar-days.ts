"use client";

import { useMemo } from "react";
import {
  buildCalendarDaysFromApi,
  buildEmptyCalendarDays,
  calendarGridRange,
} from "@/modules/editorial-operations";
import type { CalendarDay } from "@/modules/editorial-operations";
import { useContentCalendar } from "@/modules/editorial";

type UseCalendarDaysResult = {
  days: CalendarDay[];
  loading: boolean;
  error: string | null;
};

/**
 * Loads the content calendar for the month anchored at `anchor` and derives the
 * month-grid days. The fetch is scoped to the visible grid window (passed as
 * `start`/`end` to `/api/content-calendar`), and items are placed on their true
 * date by `buildCalendarDaysFromApi`.
 */
export function useCalendarDays(anchor: Date): UseCalendarDaysResult {
  const { start, end } = useMemo(() => {
    const range = calendarGridRange(anchor);
    // Real UTC instants for the local day boundaries (the backend interprets
    // the window in UTC); keeps the requested range consistent across offsets.
    return {
      start: range.start.toISOString(),
      end: range.end.toISOString(),
    };
  }, [anchor]);

  const { calendar, loading, error } = useContentCalendar(start, end);

  const days = useMemo(
    () =>
      calendar && calendar.items.length > 0
        ? buildCalendarDaysFromApi(anchor, calendar.items)
        : buildEmptyCalendarDays(anchor),
    [anchor, calendar],
  );

  return { days, loading, error };
}
