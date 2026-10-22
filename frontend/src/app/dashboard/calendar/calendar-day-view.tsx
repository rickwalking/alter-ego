"use client";

import { useTranslations } from "next-intl";
import { CALENDAR_COLORS } from "@/modules/editorial-operations";
import { NEON_BORDER_SUBTLE } from "@/constants/neon";
import { CalendarAgendaEvent } from "@/app/dashboard/calendar/calendar-agenda-event";
import type { CalendarDayViewProps } from "@/app/dashboard/calendar/types";

/** The focused day as a chronological list (the toolbar title names the day). */
export function CalendarDayView({
  day,
}: Readonly<CalendarDayViewProps>): React.ReactElement {
  const t = useTranslations("workflow.calendar.agenda");
  return (
    <section
      className="rounded-lg p-3 md:p-4"
      style={{
        background: CALENDAR_COLORS.card,
        border: `1px solid ${NEON_BORDER_SUBTLE}`,
      }}
    >
      {day.events.length > 0 ? (
        <ul className="flex flex-col gap-2">
          {day.events.map((event) => (
            <CalendarAgendaEvent key={event.id} event={event} />
          ))}
        </ul>
      ) : (
        <p
          className="py-10 text-center text-sm"
          style={{ color: CALENDAR_COLORS.tM }}
        >
          {t("emptyDay")}
        </p>
      )}
    </section>
  );
}
