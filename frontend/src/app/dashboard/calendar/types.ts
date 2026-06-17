import type {
  CalendarDay,
  CalendarEvent,
} from "@/modules/editorial-operations";

export interface CalendarGridProps {
  days: CalendarDay[];
}

export interface CalendarDayCellProps {
  cell: CalendarDay;
}

export interface CalendarDayEventProps {
  event: CalendarEvent;
  day: number;
}
