"use client";

import { useCallback, useState } from "react";
import type { UseCalendarSyncResult } from "@/app/dashboard/calendar/types";

/**
 * The Sync button's state: `sync` re-fetches the calendar window now and
 * records when it finished, only when the refetch stored new data; a failed or
 * aborted sync keeps the previous time (and the page hides it while a load
 * error is shown), so a failed sync never claims to be up to date.
 */
export function useCalendarSync(
  refetch: () => Promise<boolean>,
): UseCalendarSyncResult {
  const [syncing, setSyncing] = useState(false);
  const [syncedAt, setSyncedAt] = useState<Date | null>(null);

  const sync = useCallback(async () => {
    setSyncing(true);
    try {
      if (await refetch()) {
        setSyncedAt(new Date());
      }
    } finally {
      setSyncing(false);
    }
  }, [refetch]);

  return { syncing, syncedAt, sync };
}
