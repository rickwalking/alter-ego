"use client";

import { useMemo } from "react";
import { addDays, subDays } from "date-fns";
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
    // The grid cells are LOCAL dates but the backend window is UTC; a naive
    // toISOString() of the local boundaries shifts by the viewer's offset and
    // could drop an edge-cell event whose instant falls just outside the UTC
    // window. Pad ±1 day so every visible local cell is covered for any
    // timezone — placement stays exact because buildCalendarDaysFromApi matches
    // each item to a cell by its yyyy-MM-dd prefix (so the pad can't bleed).
    return {
      start: subDays(range.start, 1).toISOString(),
      end: addDays(range.end, 1).toISOString(),
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
