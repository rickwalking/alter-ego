"use client";

import { useCallback, useMemo, useState } from "react";
import { addMonths, format, startOfMonth, subMonths } from "date-fns";
import { CALENDAR_TITLE_FORMAT } from "@/modules/editorial-operations";

export type UseCalendarMonthResult = {
  /** First day of the viewed month (stable state used to derive the grid). */
  anchor: Date;
  /** Human title for the viewed month, e.g. "June 2026". */
  title: string;
  goPrev: () => void;
  goNext: () => void;
  goToday: () => void;
};

/**
 * Owns the viewed-month anchor, defaulting to the current month. The anchor is
 * normalized to the first of the month so the grid and the fetch window derive
 * deterministically and the value stays referentially stable between renders.
 */
export function useCalendarMonth(): UseCalendarMonthResult {
  const [anchor, setAnchor] = useState<Date>(() => startOfMonth(new Date()));

  const goPrev = useCallback(() => {
    setAnchor((current) => subMonths(current, 1));
  }, []);
  const goNext = useCallback(() => {
    setAnchor((current) => addMonths(current, 1));
  }, []);
  const goToday = useCallback(() => {
    setAnchor(startOfMonth(new Date()));
  }, []);

  const title = useMemo(() => format(anchor, CALENDAR_TITLE_FORMAT), [anchor]);

  return { anchor, title, goPrev, goNext, goToday };
}
