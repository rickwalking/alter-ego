import type {
  CalendarDay,
  CalendarEvent,
} from "@/modules/editorial-operations";

export interface CalendarGridProps {
  days: CalendarDay[];
  /** Accessible name of the grid: the viewed month, e.g. "October 2026". */
  label: string;
}

export interface CalendarDayCellProps {
  cell: CalendarDay;
}

export interface CalendarDayEventProps {
  event: CalendarEvent;
  /** Pre-formatted per-event date label, e.g. "Jun 10". */
  dateLabel: string;
}
