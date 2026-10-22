"use client";

import { useMemo, useSyncExternalStore } from "react";
import { format, parse } from "date-fns";
import { CALENDAR_ISO_DAY_FORMAT } from "@/modules/editorial-operations";

const TODAY_REFRESH_MS = 60_000;

function subscribeToClock(onChange: () => void): () => void {
  const timer = setInterval(onChange, TODAY_REFRESH_MS);
  return () => clearInterval(timer);
}

function localDayKey(): string {
  return format(new Date(), CALENDAR_ISO_DAY_FORMAT);
}

function serverDayKey(): null {
  return null;
}

/**
 * The viewer's local calendar day (midnight), or null during the server render
 * and hydration. The server runs in UTC, so a date it rendered would be
 * tomorrow for an evening viewer in Brazil, and React keeps server-rendered
 * styles on hydration; reading the day only on the client avoids both. The
 * value is re-read every minute so it rolls over at local midnight.
 */
export function useClientToday(): Date | null {
  const dayKey = useSyncExternalStore(
    subscribeToClock,
    localDayKey,
    serverDayKey,
  );
  return useMemo(
    () => (dayKey ? parse(dayKey, CALENDAR_ISO_DAY_FORMAT, new Date(0)) : null),
    [dayKey],
  );
}
