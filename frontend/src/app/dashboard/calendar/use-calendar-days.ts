"use client";

import {
  buildCalendarDaysFromApi,
  buildEmptyCalendarDays,
} from "@/modules/editorial-operations";
import type { CalendarDay } from "@/modules/editorial-operations";
import { useContentCalendar } from "@/modules/editorial";

type UseCalendarDaysResult = {
  days: CalendarDay[];
  loading: boolean;
  error: string | null;
};

/**
 * Loads the content calendar and derives the month-grid days. Behavior is
 * identical to the original inline computation: when the API returns items,
 * build the grid from them; otherwise render the empty month shell.
 */
export function useCalendarDays(): UseCalendarDaysResult {
  const { calendar, loading, error } = useContentCalendar();
  const days =
    calendar && calendar.items.length > 0
      ? buildCalendarDaysFromApi(calendar.items)
      : buildEmptyCalendarDays();

  return { days, loading, error };
}
