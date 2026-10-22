"use client";

import { useLocale, useTranslations } from "next-intl";
import {
  CALENDAR_BTN_GHOST,
  CALENDAR_COLORS,
  CALENDAR_MONO_FONT,
  CalendarSvgIcon,
} from "@/modules/editorial-operations";
import { formatLocaleTime } from "@/lib/locale-format";
import type { CalendarSyncButtonProps } from "@/app/dashboard/calendar/types";

/**
 * Sync re-fetches the calendar now. While it runs the button is busy and
 * disabled; after a successful sync the local time of the last sync is shown
 * (and announced). A failed sync shows the page's load error instead.
 */
export function CalendarSyncButton({
  syncing,
  syncedAt,
  onSync,
}: Readonly<CalendarSyncButtonProps>): React.ReactElement {
  const t = useTranslations("workflow.calendar.sync");
  const locale = useLocale();
  return (
    <span className="flex items-center gap-2">
      <span
        role="status"
        className="text-[11px]"
        style={{ fontFamily: CALENDAR_MONO_FONT, color: CALENDAR_COLORS.tM }}
      >
        {syncedAt
          ? t("syncedAt", { time: formatLocaleTime(syncedAt, locale) })
          : null}
      </span>
      <button
        type="button"
        onClick={onSync}
        disabled={syncing}
        aria-busy={syncing}
        style={{ ...CALENDAR_BTN_GHOST, opacity: syncing ? 0.6 : 1 }}
      >
        <span
          className={syncing ? "animate-spin" : undefined}
          style={{ lineHeight: 0 }}
        >
          <CalendarSvgIcon name="sync" size={14} />
        </span>
        {syncing ? t("syncing") : t("button")}
      </button>
    </span>
  );
}
