"use client";

import { useCallback, useMemo, useState } from "react";
import { useLocale } from "next-intl";
import { addMonths, startOfMonth } from "date-fns";
import { formatCalendarTitle } from "@/modules/editorial-operations";

export interface UseCalendarMonthResult {
  /** First day of the viewed month, or null until the local today is known. */
  anchor: Date | null;
  /** Viewed month in the active locale, e.g. "June 2026" / "Junho de 2026". */
  title: string;
  goPrev: () => void;
  goNext: () => void;
  goToday: () => void;
}

/**
 * Owns the viewed month as an offset from the month of `today` (the viewer's
 * local day, null until known), so the calendar opens on the local month and
 * "Today" returns to it. The anchor is the first of the month and stays
 * referentially stable between renders.
 */
export function useCalendarMonth(today: Date | null): UseCalendarMonthResult {
  const locale = useLocale();
  const [monthOffset, setMonthOffset] = useState(0);
  const currentMonth = today ? startOfMonth(today).getTime() : null;

  const goPrev = useCallback(() => {
    setMonthOffset((offset) => offset - 1);
  }, []);
  const goNext = useCallback(() => {
    setMonthOffset((offset) => offset + 1);
  }, []);
  const goToday = useCallback(() => {
    setMonthOffset(0);
  }, []);

  const anchor = useMemo(
    () =>
      currentMonth === null
        ? null
        : addMonths(new Date(currentMonth), monthOffset),
    [currentMonth, monthOffset],
  );
  const title = useMemo(
    () => (anchor ? formatCalendarTitle(anchor, locale) : ""),
    [anchor, locale],
  );

  return { anchor, title, goPrev, goNext, goToday };
}
