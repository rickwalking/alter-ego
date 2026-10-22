import type {
  CalendarDay,
  CalendarEvent,
  CalendarView,
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

/** How a toolbar change enters the browser history. */
export type CalendarHistoryEntry = "push" | "replace";

export interface CalendarUrlState {
  view: CalendarView;
  /** Focused local date; absent means today (kept out of the URL). */
  focus?: Date;
}

export interface UseCalendarViewResult {
  view: CalendarView;
  /** Focused local date (null until today is known on the client). */
  focus: Date | null;
  /** Localized title for the view, e.g. "October 2026" or "Oct 18 – 24, 2026". */
  title: string;
  goPrev: () => void;
  goNext: () => void;
  goToday: () => void;
  setView: (view: CalendarView) => void;
  openDay: (day: Date) => void;
}

export interface CalendarAgendaEventProps {
  event: CalendarEvent;
}

export interface CalendarDayViewProps {
  day: CalendarDay;
}

export interface CalendarWeekViewProps {
  days: CalendarDay[];
  onOpenDay: (day: Date) => void;
}

export interface CalendarWeekColumnProps {
  day: CalendarDay;
  onOpenDay: (day: Date) => void;
}

export interface CalendarViewSwitchProps {
  view: CalendarView;
  onViewChange: (view: CalendarView) => void;
}

export interface CalendarToolbarProps extends CalendarViewSwitchProps {
  title: string;
  onPrev: () => void;
  onNext: () => void;
  onToday: () => void;
}

export interface CalendarViewBodyProps {
  view: CalendarView;
  /** The toolbar title; names the month grid for assistive tech. */
  title: string;
  days: CalendarDay[];
  onOpenDay: (day: Date) => void;
}
